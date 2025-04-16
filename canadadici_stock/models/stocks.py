from odoo import models, fields

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    # Champ user_id avec indexation
    user_id = fields.Many2one('res.users', string="Utilisateur", index=True, readonly=True, default=lambda self: self.env.user)

    # Champ create_id avec indexation
    create_uid = fields.Many2one('res.users', string="Créé par", index=True)