# from odoo import models

# class PaymentMethod(models.Model):
#     _inherit = "account.payment.method"

#     def _get_payment_method_information(self):
#         return {
#             'om'  : {'mode': 'multi', 'type': ('bank', 'cash')},
#             'wave': {'mode': 'multi', 'type': ('bank', 'cash')},
#             'liv': {'mode': 'multi', 'type': ('cash', 'credit')},
#         }