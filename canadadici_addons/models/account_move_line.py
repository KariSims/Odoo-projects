# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2
import re

from odoo import _, api, fields, models, registry, Command, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class AccountMove(models.Model):
    _inherit = "account.move.line"
    
    is_delivery_line = fields.Boolean("Est une ligne de livraison", compute="_compute_is_delivery", store=True)

    @api.depends('product_id')
    def _compute_is_delivery(self):
        for record in self:
            record.is_delivery_line = False
            if record.product_id and record.product_id.type == 'service' and record.product_id.is_delivery_service:
                record.is_delivery_line = True