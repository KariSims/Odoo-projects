from odoo import fields, models, api
from odoo.exceptions import ValidationError
import logging
_logger =  logging.getLogger(__name__)

class Partner(models.Model):
    _inherit = 'res.partner'

    secteur = fields.Many2many(
        'res.partner.industry',
        string='Secteur d\'activité',
        help='Secteur d\'activité des Entreprises'
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    legal_status_code = fields.Selection([
        ('1', 'SARL'),
        ('2', 'SA'),
        ('3', 'SAS'),
        ('4', 'Entreprise ou Ets individuelle'),
        ('5', 'ONG / Association'),
        ('6', 'Chambre (à préciser)'),
        ('7', 'Autres (à préciser)'),
        ], 
        string="Statut juridique",
        )
    
    # label_legal_status_code = fields.Char(
    #     compute="_compute_label_legal_status"
    # )

    legal_status_detail = fields.Char(
        string="Précision statut juridique"
    )

    legal_status_display = fields.Char(
        compute="_compute_legal_status_display"
    )

    regime_cotisation = fields.Selection([
        ('1', '500 USD'),
        ('2', '2000 USD'),
        ('3', '4000 USD'),
        ('4', '8000 USD'),
        ('5', '20000 USD'),
    ], string="Régime de cotisation ($)")

    categorie_cotisant = fields.Selection([
        ('1', 'TPE'),
        ('2', 'PME'),
        ('3', 'Société'),
        ('4', 'Entreprise'),
        ('7', 'Grand Cotisant'),
    ], string="Catégorie de cotisant", compute="_compute_categorie", store=True)

    # montant_cotise = fields.Float(string="Montant cotisé")

    # date_cotisation = fields.Date(string="Date de cotisation")

    identifiant = fields.Char(
        string="Numéro d'identification",
        readonly=True,
        copy=False,
        compute="_compute_identifiant",
        store=True,
        index=True
    )

    @api.onchange('phone')
    def _onchange_telephone(self):
        if self.phone:
            self.street2 = self.phone

    @api.depends('legal_status_code')
    def _compute_legal_status_display(self):
        for rec in self:
            if rec.legal_status_code:
                label_legal_status_code = dict(self._fields['legal_status_code'].selection).get(rec.legal_status_code)
                rec.legal_status_display = f"{rec.legal_status_code} - {label_legal_status_code}"
            else:
                rec.legal_status_display = False


    @api.constrains('legal_status_code', 'legal_status_detail')
    def _check_legal_status_detail(self):
        for rec in self:
            if rec.legal_status_code in ('6', '7') and not rec.legal_status_detail:
                raise ValidationError(
                    "Veuillez préciser le statut juridique pour 'Chambre' ou 'Autres'."
                )
            
    @api.depends('regime_cotisation')
    def _compute_categorie(self):
        mapping = {
            '1': '1',
            '2': '2',
            '3': '3',
            '4': '4',
            '5': '7',
        }
        for rec in self:
            rec.categorie_cotisant = mapping.get(rec.regime_cotisation, False)
        
        # ==================================
        # ==================================
        # MAPPING CITY - PROVINCE
        # ==================================

    # @api.model
    # def create(self, vals):
        
    #     vals['country_id'] = self.env.ref('base.cd').id

    #     record = super().create(vals)

    #     record._update_identifiant()
    #     record._update_sending_method()

    #     return record
    

    # def write(self, vals):

    #     if 'country_id' in vals:
    #         vals['country_id'] = self.env.ref('base.cd').id

    #     res = super().write(vals)

    #     if 'state_id' in vals:
    #         self._update_identifiant()

    #     return res


    
    # def _update_identifiant(self):
    #     for rec in self:
    #         if not rec.state_id:
    #             continue

    #         prefix = rec.state_id.code

    #         if not prefix:
    #             raise ValidationError("Le code de la province est manquant.")

    #         rec.identifiant = f"{prefix}_{rec.id}"
    @api.depends('state_id', 'state_id.code')
    def _compute_identifiant(self):
        for rec in self:
            if isinstance(rec.id, models.NewId):
                rec.identifiant = False
                continue

            if rec.state_id and rec.state_id.code:
                rec.identifiant = f"{rec.state_id.code}_{rec.id}"
            else:
                rec.identifiant = False

    # mettre invoice_sending_method = 'email' à la création
    # corrige automatiquement les anciens contacts sans valeur
    def _update_sending_method(self):
        # éviter exécution multiple
        if self.env.context.get('fix_done'):
            return

        partners = self.search([
            ('invoice_sending_method', '=', False)
        ])

        if partners:
            partners.with_context(fix_done=True).write({
                'invoice_sending_method': 'email'
            })
            
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'country_id' in fields_list:
            res['country_id'] = self.env.ref('base.cd').id  # RDC
        return res
    
    # code de connexion with account.move
    @api.model_create_multi
    def create(self, vals_list):

        country = self.env.ref('base.cd').id

        for vals in vals_list:
            vals['country_id'] = country        #SP

        partners = super(Partner, self).create(vals_list)
        auto_invoice = self.env['ir.config_parameter'].sudo().get_param('recouvrement_drc.auto_create_invoice')
        
        if auto_invoice:
            for partner in partners:
                if partner.regime_cotisation:
                    partner._create_initial_draft_invoice()
        return partners

    def write(self, vals):
        """ Déclenche la facture si le régime est ajouté après la création """
        if 'country_id' in vals:
            vals['country_id'] = self.env.ref('base.cd').id #SP
        
        res = super(Partner, self).write(vals)
        auto_invoice = self.env['ir.config_parameter'].sudo().get_param('recouvrement_drc.auto_create_invoice')
        
        if auto_invoice and 'regime_cotisation' in vals and vals['regime_cotisation']:
            for partner in self:
                # On vérifie s'il n'a pas déjà de facture pour éviter les doublons
                existing_invoice = self.env['account.move'].search_count([
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', 'out_invoice')
                ])
                if existing_invoice == 0:
                    partner._create_initial_draft_invoice()
        return res

    def _create_initial_draft_invoice(self):
        # CRUCIAL : On cherche dans product.product même si le champ est défini dans template
        # Car regime_cotisation est délégué aux variantes automatiquement
        product = self.env['product.product'].search([
            ('regime_cotisation', '=', self.regime_cotisation),
            ('active', '=', True)
        ], limit=1)

        if product:
            try:
                self.env['account.move'].create({
                    'move_type': 'out_invoice',
                    'partner_id': self.id,
                    'invoice_date': fields.Date.today(),
                    'invoice_line_ids': [(0, 0, {
                        'product_id': product.id,
                        'quantity': 1.0,
                        'price_unit': product.list_price, # Utilise le prix auto-extrait
                    })],
                })
                _logger.info("Facture auto-générée pour le client %s", self.name)
            except Exception as e:
                _logger.error("Erreur lors de la création de facture : %s", str(e))