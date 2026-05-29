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

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def write(self, vals):
        for order in self:
            if vals.get('payment_ids'):
                
                # Réinitialiser le compteur d'impression si nécessaire
                if order.nb_print > 0:
                    order.nb_print = 0

                # Ajouter un message dans le fil de discussion
                order.message_post(body=_("Le mode de paiement a été modifié."))

        return super(PosOrder, self).write(vals)
