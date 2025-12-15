from odoo import models, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Bloque la confirmation si un produit a un stock insuffisant dans l'entrepôt par défaut,
        en tenant compte des unités de mesure (UoM).
        """
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

                # Focus sur les produits de type "consommable"
                if product.type == 'consu':
                    # Calcul de la quantité commandée dans l’unité de stock du produit
                    ordered_qty_in_stock_uom = line.product_uom._compute_quantity(
                        line.product_uom_qty, product.uom_id, rounding_method='HALF-UP'
                    )

                    # Quantité disponible à l’emplacement de l'entrepôt
                    available_qty = product.with_context(location=stock_location.id).free_qty

                    if ordered_qty_in_stock_uom > available_qty:
                        error_lines.append(
                            _(
                                "Produit '%s': commandé %.2f %s (équivaut à %.2f %s) mais seulement %.2f %s disponible dans l'entrepôt '%s'."
                            ) % (
                                product.display_name,
                                line.product_uom_qty,
                                line.product_uom.name,
                                ordered_qty_in_stock_uom,
                                product.uom_id.name,
                                available_qty,
                                product.uom_id.name,
                                warehouse.display_name
                            )
                        )

            if error_lines:
                raise ValidationError(
                    _("Impossible de confirmer la commande à cause d’un stock insuffisant dans l’entrepôt par défaut :\n\n") +
                    "\n".join(error_lines)
                )

        return super().action_confirm()