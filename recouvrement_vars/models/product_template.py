from odoo import api, fields, models
import re
import logging
_logger =  logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    regime_cotisation = fields.Selection([
        ('1', '500 USD'),
        ('2', '2000 USD'),
        ('3', '4000 USD'),
        ('4', '8000 USD'),
        ('5', '20000 USD'),
    ], string="Lié au régime")

    @api.onchange('regime_cotisation')
    def _onchange_regime_cotisation_set_price(self):
        """ 
        Extrait le montant du libellé de la sélection et l'affecte au prix de vente
        Ex: '2000 USD' -> 2000.0
        """
        if self.regime_cotisation:
            # Récupérer le libellé affiché (ex: '2000 USD')
            selection_label = dict(self._fields['regime_cotisation'].selection).get(self.regime_cotisation)
            
            if selection_label:
                # Utilise une expression régulière pour extraire uniquement les chiffres
                # On cherche tous les chiffres consécutifs avant l'espace
                match = re.search(r'\d+', selection_label)
                if match:
                    # Conversion en flottant et mise à jour du champ prix de vente standard d'Odoo
                    self.list_price = float(match.group())