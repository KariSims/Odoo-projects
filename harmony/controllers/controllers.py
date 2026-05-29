# -*- coding: utf-8 -*-
# from odoo import http


# class Harmony(http.Controller):
#     @http.route('/harmony/harmony', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/harmony/harmony/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('harmony.listing', {
#             'root': '/harmony/harmony',
#             'objects': http.request.env['harmony.harmony'].search([]),
#         })

#     @http.route('/harmony/harmony/objects/<model("harmony.harmony"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('harmony.object', {
#             'object': obj
#         })

