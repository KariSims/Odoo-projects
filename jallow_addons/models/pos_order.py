# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime
from markupsafe import Markup
from itertools import groupby
from collections import defaultdict
from random import randrange
from pprint import pformat

import psycopg2
import pytz

from odoo import api, fields, models, tools, _, Command
from odoo.tools import float_is_zero, float_round, float_repr, float_compare, formatLang
from odoo.exceptions import ValidationError, UserError
from odoo.osv.expression import AND
import base64

# _logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"


    def write(self, vals):
        for order in self:
            if vals.get('state') and vals['state'] == 'paid' and order.name == '/':
                vals['name'] = self._compute_order_name()
            if vals.get('mobile'):
                vals['mobile'] = order._phone_format(number=vals.get('mobile'),
                        country=order.partner_id.country_id or self.env.company.country_id)
            if vals.get('has_deleted_line') is not None and self.has_deleted_line:
                del vals['has_deleted_line']
            # order.nb_print = 0
        list_line = self._create_pm_change_log(vals)
        res = super().write(vals)
        for order in self:
            if vals.get('payment_ids'):
                order.with_context(backend_recomputation=True)._compute_prices()
                totally_paid_or_more = float_compare(order.amount_paid, self._get_rounded_amount(order.amount_total), precision_rounding=order.currency_id.rounding)
                if totally_paid_or_more < 0 and order.state in ['paid', 'done', 'invoiced']:
                    raise UserError(_('The paid amount is different from the total amount of the order.'))
                elif totally_paid_or_more > 0 and order.state == 'paid':
                    list_line.append(_("Warning, the paid amount is higher than the total amount. (Difference: %s)", formatLang(self.env, order.amount_paid - order.amount_total, currency_obj=order.currency_id)))
                if order.nb_print > 0 and vals.get('payment_ids'):
                    """ """
                    # raise UserError(_('You cannot change the payment of a printed order.'))

        if len(list_line) > 0:
            body = _("Payment changes:")
            body += self._markup_list_message(list_line)
            for order in self:
                if vals.get('payment_ids'):
                    order.message_post(body=body)

        return res