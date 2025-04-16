from odoo import models

class PaymentMethod(models.Model):
    _inherit = "account.payment.method"

    def _get_payment_method_information(self):
        return {
            'vbk'  : {'mode': 'multi', 'type': ('bank', 'credit')},
            'om'  : {'mode': 'multi', 'type': ('bank', 'credit')},
            'wave': {'mode': 'multi', 'type': ('bank', 'credit')},
            'liv': {'mode': 'multi', 'type': ('cash', 'credit')},
        }