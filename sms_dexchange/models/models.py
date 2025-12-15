# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class sms_dexchange(models.Model):
#     _name = 'sms_dexchange.sms_dexchange'
#     _description = 'sms_dexchange.sms_dexchange'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

