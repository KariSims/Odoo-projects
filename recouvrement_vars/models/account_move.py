from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    amount_paid = fields.Monetary(
        string="Montant payé",
        currency_field='currency_id',
        compute='_compute_amount_paid',
        store=True,
    )

    @api.depends('amount_total', 'amount_residual')
    def _compute_amount_paid(self):
        for record in self:
            record.amount_paid = record.amount_total - record.amount_residual


    # Creation de ligne facture - sp
    @api.onchange('partner_id')
    def _onchange_partner_id_recouvrement(self):

        if not self.partner_id:
            return

        partner = self.partner_id

        if not partner.regime_cotisation:
            return

        # Recherche du produit lié au régime
        product = self.env['product.product'].search([
            ('product_tmpl_id.regime_cotisation', '=', partner.regime_cotisation),
            ('sale_ok', '=', True),
        ], limit=1)

        if not product:
            return

        # Nettoyer anciennes lignes
        self.invoice_line_ids = [(5, 0, 0)]

        # Ajouter nouvelle ligne
        self.invoice_line_ids = [(0, 0, {
            'product_id': product.id,
            'name': product.name,
            'quantity': 1,
            'price_unit': product.lst_price,
        })]