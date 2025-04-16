# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2
import re

from odoo import _, api, fields, models
import logging
logger = logging.getLogger(__name__)

class DeliveyCarrier(models.Model):
    _inherit = "delivery.carrier"
    
    city_ids = fields.Many2many('res.city', 'delivery_carrier_city_rel', 'carrier_id', 'city_id', 'Villes')
    municipality_ids = fields.Many2many('res.municipality', 'delivery_carrier_municipality_rel', 'carrier_id', 'municipality_id', 'Communes')

    def _match_address(self, partner):
        self.ensure_one()
        if self.country_ids and partner.country_id not in self.country_ids:
            return False
        if self.state_ids and partner.state_id not in self.state_ids:
            return False
        if self.city_ids and partner.city_id not in self.city_ids:
            return False
        if self.municipality_ids and partner.municipality_id not in self.municipality_ids:
            return False
        if self.zip_prefix_ids:
            regex = re.compile('|'.join(['^' + zip_prefix for zip_prefix in self.zip_prefix_ids.mapped('name')]))
            if not partner.zip or not re.match(regex, partner.zip.upper()):
                return False
        return True