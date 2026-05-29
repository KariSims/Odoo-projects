# -*- coding: utf-8 -*-
# from odoo import http


# class RecouvrementDrc(http.Controller):
#     @http.route('/recouvrement_drc/recouvrement_drc', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/recouvrement_drc/recouvrement_drc/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('recouvrement_drc.listing', {
#             'root': '/recouvrement_drc/recouvrement_drc',
#             'objects': http.request.env['recouvrement_drc.recouvrement_drc'].search([]),
#         })

#     @http.route('/recouvrement_drc/recouvrement_drc/objects/<model("recouvrement_drc.recouvrement_drc"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('recouvrement_drc.object', {
#             'object': obj
#         })

