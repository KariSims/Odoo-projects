# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    is_delivery_line = fields.Boolean("Est une ligne de livraison", compute="_compute_is_delivery", store=True)

    product_image = fields.Binary(
        string='Image',
        related='product_id.image_1920',
        store=False,
        readonly=True
    )

    @api.depends('product_template_id')
    def _compute_is_delivery(self):
        for record in self:
            record.is_delivery_line = False
            if (record.product_template_id and record.product_template_id.type == 'service' and record.product_template_id.is_delivery_service) or (record.product_id and record.product_id.type == 'service' and record.product_id.is_delivery_service) :
                record.is_delivery_line = True