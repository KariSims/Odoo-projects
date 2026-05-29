from odoo import _, api, fields, models, registry, Command, SUPERUSER_ID
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)


class PosPayment(models.Model):
    _inherit = "pos.payment"


    payment_date = fields.Datetime(string='Date', required=False, readonly=False, default=lambda self: fields.Datetime.now())

    @api.constrains('amount')
    def _check_amount(self):
        for payment in self:
            if payment.pos_order_id.state in ['invoiced', 'posted', 'done', 'paid']:
                """ """
