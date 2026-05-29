# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
_logger = logging.getLogger("__name__")
from datetime import datetime
from odoo import http
from odoo.http import request, route
from odoo.exceptions import ValidationError
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.tools import clean_context, str2bool, single_email_re
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.translate import _
import json

class WebsiteSMSController(http.Controller):

    @http.route('/shop/send_order_message', type='json', auth='public', website=True, csrf=False)
    def send_order_message(self, order_id=None, **post):
        """
        Contrôleur appelé par le JavaScript pour envoyer un SMS lié à une commande.
        """
        
        # 1. Récupération des données de configuration et de la commande
        if not order_id:
            return {'error': "Order ID manquant."}

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
        
        # 3. Appel de la méthode d'envoi de SMS
        sms_service = request.env['dexchange.sms.service']
        response = sms_service.send_sms(
            recipients=[mobile_or_phone],
            content=message_content,
            sender=config.sender,
            api_key=config.api_key,
            url=config.url
        )

        if response.get('error'):
            # Enregistrez l'échec dans un log si nécessaire
            # request.env['dexchange.sms.service'].create(...)
            return {'error': response.get('error'), 'message': "L'envoi du SMS a échoué."}
        
        # 4. Succès
        return {'success': True, 'message': "SMS de confirmation envoyé avec succès !", 'response': response}