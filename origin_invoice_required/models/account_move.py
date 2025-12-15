from odoo import models, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange('invoice_origin')
    def _onchange_invoice_origin(self):
        if not self.invoice_origin:
            raise UserError(
                _("Pensez à lier cette facture à un devis ou commande de vente avant de la valider.")
            )
            # return {
            #     'warning': {
            #         'title': _("Attention"),
            #         'message': _("Pensez à lier cette facture à un devis ou commande de vente avant de la valider.")
            #     }
            # }
            
    def action_post(self):
        """Empêche la validation si la facture n’a pas de devis d’origine"""
        for move in self:
            # On cible uniquement les factures clients
            if move.move_type in ["out_invoice", "out_refund"]:
                if not move.invoice_origin:
                    raise UserError(
                        _("Vous ne pouvez pas valider cette facture car aucun devis ou commande de vente n’est lié.")
                    )

                # Option plus stricte : vérifier que l’origine existe réellement
                sale_orders = self.env["sale.order"].search([("name", "=", move.invoice_origin)])
                if not sale_orders:
                    raise UserError(
                        _("Le devis ou la commande mentionné(e) (%s) n’existe pas dans le système.") % move.invoice_origin
                    )

        # Si tout est OK, on laisse Odoo continuer
        return super().action_post()
