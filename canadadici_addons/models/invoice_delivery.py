from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'


    delivery_amount = fields.Monetary(string='Delivery Amount', compute='_compute_delivery_amount', store=True, currency_field='currency_id')

    @api.depends('invoice_line_ids')
    def _compute_delivery_amount(self):
        for record in self:
            # Filtrer les lignes de la facture liées à la catégorie de livraison
            delivery_lines = record.invoice_line_ids.filtered(lambda line: line.product_id.default_code in ['Delivery_03', 'Delivery_04', 'Delivery_05','Delivery_06', 'Delivery_07', 'Delivery_08', 'Delivery_09'])
            
            if delivery_lines:
                record.delivery_amount = sum(delivery_lines.mapped('price_total'))
            else:
                record.delivery_amount = 0.0