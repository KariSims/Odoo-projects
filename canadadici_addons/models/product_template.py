from odoo import api, fields, models
from datetime import datetime
import logging
_logger =  logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    is_delivery_service = fields.Boolean('Est un service de livraison ?', default=False)
    is_published = fields.Boolean('Est Publié', default=True)
    is_storable = fields.Boolean('Suivre le stock', default=True)
    allow_out_of_stock_order = fields.Boolean('En rupture de stock', default=False)

    def create(self, vals):
        # Applique la logique avant la création du produit
        self._set_default_values(vals)
        return super(ProductTemplate, self).create(vals)

    def write(self, vals):
        # Applique la logique avant la mise à jour du produit
        self._set_default_values(vals)
        return super(ProductTemplate, self).write(vals)

    def _set_default_values(self, vals):
        # Appliquer la logique de définition des valeurs par défaut

        # 1. Désactivation de allow_out_of_stock_order si activé
        if 'allow_out_of_stock_order' in vals and vals['allow_out_of_stock_order']:
            vals['allow_out_of_stock_order'] = False  # Désactiver allow_out_of_stock_order

        # 2. Définir 'is_storable' à True si ce n'est pas déjà défini
        if 'is_storable' not in vals:
            vals['is_storable'] = True

        # 3. Définir 'is_published' à True si ce n'est pas déjà défini
        if 'is_published' not in vals:
            vals['is_published'] = True
    # @api.depends('value')
    # def create(self):
    #     # activer is_published & allow_out_of_stock_order par défaut
    #     if 'is_published' != True:
    #         self.is_published = True
    #     if 'is_storable' != True:
    #         self.is_storable = True
    #     if 'allow_out_of_stock_order' == True:
    #         self.allow_out_of_stock_order = False
    
    # @api.depends('value')
    # # def write(self, vals):
    #     # # Avant de mettre à jour un produit, on vérifie si ces champs sont décochés
    #     # if 'is_published' in vals and not vals['is_published']:
    #     #     vals['is_published'] = True  # Active is_published par défaut
    #     # if 'is_storable' in vals and not vals['is_storable']:
    #     #     vals['is_storable'] = True  # Active is_published par défaut
    #     # if 'allow_out_of_stock_order' in vals and vals['allow_out_of_stock_order']:
    #     #     vals['allow_out_of_stock_order'] = False  # Deactiver allow_out_of_stock_order par défaut
    #     # return super(ProductTemplate, self).write(vals)
    # def write(self):
    #     # Activer is_published & allow_out_of_stock_order si ce n'est pas déjà fait
    #     if 'is_published' != True:
    #         self.is_published = True
    #     if 'is_published' != True:
    #         self.is_storable = True
    #     if 'allow_out_of_stock_order' == True :
    #         self.allow_out_of_stock_order = False
            