from odoo import _, api, fields, models, registry, Command, SUPERUSER_ID
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)


class AccountPartner(models.Model):
    _inherit = "res.partner"
    
    title_shortcut = fields.Char(
        related='title.shortcut',
        string='Title Shortcut',
        readonly=True,  # Le champ est en lecture seule car c'est un champ "related"
        help="Shortcut of the partner's title"
    ) 