from odoo import models, fields, exceptions


class MicroCycleLine(models.Model):
    _name = 'micro.cycle.line'
    _order = 'sequence'

    cycle_id = fields.Many2one('micro.cycle', string="Cycle Parent", ondelete='cascade')
    sequence = fields.Integer("N° Case")
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id.id
    )
    amount_expected = fields.Monetary(string="Montant attendu", currency_field='currency_id')
    is_paid = fields.Boolean("Coché", default=False)

    def register_collection(self):
        """Coche une case et crée la transaction terrain."""
        journal_id = self.env['micro.transaction']._get_collection_journal_id()
        for line in self:
            if line.is_paid:
                continue
            commission = 0.0
            if line.cycle_id.commission_rate > 0:
                commission = (line.amount_expected * line.cycle_id.commission_rate) / 100
            self.env['micro.transaction'].create({
                'partner_id': line.cycle_id.partner_id.id,
                'amount': line.amount_expected,
                'commission_amount': commission,
                'journal_id': journal_id,
                'transaction_type': 'savings',
                'state': 'draft',
                'cycle_line_id': line.id,
            })
            line.is_paid = True

    def unregister_collection(self):
        """Décoche une case — annule la transaction si draft, bloque si confirmée."""
        self.ensure_one()
        if not self.is_paid:
            raise exceptions.UserError("Cette case n'est pas encore cochée.")

        is_manager = self.env.user.has_group('microflow.group_micro_flow_manager')

        transaction = self.env['micro.transaction'].search(
            [('cycle_line_id', '=', self.id)], limit=1
        )

        if transaction:
            if transaction.state == 'confirmed':
                raise exceptions.UserError(
                    "Impossible d'annuler : cette collecte a déjà été validée "
                    "par le Manager."
                )
            if not is_manager:
                today = fields.Date.today()
                if transaction.create_date.date() != today:
                    raise exceptions.UserError(
                        "Vous ne pouvez décocher une case que le jour même "
                        "de la collecte."
                    )
            transaction.unlink()

        self.is_paid = False
