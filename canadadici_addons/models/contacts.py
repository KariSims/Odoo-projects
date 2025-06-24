from odoo import fields, models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    title_shortcut = fields.Char(
        related='title.shortcut',
        string='Title Shortcut',
        readonly=True,  # Le champ est en lecture seule car c'est un champ "related"
        help="Shortcut of the partner's title"
    )