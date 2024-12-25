from odoo import models, fields, api

# class AccountMove(models.Model):
#     _inherit = 'account.move'

#     shipping_total = fields.Float(string="Shipping Total", compute="_compute_shipping_total")

#     @api.depends('invoice_line_ids')
#     def _compute_shipping_total(self):
#         for record in self:
#             total_shipping = 0.0
#             for line in record.invoice_line_ids:
#                 # Supposons que les lignes de livraison ont un type spécifique (par exemple, 'delivery')
#                 if line.product_id.type == 'service' and 'delivery' in line.product_id.name.lower():
#                     total_shipping += line.price_total
#             record.shipping_total = total_shipping

# class AccountMove(models.Model):
#     _inherit = 'account.move'

#     shipping_total = fields.Monetary(string='Frais de livraison', currency_field='currency_id')

#     def _get_report_values(self, docids, data=None):
#         res = super(AccountMove, self)._get_report_values(docids, data)
#         for doc in res['docs']:
#             # Ajouter le champ shipping_total à chaque facture
#             doc.shipping_total = self.shipping_total
#         return res
    
# models/account_move.py

# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'

#     @api.model
#     def get_delivery_amount(self):
#         """
#         Cette méthode vérifie si la ligne de facture correspond à un produit de la catégorie 'All/Deliveries'
#         et retourne le montant associé à ce produit pour les frais de livraison.
#         """
#         # Vérifie si la ligne de facture est liée à un produit dans la catégorie 'All/Deliveries'
#         if self.product_id and self.product_id.categ_id.name == 'All/Deliveries':
#             return self.price_total  # Retourne le total de la ligne de livraison
#         return 0.0  # Si ce n'est pas une ligne de livraison, retourne 0

class AccountMove(models.Model):
    _inherit = 'account.move'


    delivery_amount = fields.Monetary(string='Delivery Amount', compute='_compute_delivery_amount', store=True, currency_field='currency_id')

    @api.depends('invoice_line_ids')
    def _compute_delivery_amount(self):
        for record in self:
            # Filtrer les lignes de la facture liées à la catégorie de livraison
            delivery_lines = record.invoice_line_ids.filtered(lambda line: line.product_id.default_code == 'Delivery_03')
            # Calculer le montant total des frais de livraison
            if delivery_lines:
                record.delivery_amount = sum(delivery_lines.mapped('price_total'))
            else:
                record.delivery_amount = 0