from odoo import models, fields, api, exceptions


class MicroCreditLine(models.Model):
    _name = 'micro.credit.line'
    _description = "Ligne d'échéancier de remboursement"
    _order = 'sequence'

    credit_id = fields.Many2one('micro.credit', string="Crédit", ondelete='cascade')
    sequence = fields.Integer("N°", default=1)
    date_due = fields.Date(string="Date d'échéance")
    amount_due = fields.Monetary(string="Montant dû", currency_field='currency_id')
    amount_paid = fields.Monetary(string="Cumul payé", default=0.0, currency_field='currency_id')
    amount_residual = fields.Monetary(
        string="Reste à payer", currency_field='currency_id',
        compute='_compute_residual', store=True)
    payment_count = fields.Integer("Versements", default=0)
    currency_id = fields.Many2one('res.currency', related='credit_id.currency_id')
    is_overdue = fields.Boolean(
        string="Dépassée", compute='_compute_is_overdue',
        help="Vrai si la date d'échéance est passée et le solde non nul.")

    @api.depends('amount_due', 'amount_paid')
    def _compute_residual(self):
        for rec in self:
            rec.amount_residual = rec.amount_due - rec.amount_paid

    @api.depends('date_due', 'amount_residual')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_overdue = bool(
                rec.date_due and rec.date_due < today and rec.amount_residual > 0
            )

    def register_payment(self, payment_amount):
        self.ensure_one()
        if self.payment_count >= self.credit_id.max_partial_payments:
            raise exceptions.UserError(
                f"Limite de {self.credit_id.max_partial_payments} versement(s) "
                f"atteinte pour cette échéance."
            )
        if payment_amount <= 0 or payment_amount > self.amount_residual:
            raise exceptions.UserError(
                "Montant invalide : doit être > 0 et ≤ au reste à payer "
                f"({self.amount_residual:,.0f} {self.currency_id.name})."
            )
        self.amount_paid += payment_amount
        self.payment_count += 1
        journal_id = self.env['micro.transaction']._get_collection_journal_id()
        self.env['micro.transaction'].create({
            'partner_id': self.credit_id.partner_id.id,
            'agent_id': self.credit_id.agent_id.id,
            'amount': payment_amount,
            'journal_id': journal_id,
            'transaction_type': 'credit_repayment',
            'state': 'draft',
        })
        return True
