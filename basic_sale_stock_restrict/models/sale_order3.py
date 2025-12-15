from odoo import models, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Bloc la confirmation si un produit a un stock insuffisant dans l'entrepôt par défaut"""
        for order in self:
            error_lines = []

            # Récupération de l'entrepôt par défaut de la commande
            warehouse = order.warehouse_id or self.env['stock.warehouse'].search(
                [('company_id', '=', order.company_id.id)], limit=1
            )
            if not warehouse:
                raise ValidationError(_("Aucun entrepôt par défaut trouvé pour cette commande."))

            # Emplacement de stock principal de l'entrepôt
            stock_location = warehouse.lot_stock_id

            for line in order.order_line:
                product = line.product_id

                # Ici, on filtre sur les consommables
                if product.type == 'consu':  
                    available_qty = product.with_context(location=stock_location.id).free_qty
                    if line.product_uom_qty > available_qty:
                        error_lines.append(
                            _(
                                "Produit '%s': commandé %.2f mais seulement %.2f disponible dans l'entrepôt '%s'."
                            ) % (
                                product.display_name,
                                line.product_uom_qty,
                                available_qty,
                                warehouse.display_name
                            )
                        )
            if error_lines:
                raise ValidationError(
                    _("Impossible de confirmer la commande à cause d’un stock insuffisant dans l’entrepôt par défaut:\n\n") +
                    "\n".join(error_lines)
                )

        return super().action_confirm()
