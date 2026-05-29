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

class ShopController(http.Controller):


    @http.route('/shop/get_order_info',
                type='json', auth='public',
                website=True, #methods=['GET'],
                csrf=False)
    def get_order_info(self):
    # def get_order_info(self, order_id=None, **post):

        order    = request.website.sale_get_order()
        order_id = order.id
        if not order_id:
            return {'error': 'Order ID manquant'}

        # order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists():
            return {'error': 'Commande introuvable'}

        # Appel de la méthode métier
        result = order.send_order_message()

        if result.get('error'):
            return {'error': result.get('error')}

        return {
            'success': True,
            'message': 'SMS "commande reçue" envoyé avec succès',
            'response': result
        }

    ## controller d'affichage d'infos de la commande from website '/shop/checkout'
    # @http.route('/shop/get_order_info', 
    #         type='http', auth='public', 
    #         website=True, methods=['GET'], csrf=False)
    # def get_order_info(self):
    #     order = request.website.sale_get_order()
    #     print("sale_order ===>>>>", order)
    #     if not order:
    #         return request.make_response(
    #             json.dumps({'error': 'Panier vide'}),
    #             [('Content-Type', 'application/json')]
    #         )

    #     data = {
    #         'order_id': order.id,
    #         'total': order.amount_total,
    #         'lines': [
    #             {
    #                 'name': line.product_id.name,
    #                 'qty': line.product_uom_qty,
    #                 'price': line.price_total
    #             } for line in order.order_line
    #         ]
    #     }

    #     return request.make_response(
    #         json.dumps(data),
    #         [('Content-Type', 'application/json')]
    #     )