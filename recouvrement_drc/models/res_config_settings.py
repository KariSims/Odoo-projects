from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_create_invoice = fields.Boolean(
        string="Facturation automatique à la création du client",
        config_parameter='recouvrement_drc.auto_create_invoice',
        help="Si coché, une facture brouillon sera générée dès qu'un client avec un régime est créé."
    )