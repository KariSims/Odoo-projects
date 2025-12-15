from odoo import fields, models, api

class Partner(models.Model):
    _inherit = 'res.partner'   


    phone = fields.Char('phone')
    street2 = fields.Char('Street2')

    @api.onchange('phone')
    def _onchange_telephone(self):
        if self.phone:
            self.street2 = self.phone
