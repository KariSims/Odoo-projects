from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        res = super().action_post()

        for rec in self:
            rec._send_payment_email()

        return res

    def _send_payment_email(self):
        for rec in self:
            partner = rec.partner_id

            if not partner.email:
                continue

            # factures liées
            invoices = rec.reconciled_invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice'
            )

            total_amount = sum(invoices.mapped('amount_total'))
            residual_amount = sum(invoices.mapped('amount_residual'))

            # 📅 formatage de la date
            payment_date = fields.Date.to_string(rec.date)

            body = f"""
                <p>Bonjour {partner.name},</p>

                <p>Nous confirmons la réception de votre paiement.</p>

                <ul>
                    <li><b>Montant payé :</b> {rec.amount} {rec.currency_id.symbol}</li>
                    <li><b>Montant total :</b> {total_amount} {rec.currency_id.symbol}</li>
                    <li><b>Reste à payer :</b> {residual_amount} {rec.currency_id.symbol}</li>
                    <li><b>Date de paiement :</b> {payment_date}</li>
                </ul>

                <p>Merci pour votre confiance.</p>
            """

            try:
                self.env['mail.mail'].create({
                    'subject': 'Confirmation de paiement',
                    'body_html': body,
                    'email_to': partner.email,
                }).send()
            except Exception as e:
                _logger.warning(f"Impossible d’envoyer le mail au partenaire {partner.name}: {e}")