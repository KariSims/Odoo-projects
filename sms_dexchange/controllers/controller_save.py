import logging
from odoo import http
from odoo.http import request, route
from odoo.exceptions import ValidationError
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.tools import clean_context, str2bool, single_email_re
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.translate import _
from odoo.addons.website_sale.controllers.main import WebsiteSale
import json

_logger = logging.getLogger(__name__)

class dexchangeWebhook(http.Controller):

    @http.route('/dexchange/status', type='json', auth='none', methods=['POST'], csrf=False)
    def dexchange_status(self, **post):
        """
        Réception du webhook dexchange : mise à jour du statut d’un SMS.
        dexchange envoie un JSON du genre :
        {
          "message_id": "abc123",
          "type": "delivery",
          "status": "DELIVERED",
          "mobile": "221771819534"
        }
        """
        try:
            data = post or json.loads(request.httprequest.data.decode())
            _logger.info("dexchange webhook reçu : %s", data)

            msg_id = data.get('message_id')
            status = data.get('status', '').upper()

            if not msg_id:
                _logger.warning("Webhook dexchange sans message_id : %s", data)
                return {"status": "missing_message_id"}

            sms_message = request.env['sms.api.queue.message'].sudo().search([
                ('msgid', '=', msg_id)
            ], limit=1)

            if not sms_message:
                _logger.warning("Message non trouvé pour message_id=%s", msg_id)
                return {"status": "not_found"}

            # Mapper le statut dexchange → statut Odoo
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
            _logger.error("Erreur dans webhook dexchange : %s", e)
            return {"status": "error", "details": str(e)}


class WebsiteSMSController(http.Controller):
    @http.route(
        '/shop/send_order_message',
        type='http', 
        auth='public', 
        website=True, 
        csrf=False)
    def send_order_message(self, order_id=None, **post):
        """
        Contrôleur appelé par le JavaScript pour envoyer un SMS lié à une commande.
        """
        # 1. Récupération des données de configuration et de la commande
        if not order_id:
            return {'error': "Order ID manquant. 'SP'"}

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': f"Commande avec ID {order_id} introuvable."}

        partner = order.partner_id
        mobile_or_phone = partner.mobile or partner.phone

        if not mobile_or_phone:
            return {'error': f"Aucun numéro de téléphone/mobile trouvé pour le client de la commande {order.name}."}

        # 2. Trouver la configuration active
        config = request.env['dexchange.sms.config'].sudo().search([('active', '=', True)], limit=1)
        if not config:
            return {'error': "Aucune configuration Dexchange SMS active trouvée."}

        # --- Définir le Contenu du Message ---
        # NOTE: Vous devez définir ici le contenu exact du SMS.
        message_content = f"Votre commande {order.name} est confirmée. Merci de votre achat !"
        message_admin = (
            f"La commande {order.name} de {partner.name} "
            f"est confirmée. Veuillez la traiter dans le meilleur délai !"
            )
        admin_phone = "221771819534"

        # 3. Appel de la méthode d'envoi de SMS
        sms_service = request.env['dexchange.sms.service']

        ## Customer case
        response = sms_service.send_sms(
            recipients=[mobile_or_phone,221771819534],
            content=message_content,
            sender=config.sender,
            api_key=config.api_key,
            url=config.url
        )

        if response.get('error'):
            # Enregistrez l'échec dans un log si nécessaire
            # request.env['dexchange.sms.service'].create(...)
            return {'error': response.get('error'), 'message': "L'envoi du SMS a échoué."}
        
        ## Admin Case
        ###Envoi SMS ADMIN
        response_admin = sms_service.send_sms(
            recipients=[admin_phone],
            content=message_admin,
            sender=config.sender,
            api_key=config.api_key,
            url=config.url
            )

        if response_admin.get('error'):
            return {
                'error': response_admin.get('error'),
                'message': "SMS client envoyé, mais échec SMS admin."
            }

        # 4. Succès
        return {'success': True, 
                'message': "SMS de confirmation envoyé avec succès !", 
                'client_sms_response': response,
                'admin_sms_response': response_admin
                }


    @http.route('/shop/get_order_info', 
                type='http', 
                auth='public', 
                website=True, 
                methods=['GET'], csrf=False)
    def get_order_info(self):
        order = request.website.sale_get_order()
        if not order:
            return request.make_response(
                json.dumps({'error': 'Panier vide'}),
                [('Content-Type', 'application/json')]
            )

        data = {
            'order_id': order.id,
            'total': order.amount_total,
            'lines': [
                {
                    'name': line.product_id.name,
                    'qty': line.product_uom_qty,
                    'price': line.price_total
                } for line in order.order_line
            ]
        }

        return request.make_response(
            json.dumps(data),
            [('Content-Type', 'application/json')]
        )