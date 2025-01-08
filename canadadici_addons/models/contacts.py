from odoo import fields, models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # titel = fields.Char('Vitre')
    titel = fields.Selection([
        ('', 'Choisissez un titre'),
        ('mr', 'Mr'),
        ('mme', 'Mme'),
        ],
        string="Ttitre",
        required=True,
        default='')
    
    phone = fields.Char('phone')
    street2 = fields.Char('Street2')

    @api.onchange('phone')
    def _onchange_telephone(self):
        if self.phone:
            self.street2 = self.phone