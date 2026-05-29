# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MaxImmoPayment(models.Model):
    _name = 'max.immo.payment'
    _description = 'Règlement / Paiement Locataire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'payment_datetime desc'
    _rec_name = 'reference'

    # ── Référence auto ─────────────────────────────────────────────────
    reference = fields.Char(
        string='Référence', readonly=True, default='/',
        copy=False, tracking=True,
    )

    # ── Liens contextuels ──────────────────────────────────────────────
    occupation_id = fields.Many2one(
        'max.immo.occupation', string='Occupation',
        ondelete='cascade', tracking=True, index=True,
    )
    bill_id = fields.Many2one(
        'max.immo.bill', string='Facture liée',
        ondelete='set null', tracking=True,
    )

    # ── Qui paie ───────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Payé par',
        required=True, tracking=True,
        help="Locataire ou partenaire ayant effectué le règlement (issu de res.partner).",
    )

    # ── Localisation déduite ───────────────────────────────────────────
    room_id = fields.Many2one(
        'max.immo.room', string='Chambre',
        compute='_compute_location', store=True, readonly=True,
    )
    property_id = fields.Many2one(
        'max.immo.property', string='Propriété',
        compute='_compute_location', store=True, readonly=True,
    )

    # ── Type et montant ────────────────────────────────────────────────
    payment_type = fields.Selection([
        ('rent',    'Loyer'),
        ('deposit', 'Caution / Dépôt de garantie'),
        ('charge',  'Charge (eau, élec, internet…)'),
        ('repair',  'Réparation / Travaux'),
        ('other',   'Autre'),
    ], string='Type de règlement', required=True, default='rent', tracking=True)

    amount = fields.Float(
        string='Montant (FCFA)', digits=(15, 0),
        required=True, tracking=True,
    )

    # ── Date et heure EXACTES du règlement ─────────────────────────────
    payment_datetime = fields.Datetime(
        string='Date et heure du règlement',
        required=True, default=fields.Datetime.now,
        tracking=True,
        help="Horodatage précis du paiement : date + heure.",
    )
    payment_date = fields.Date(
        string='Date du règlement',
        compute='_compute_payment_date', store=True,
        help="Date seule, calculée depuis l'horodatage (pour les filtres et regroupements).",
    )
    payment_day = fields.Integer(
        string='Jour du mois',
        compute='_compute_payment_date', store=True,
        help="Jour du mois du règlement (1–31), utile pour analyser les habitudes de paiement.",
    )
    payment_month = fields.Char(
        string='Mois',
        compute='_compute_payment_date', store=True,
    )

    # ── Mode de paiement ──────────────────────────────────────────────
    payment_method = fields.Selection([
        ('cash',          'Espèces'),
        ('bank_transfer', 'Virement bancaire'),
        ('check',         'Chèque'),
        ('mobile_money',  'Mobile Money (Wave / Orange Money…)'),
        ('other',         'Autre'),
    ], string='Mode de paiement', default='cash', required=True, tracking=True)

    # ── Références externes ────────────────────────────────────────────
    reference_ext = fields.Char(
        string='Réf. externe',
        help='Numéro de reçu, bordereau bancaire, numéro de chèque, ID transaction mobile…',
    )
    period_label = fields.Char(
        string='Période concernée',
        help="Libellé libre : ex. «Loyer Mars 2026», «Eau Janv–Fév 2026».",
    )

    # ── État ───────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft',     'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('cancelled', 'Annulé'),
    ], string='État', default='confirmed', required=True, tracking=True)

    notes = fields.Text(string='Observations')

    confirmed_by = fields.Many2one(
        'res.users', string='Enregistré par',
        default=lambda self: self.env.user,
        readonly=True, tracking=True,
    )

    # ── Computed ───────────────────────────────────────────────────────

    @api.depends('occupation_id', 'occupation_id.room_id',
                 'occupation_id.property_id')
    def _compute_location(self):
        for pay in self:
            pay.room_id = pay.occupation_id.room_id if pay.occupation_id else False
            pay.property_id = pay.occupation_id.property_id if pay.occupation_id else False

    @api.depends('payment_datetime')
    def _compute_payment_date(self):
        for pay in self:
            if pay.payment_datetime:
                dt = pay.payment_datetime
                pay.payment_date = dt.date()
                pay.payment_day = dt.day
                pay.payment_month = dt.strftime('%m/%Y')
            else:
                pay.payment_date = False
                pay.payment_day = 0
                pay.payment_month = ''

    # ── Onchange ───────────────────────────────────────────────────────

    @api.onchange('occupation_id')
    def _onchange_occupation(self):
        """Auto-remplit le partenaire depuis l'occupation sélectionnée."""
        if self.occupation_id and self.occupation_id.tenant_id:
            self.partner_id = self.occupation_id.tenant_id

    @api.onchange('bill_id')
    def _onchange_bill(self):
        """Auto-remplit le montant et la période depuis la facture."""
        if self.bill_id:
            self.amount = self.bill_id.amount
            self.payment_type = 'charge'
            if self.bill_id.display_name:
                self.period_label = self.bill_id.display_name

    # ── CRUD ───────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', '/') == '/':
                vals['reference'] = (
                    self.env['ir.sequence'].next_by_code('max.immo.payment') or '/'
                )
            # S'assurer que confirmed_by est rempli
            if not vals.get('confirmed_by'):
                vals['confirmed_by'] = self.env.user.id
        return super().create(vals_list)

    # ── Actions ────────────────────────────────────────────────────────

    def action_confirm(self):
        for pay in self:
            if pay.state != 'draft':
                raise UserError(_("Seuls les règlements en brouillon peuvent être confirmés."))
            pay.write({'state': 'confirmed'})

    def action_cancel(self):
        for pay in self:
            if pay.state == 'confirmed':
                # Si ce règlement était lié à une facture payée, on la remet en attente
                if pay.bill_id and pay.bill_id.state == 'paid':
                    pay.bill_id.write({
                        'state': 'pending',
                        'payment_date': False,
                        'payment_ref': False,
                    })
            pay.write({'state': 'cancelled'})

    def action_reset_draft(self):
        for pay in self:
            if pay.state != 'cancelled':
                raise UserError(_("Seuls les règlements annulés peuvent être remis en brouillon."))
            pay.write({'state': 'draft'})
