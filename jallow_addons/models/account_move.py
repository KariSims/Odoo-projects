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

    commercial_id = fields.Many2one(
        'jallow.commercial',
        string='Commercial',
        readonly=True,
        tracking=True,
        compute='_compute_commercial_id',
        store=True,
        help="Le nom du commercial qui a passé la commande"
        )
    
    @api.depends('invoice_origin')
    def _compute_commercial_id(self):
        for record in self:
            if record.invoice_origin:
                # Recherche de la commande de vente à partir de l'origine de la facture
                sale_order = self.env['sale.order'].search([('name', '=', record.invoice_origin)], limit=1)
                if sale_order:
                    record.commercial_id = sale_order.commercial_id
                else:
                    record.commercial_id = False