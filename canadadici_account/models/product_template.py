from odoo import api, fields, models
from datetime import datetime
import logging
_logger =  logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    is_delivery_service = fields.Boolean('Est un service de livraison ?', default=False)
    # is_published = fields.Boolean('Est Publié', default=True)
    # allow_out_of_stock_order = fields.Boolean('En rupture de stock', default=False)
