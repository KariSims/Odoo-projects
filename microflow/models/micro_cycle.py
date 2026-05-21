from odoo import models, fields, api, exceptions
import logging
_logger = logging.getLogger(__name__)


class MicroCycle(models.Model):
    _name = 'micro.cycle'
    _description = 'Cycle d Epargne'

    partner_id = fields.Many2one('res.partner', string="Membre", required=True)
    agent_id = fields.Many2one('res.users', string="Agent responsable",
                               default=lambda self: self.env.user, readonly=True)
    duration_months = fields.Integer("Durée (Mois)", default=1)
    case_count = fields.Integer("Nombre de cases", required=True)

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    amount_per_case = fields.Monetary(
        string="Montant par case",
        currency_field='currency_id', required=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'En cours'),
        ('closed', 'Terminé')
    ], default='draft')
    line_ids = fields.One2many(
        comodel_name='micro.cycle.line',
        inverse_name='cycle_id', string="Grille de Collecte")

    opening_fee = fields.Monetary(
        string="Frais d'adhésion",
        currency_field='currency_id', default=1000.0)
    commission_rate = fields.Float("Commission Collecte (%)", default=0.0)
    income_account_id = fields.Many2one('account.account', string="Compte de revenus")

    case_count_requested = fields.Integer(
        string="Correction demandée (cases)", default=0,
        help="Mis à jour par l'agent — en attente d'approbation Manager. 0 = aucune demande."
    )

    @api.model
    def init(self):
        _logger.warning("MODEL micro.cycle loaded")

    def action_activate(self):
        max_cycles = int(self.env['ir.config_parameter'].sudo().get_param('microflow.max_active_cycles', 1))
        for record in self:
            active_count = self.search_count([
                ('partner_id', '=', record.partner_id.id),
                ('state', '=', 'active'),
                ('id', '!=', record.id),
            ])
            if active_count >= max_cycles:
                raise exceptions.UserError(
                    f"Ce membre a déjà {active_count} cycle(s) actif(s). Maximum autorisé : {max_cycles}."
                )

            for i in range(1, record.case_count + 1):
                self.env['micro.cycle.line'].create({
                    'cycle_id': record.id,
                    'sequence': i,
                    'amount_expected': record.amount_per_case,
                })

            if record.opening_fee > 0:
                journal_id = self.env['micro.transaction']._get_collection_journal_id()
                self.env['micro.transaction'].create({
                    'partner_id': record.partner_id.id,
                    'amount': record.opening_fee,
                    'journal_id': journal_id,
                    'transaction_type': 'fees',
                    'state': 'confirmed',
                    'name': f"Frais adhésion — {record.partner_id.name}"
                })

            record.state = 'active'

    def action_request_correction(self):
        self.ensure_one()
        new_count = self.case_count_requested
        if new_count <= 0:
            raise exceptions.UserError("Indiquez un nombre de cases valide (supérieur à 0).")
        current_count = len(self.line_ids)
        if new_count == current_count:
            raise exceptions.UserError(
                f"Le nombre demandé ({new_count}) est identique au nombre de cases actuelles."
            )
        paid_count = len(self.line_ids.filtered('is_paid'))
        if new_count < paid_count:
            raise exceptions.UserError(
                f"{paid_count} case(s) déjà collectée(s). "
                f"Le nombre corrigé ne peut pas être inférieur à {paid_count}."
            )

    def action_approve_correction(self):
        self.ensure_one()
        new_count = self.case_count_requested
        paid_count = len(self.line_ids.filtered('is_paid'))
        if new_count < paid_count:
            raise exceptions.UserError(
                f"Approbation impossible : {paid_count} case(s) déjà collectée(s). "
                f"Minimum autorisé : {paid_count}."
            )
        current_count = len(self.line_ids)
        if new_count > current_count:
            for i in range(current_count + 1, new_count + 1):
                self.env['micro.cycle.line'].create({
                    'cycle_id': self.id,
                    'sequence': i,
                    'amount_expected': self.amount_per_case,
                })
        elif new_count < current_count:
            unpaid_desc = (
                self.line_ids
                .filtered(lambda l: not l.is_paid)
                .sorted('sequence', reverse=True)
            )
            unpaid_desc[:current_count - new_count].unlink()
        self.case_count = new_count
        self.case_count_requested = 0

    def action_reject_correction(self):
        self.ensure_one()
        self.case_count_requested = 0
