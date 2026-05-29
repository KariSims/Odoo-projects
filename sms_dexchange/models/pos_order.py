from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model_create_multi
    def create(self, vals_list):
        order = super().create(vals_list)

        partner = order.partner_id
        customer_phone = order.partner_id.phone or order.partner_id.mobile
        mobile_or_phone = customer_phone.lstrip('+')

        # Trouver la configuration active
        # config = request.env['dexchange.sms.config'].sudo().search([('active', '=', True)], limit=1)
        config = self.env['dexchange.sms.config'].sudo().search([('active', '=', True)], limit=1)
        if not config:
            return {'error': "Aucune configuration Dexchange SMS active trouvée."}

        sms_service = self.env['dexchange.sms.service']
        try:
            if (partner and mobile_or_phone):
                # and not self.sms_sent
                message = (
                    f"Merci pour votre achat.\n"
                    f"Ticket: {order.name}\n"
                    f"Montant: {order.amount_total:.0f} FCFA"
                    )
                
                sms_service.send_sms(
                recipients=[mobile_or_phone],
                content=message,
                sender=config.sender,
                api_key=config.api_key,
                url=config.url
                    )
                # self.env["dexchange.sms"].sudo().send_sms(
                #     phone=order.partner_id.phone,
                #     message=message,
                # )
                # self.sms_sent = True
                _logger.info(
                    "SMS envoyé pour la commande %s (uuid=%s)",
                    order.name,
                    order.uuid,
                )

        except Exception as e:
            _logger.exception(
                "Erreur SMS pour la commande %s (uuid=%s)",
                order.name,
                order.uuid,
            )

        return order


# class PosOrder(models.Model):
#     _inherit = "pos.order"

#     def action_send_sms_from_pos(self, order_uid=None):
#         _logger.info("action_send_sms_from_pos appelé avec order_uid=%s", order_uid)

#         if not order_uid:
#             return False

#         order = self.search([("uuid", "=", order_uid)], limit=1)
#         _logger.info("Order trouvé: %s", order)

#         if not order or not order.partner_id or not order.partner_id.phone:
#             return False

#         try:
#             message = (
#                 f"Merci pour votre achat.\n"
#                 f"Ticket: {order.name}\n"
#                 f"Montant: {order.amount_total:.0f} FCFA"
#             )

#             self.env["dexchange.sms"].sudo().send_sms(
#                 phone=order.partner_id.phone,
#                 message=message
#             )

#         except Exception as e:
#             _logger.exception("Erreur Dexhange SMS")
#             return False

#         return True
