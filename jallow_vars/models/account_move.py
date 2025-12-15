from odoo import _, api, fields, models
from odoo.tools import formatLang
from odoo.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"
 
    
    phone_sale = fields.Char(
        related='partner_id.phone',
        string='Téléphone',
        readonly=True,
    )

    on_enlevement = fields.Boolean(
            'Fait partie de l\'enlevement ?',
            default=False
            )

    commercial_id = fields.Many2one(
        'jallow.commercial',
        string='Commercial',
        # readonly=False,
        tracking=True,
        compute='_compute_commercial_id',
        store=True,
        help="Le nom du commercial qui a passé la commande"
        )

    supervisor_id = fields.Many2one(
        'jallow.supervisor',
        string='Superviseur',
        # readonly=True,
        tracking=True,
        compute='_compute_commercial_id',
        store=True,
        help="Le nom du Superviseur du Foot Soldier"
        )

    soldier_id = fields.Many2one(
        'jallow.soldier',
        string='Merchandiser',
        # readonly=True,
        tracking=True,
        compute='_compute_commercial_id',
        store=True,
        help="Le nom du Merchandiser qui a passé la commande"
        )
    
    @api.depends('invoice_origin')
    def _compute_commercial_id(self):
        for record in self:
            if record.invoice_origin:
                sale_order = self.env['sale.order'].search([('name', '=', record.invoice_origin)], limit=1)
                if sale_order:
                    record.commercial_id = sale_order.commercial_id
                    record.supervisor_id = sale_order.supervisor_id
                    record.soldier_id = sale_order.soldier_id
                else:
                    record.commercial_id = False
                    record.supervisor_id = False
                    record.soldier_id = False

    def button_draft(self):
        """Quand on remet la facture en brouillon, on recharge les infos commerciales."""
        res = super(AccountMove, self).button_draft()
        for record in self:
            if record.invoice_origin:
                sale_order = self.env['sale.order'].search([('name', '=', record.invoice_origin)], limit=1)
                if sale_order:
                    vals = {
                        'commercial_id': sale_order.commercial_id.id or False,
                        'supervisor_id': sale_order.supervisor_id.id or False,
                        'soldier_id': sale_order.soldier_id.id or False,
                    }
                    # write() ici est essentiel pour forcer la mise à jour dans la base
                    record.write(vals)
        return res