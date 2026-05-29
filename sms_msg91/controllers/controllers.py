from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)

class Msg91Webhook(http.Controller):

    # @http.route('/msg91/status', type='json', auth='none', methods=['POST'], csrf=False)
    @http.route('/shop/get_order_info',
                type='json', auth='public',
                website=True, #methods=['GET'],
                csrf=False)
    def msg91_status(self, **post):
        """
        Réception du webhook MSG91 : mise à jour du statut d’un SMS.
        MSG91 envoie un JSON du genre :
        {
          "message_id": "abc123",
          "type": "delivery",
          "status": "DELIVERED",
          "mobile": "221771234567"
        }
        """
        try:
            data = post or json.loads(request.httprequest.data.decode())
            _logger.info("MSG91 webhook reçu : %s", data)

            msg_id = data.get('message_id')
            status = data.get('status', '').upper()

            if not msg_id:
                _logger.warning("Webhook MSG91 sans message_id : %s", data)
                return {"status": "missing_message_id"}

            sms_message = request.env['sms.api.queue.message'].sudo().search([
                ('msgid', '=', msg_id)
            ], limit=1)

            if not sms_message:
                _logger.warning("Message non trouvé pour message_id=%s", msg_id)
                return {"status": "not_found"}

            # Mapper le statut MSG91 → statut Odoo
            odoo_status = 'sent'
            if status in ['DELIVERED', 'SUCCESS']:
                odoo_status = 'delivered'
            elif status in ['FAILED', 'UNDELIVERED']:
                odoo_status = 'error'

            sms_message.write({
                'state': odoo_status,
                'error_message': '' if odoo_status != 'error' else status
            })

            return {"status": "updated", "message_id": msg_id, "new_state": odoo_status}

        except Exception as e:
            _logger.error("Erreur dans webhook MSG91 : %s", e)
            return {"status": "error", "details": str(e)}
