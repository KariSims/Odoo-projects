from odoo import fields, models, api
from odoo.tools import formatLang
import logging
logger =  logging.getLogger("__name__")

class SaleOrder(models.Model):
    _inherit = "sale.order"


    phone_sale = fields.Char(
        related='partner_id.phone',
        string='Téléphone Client',
        readonly=True,
        help='Téléphone du Client ou Partenaire'
    )

    commercial_id = fields.Many2one(
    'jallow.commercial',
    string='Commercial',
    help='Commercial qui a prospecté le client'
    )