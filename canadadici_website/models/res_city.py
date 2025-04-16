from odoo import _, api, fields, models

class ResCity(models.Model):
    _name = "res.city"
    
    name = fields.Char("Nom") 
    country_id = fields.Many2one("res.country", string="Pays d'appartenance")
    municipality_ids = fields.One2many("res.municipality", "city_id", string="Communes")
    municipality_required = fields.Boolean(compute="_compute_required")
    
    @api.depends("municipality_ids")
    def _compute_required(self):
        for record in self:
            record.municipality_required = False
            if record.municipality_ids:
                record.municipality_required = True