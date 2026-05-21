from odoo import models, fields, api, exceptions
from dateutil.relativedelta import relativedelta


class MicroCredit(models.Model):
    _name = 'micro.credit'
    _description = 'Gestion des Credits'

    # ── Identification ────────────────────────────────────────────────────────
    partner_id = fields.Many2one('res.partner', string="Membre", required=True)
    agent_id = fields.Many2one(
        'res.users', string="Agent responsable",
        default=lambda self: self.env.user,
    )

    # ── Paramètres financiers ─────────────────────────────────────────────────
    capital = fields.Monetary(
        string="Capital octroyé", currency_field='currency_id', required=True)
    interest_rate = fields.Float("Taux d'intérêt (%)", default=0.0)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    # ── Échéancier ────────────────────────────────────────────────────────────
    installment_count = fields.Integer("Nombre d'échéances", required=True)
    installment_interval = fields.Integer("Intervalle", default=1)
    installment_period = fields.Selection([
        ('days',   'Jour(s)'),
        ('weeks',  'Semaine(s)'),
        ('months', 'Mois'),
    ], string="Période", default='months', required=True)
    max_partial_payments = fields.Integer("Limite paiements partiels", default=3)
    date_granted = fields.Date(string="Date d'octroi", readonly=True)

    # ── Workflow ──────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft',   'Brouillon'),
        ('pending', "En attente d'approbation"),
        ('active',  'En cours'),
        ('closed',  'Soldé'),
    ], default='draft', string="Statut")

    line_ids = fields.One2many('micro.credit.line', 'credit_id', string="Échéancier")

    # ── Montants calculés ─────────────────────────────────────────────────────
    amount_total = fields.Monetary(
        string="Total à rembourser",
        compute='_compute_amounts', store=True,
        currency_field='currency_id')
    amount_residual_total = fields.Monetary(
        string="Reste dû total",
        compute='_compute_amounts', store=True,
        currency_field='currency_id')

    @api.depends('capital', 'interest_rate', 'line_ids.amount_residual')
    def _compute_amounts(self):
        for rec in self:
            rec.amount_total = rec.capital * (1 + rec.interest_rate / 100)
            rec.amount_residual_total = sum(l.amount_residual for l in rec.line_ids)

    # ── Restrictions d'écriture ───────────────────────────────────────────────
    def write(self, vals):
        if 'agent_id' in vals:
            if not self.env.user.has_group('microflow.group_micro_flow_manager'):
                raise exceptions.UserError(
                    "Seul un Manager peut réaffecter l'agent responsable d'un crédit."
                )
        return super().write(vals)

    # ── Actions workflow ──────────────────────────────────────────────────────
    def action_submit(self):
        self.ensure_one()
        if not self.capital or self.capital <= 0:
            raise exceptions.UserError(
                "Définissez un capital valide (> 0) avant de soumettre.")
        if not self.installment_count or self.installment_count <= 0:
            raise exceptions.UserError(
                "Définissez le nombre d'échéances avant de soumettre.")
        self.state = 'pending'

    def action_approve(self):
        self.ensure_one()
        self.date_granted = fields.Date.today()
        self._generate_installments()
        self.state = 'active'

    def action_reject(self):
        self.ensure_one()
        self.state = 'draft'

    def action_close(self):
        self.ensure_one()
        unpaid = [l for l in self.line_ids if l.amount_residual > 0]
        if unpaid:
            total_due = sum(l.amount_residual for l in unpaid)
            raise exceptions.UserError(
                f"Impossible de solder ce crédit : "
                f"{total_due:,.0f} {self.currency_id.name} encore dû "
                f"sur {len(unpaid)} échéance(s)."
            )
        self.state = 'closed'

    # ── Génération de l'échéancier ────────────────────────────────────────────
    def _generate_installments(self):
        self.line_ids.unlink()
        total = self.capital * (1 + self.interest_rate / 100)
        per_installment = round(total / self.installment_count, 2)
        period = self.installment_period
        interval = self.installment_interval
        for i in range(1, self.installment_count + 1):
            if period == 'days':
                date_due = self.date_granted + relativedelta(days=i * interval)
            elif period == 'weeks':
                date_due = self.date_granted + relativedelta(weeks=i * interval)
            else:
                date_due = self.date_granted + relativedelta(months=i * interval)
            self.env['micro.credit.line'].create({
                'credit_id': self.id,
                'sequence': i,
                'date_due': date_due,
                'amount_due': per_installment,
            })
