import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class PosSmsController(http.Controller):

    @http.route('/pos/sp/send_sms', type='json', auth='user')
    def send_sms_after_pos(self, **kwargs):
        # Retrouver la commande PoS
        order_uid = kwargs.get("order_uid")           #suggestion gpt
        
        _logger.info("Controller OK")

        order = request.env['pos.order'].sudo().search(
            [('uuid', '=', order_uid)], limit=1
        )
        _logger.info("KWARGS REÇUS: %s et order_uid : %s", kwargs, order_uid)
        _logger.info("Order REÇUS: %s", order)

        if not order:
            return False

        if not order or not order.partner_id or not order.partner_id.phone:
            return False

        # Sécurité : éviter double envoi backend
        # if order.x_sms_sent:
        #     return True
        
        # Appel de la méthode métier
        result = order.send_order_message()

        message = (
            f"Merci pour votre achat.\n"
            f"Ticket: {order.name}\n"
            f"Montant: {order.amount_total:.0f} FCFA"
        )

        # Appel Dexchange SMS
        request.env['dexchange.sms'].sudo().send_sms(
            phone=order.partner_id.phone,
            message=message
        )

        # Marquer comme envoyé (champ custom)
        # order.x_sms_sent = True

        return True
