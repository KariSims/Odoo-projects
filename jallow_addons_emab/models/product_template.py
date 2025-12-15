from odoo import api, fields, models
import logging
_logger =  logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    def publish_products(self):
        for product in self:
            if not product.is_published:
                product.is_published = True

    def unpublish_products(self):
        for product in self:
            if product.is_published:
                product.is_published = False