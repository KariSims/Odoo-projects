from odoo import fields, models, api
from odoo.tools import formatLang
import logging
logger =  logging.getLogger("__name__")

class SaleOrder(models.Model):
    _inherit = "sale.order"


    phone_sale = fields.Char(
        related='partner_id.phone',
        string=' ',
        readonly=True,
        # help='Custom address field from the partner'
    )
    
    new_order_line = fields.One2many(
        comodel_name='sale.order.line',
        inverse_name='order_id',
        string="Lignes de commande",
        copy=True, auto_join=True, domain=[('is_delivery_line', '=', False)])
    
    delivery_amount = fields.Monetary("Montant de la livraison", compute="_compute_delivery_amount", 
                                      currency_field='currency_id', 
                                      readonly=True)  
    delivery_amount_to_print = fields.Char("Montant de la livraison à imprimer", compute="_compute_amount", readonly=True)

    @api.depends('order_line')
    def _compute_delivery_amount(self):
        for record in self:
            record.delivery_amount = 0
            for line in record.order_line:
                if line.is_delivery_line:
                    record.delivery_amount += line.price_total
            record.delivery_amount_to_print = formatLang(self.env, record.delivery_amount, currency_obj=record.currency_id)
                
    @api.depends_context('lang')
    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id')
    def _compute_tax_totals(self):
        AccountTax = self.env['account.tax']
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
            order.tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id or order.company_id.currency_id,
                company=order.company_id,
            )
            order.tax_totals['delivery_amount'] = order.delivery_amount
                