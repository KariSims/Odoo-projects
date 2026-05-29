from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"


    sms_sent = fields.Boolean(default=False)

    def send_order_message(self):
        """
        Contrôleur appelé par le JavaScript pour envoyer un SMS lié à une commande.
        """
        self.ensure_one()

        # 1. Récupération des données de configuration et de la commande
        partner = self.partner_id
        customer_phone = partner.mobile or partner.phone
        mobile_or_phone = customer_phone.lstrip('+')

        if not mobile_or_phone:
            return {'error': f"Aucun numéro de téléphone/mobile trouvé pour le client de la commande {self.name}."}

        ## *****************
        ## *****************
        # Check sms sending once
        if self.sms_sent:
            return {'error': 'SMS déjà envoyé'}

        # 2. Trouver la configuration active
        # config = request.env['dexchange.sms.config'].sudo().search([('active', '=', True)], limit=1)
        config = self.env['dexchange.sms.config'].sudo().search([('active', '=', True)], limit=1)
        if not config:
            return {'error': "Aucune configuration Dexchange SMS active trouvée."}

        # --- Définir le Contenu du Message ---
        # NOTE: Vous devez définir ici le contenu exact du SMS.
        message_content = f"Votre commande {self.name} est confirmée. Merci de votre achat !"
        message_admin = (
            f"La commande {self.name} de {partner.name} "
            f"est confirmée. Veuillez la traiter dans le meilleur délai !")
        admin_phone = "221771819534"

        # 3. Appel de la méthode d'envoi de SMS
        sms_service = self.env['dexchange.sms.service']

        ## Customer case
        try:
            response = sms_service.send_sms(
                recipients=[mobile_or_phone],
                content=message_content,
                sender=config.sender,
                api_key=config.api_key,
                url=config.url
            )
        except Exception as e:
            return { 'error': f"Erreur SMS provider: {str(e)}" }

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
        self.sms_sent = True
        return {'success': True, 
                'message': "SMS de confirmation envoyé avec succès !", 
                'client_sms_response': response,
                'admin_sms_response': response_admin
                }

    # def send_sms_order_received(self):
    #     """
    #     Envoie un SMS au client indiquant que la commande est reçue
    #     """
    #     self.ensure_one()

    #     partner = self.partner_id
    #     phone = partner.mobile or partner.phone

    #     if not phone:
    #         return {'error': 'Aucun numéro client'}

    #     config = self.env['dexchange.sms.config'].sudo().search(
    #         [('active', '=', True)],
    #         limit=1
    #     )
    #     if not config:
    #         return {'error': 'Configuration SMS manquante'}

    #     message = (
    #         f"Bonjour {partner.name}, "
    #         f"nous avons bien reçu votre commande {self.name}. "
    #         f"Elle sera traitée dans les plus brefs délais."
    #     )

    #     response = self.env['dexchange.sms.service'].send_sms(
    #         recipients=[phone],
    #         content=message,
    #         sender=config.sender,
    #         api_key=config.api_key,
    #         url=config.url
    #     )

    #     return response
