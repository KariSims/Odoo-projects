from odoo import models, fields, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        moves = self.filtered(lambda m:
            m.move_type == 'out_invoice'
            and m.state == 'posted'
            and m.commercial_partner_id.invoice_sending_method == 'email'
        )

        if moves:
            self.env['account.move.send']._generate_and_send_invoices(
                moves,
                from_cron=False,
                allow_raising=True
            )

        return res
    
    # Boutons customs
    def action_print_last_payment_receipt(self):
        self.ensure_one()

        # récupérer les paiements liés
        payments = self._get_reconciled_payments()

        if not payments:
            raise UserError("Aucun paiement lié à cette facture.")


        last_payment = payments.sorted(lambda p: p.date)[-1]

        # appeler le report du paiement
        return self.env.ref('account.action_report_payment_receipt').report_action(last_payment)


    def action_print_certificat(self):
        self.ensure_one()

        if self.amount_residual != 0:
            return

        # appeler ton report personnalisé
        return self.env.ref('recouvrement_drc.report_certificat_fin_cotisation').report_action(self)