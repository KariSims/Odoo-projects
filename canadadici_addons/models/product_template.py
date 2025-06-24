from odoo import api, fields, models
import logging
_logger =  logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    is_delivery_service = fields.Boolean('Est un service de livraison ?', default=False)
    
    def publish_products(self):
        for product in self:
            if not product.is_published:
                product.is_published = True

    def unpublish_products(self):
        for product in self:
            if product.is_published:
                product.is_published = False

    @api.onchange('categ_id')
    def _onchange_categ_id_sync_website(self):
        for product in self:
            # Recherche ou création d'une catégorie eCommerce portant le même nom
            if product.categ_id:
                public_categ_ids = self.env['product.public.category'].search([
                    ('name', '=', product.categ_id.name)
                ], limit=1)

                if not public_categ_ids:
                    public_categ_ids = self.env['product.public.category'].create({
                        'name': product.categ_id.name,
                    })

                product.public_categ_ids = [(6, 0, [public_categ_ids.id])]