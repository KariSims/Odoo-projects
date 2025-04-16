# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields,api
import logging
_logger = logging.getLogger(__name__)

class ResCountry(models.Model):
    _inherit = 'res.country'
 
    city_ids = fields.One2many('res.city', 'country_id', string="Villes")
    municipality_ids = fields.One2many('res.municipality', 'country_id', string="Communes")
    city_required = fields.Boolean(compute="_compute_required")
    municipality_required = fields.Boolean(compute="_compute_required")

    @api.depends("city_ids", "municipality_ids")
    def _compute_required(self):
        for record in self:
            record.city_required = False
            record.municipality_required = False
            if record.city_ids:
                record.city_required = True
            if record.municipality_ids:
                record.municipality_required = True
             
    def get_website_sale_cities(self, mode='billing'):
        res = self.env['res.city'].search([])
        return res
    
    def get_website_sale_municipalities(self, mode='billing'):
        res = self.env['res.municipality'].search([])
        return res
