from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    micro_flow_journal_id = fields.Many2one(
        'account.journal',
        string="Journal de collecte Micro Flow",
        config_parameter='microflow.journal_id',
        domain=[('type', '=', 'cash')],
    )
    max_active_cycles = fields.Integer(
        string="Cycles simultanés max par membre",
        config_parameter='microflow.max_active_cycles',
        default=1,
    )
