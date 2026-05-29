from odoo import fields, models, api
from odoo.tools import formatLang
import logging
logger =  logging.getLogger("__name__")

class ResPartner(models.Model):
    _inherit = "res.partner"

    phone = fields.Char('phone')
    street2 = fields.Char('Street2')

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    @api.onchange('phone')
    def _onchange_telephone(self):
        if self.phone:
            self.street2 = self.phone