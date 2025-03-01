from odoo import _, api, fields, models

class ResMunicipality(models.Model):
    _name = "res.municipality"
    
    name = fields.Char("Nom") 
    country_id = fields.Many2one("res.country", string="Pays d'appartenance")
    city_id = fields.Many2one("res.city", string="Ville", domain="[('country_id', '=', country_id)]")