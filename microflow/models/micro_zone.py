from odoo import models, fields

class MicroZone(models.Model):
    _name = 'micro.zone'
    _description = 'Zone de Collecte'
    _rec_name = 'name'

    name = fields.Char(string="Nom de la zone", required=True)
    code = fields.Char(string="Code", required=True, size=10)
    commission_rate = fields.Float(string="Taux de commission (%)", default=0.0)
    active = fields.Boolean(default=True)
