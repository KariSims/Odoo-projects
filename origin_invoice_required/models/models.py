# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class origin_invoice_required(models.Model):
#     _name = 'origin_invoice_required.origin_invoice_required'
#     _description = 'origin_invoice_required.origin_invoice_required'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

