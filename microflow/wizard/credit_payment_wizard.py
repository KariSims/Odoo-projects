from odoo import models, fields


class CreditPaymentWizard(models.TransientModel):
    _name = 'credit.payment.wizard'
    _description = "Assistant de versement crédit"

    line_id = fields.Many2one('micro.credit.line', string="Échéance cible", readonly=True)
    currency_id = fields.Many2one('res.currency', related='line_id.currency_id')

    # Champs contextuels (readonly) — informent l'agent sans navigation
    sequence = fields.Integer(related='line_id.sequence', readonly=True, string="N° Échéance")
    date_due = fields.Date(related='line_id.date_due', readonly=True, string="Date d'échéance")
    amount_due = fields.Monetary(
        related='line_id.amount_due', readonly=True,
        string="Montant de l'échéance", currency_field='currency_id')
    amount_paid = fields.Monetary(
        related='line_id.amount_paid', readonly=True,
        string="Déjà versé", currency_field='currency_id')
    amount_residual = fields.Monetary(
        related='line_id.amount_residual', readonly=True,
        string="Reste à payer", currency_field='currency_id')

    # Champ de saisie
    amount_to_pay = fields.Monetary("Montant versé", currency_field='currency_id')

    def action_validate_payment(self):
        self.line_id.register_payment(self.amount_to_pay)
        return {'type': 'ir.actions.act_window_close'}
