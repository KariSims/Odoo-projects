# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class MaxImmoBill(models.Model):
    _name = 'max.immo.bill'
    _description = 'Facture / Échéance de Charge'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, room_id'
    _rec_name = 'display_name'

    # --- Identification ---
    reference = fields.Char(
        string='Référence facture',
        help="Numéro de facture du fournisseur (eau, EDF, etc.)",
        tracking=True,
    )

    # --- Localisation ---
    room_id = fields.Many2one(
        'max.immo.room', string='Chambre / Unité',
        required=True, ondelete='cascade', tracking=True,
        index=True,
    )
    property_id = fields.Many2one(
        'max.immo.property', string='Propriété',
        related='room_id.property_id', store=True, readonly=True,
        index=True,
    )

    # --- Type et période ---
    bill_type_id = fields.Many2one(
        'max.immo.bill.type', string='Type de Facture',
        required=True, tracking=True,
    )
    period_date = fields.Date(
        string='Période',
        help="Mois/période concerné par cette facture (ex: 01/03/2026 = mars 2026).",
    )
    frequency = fields.Selection(
        related='bill_type_id.default_frequency',
        store=True, readonly=True,
    )

    # --- Montant et échéance ---
    amount = fields.Float(
        string='Montant (FCFA)', digits=(15, 0),
        tracking=True,
    )
    due_date = fields.Date(
        string='Date d\'échéance',
        required=True, tracking=True,
    )

    # --- État ---
    state = fields.Selection([
        ('pending', 'En attente'),
        ('paid', 'Payée'),
        ('cancelled', 'Annulée'),
    ], string='État', default='pending', required=True, tracking=True)

    payment_date = fields.Date(
        string='Date de paiement',
        readonly=True, tracking=True,
    )
    payment_ref = fields.Char(
        string='Référence paiement',
        readonly=True,
    )

    notes = fields.Text(string='Notes')

    # --- Champs calculés ---
    display_name = fields.Char(
        string='Nom', compute='_compute_display_name', store=True,
    )
    is_overdue = fields.Boolean(
        string='En retard',
        compute='_compute_overdue',
        help="Échéance dépassée et facture non payée.",
    )
    days_overdue = fields.Integer(
        string='Jours de retard',
        compute='_compute_overdue',
    )
    days_until_due = fields.Integer(
        string='Jours avant échéance',
        compute='_compute_overdue',
    )

    @api.depends('bill_type_id', 'room_id', 'period_date', 'due_date')
    def _compute_display_name(self):
        for bill in self:
            parts = []
            if bill.bill_type_id:
                parts.append(bill.bill_type_id.name)
            if bill.room_id:
                parts.append(bill.room_id.name)
            if bill.period_date:
                parts.append(bill.period_date.strftime('%m/%Y'))
            bill.display_name = ' — '.join(parts) if parts else '/'

    @api.depends('due_date', 'state')
    def _compute_overdue(self):
        today = date.today()
        for bill in self:
            if bill.state == 'pending' and bill.due_date:
                delta = (today - bill.due_date).days
                bill.is_overdue = delta > 0
                bill.days_overdue = max(delta, 0)
                bill.days_until_due = max(-delta, 0)
            else:
                bill.is_overdue = False
                bill.days_overdue = 0
                bill.days_until_due = 0

    # --- Actions ---

    def action_mark_paid(self):
        """Marque la facture payée et crée automatiquement un règlement tracé."""
        for bill in self:
            if bill.state != 'pending':
                raise UserError(_("Seules les factures en attente peuvent être marquées payées."))

            # Identifier le partenaire payeur (locataire actuel si disponible)
            partner = bill.room_id.current_tenant_id if bill.room_id else False

            # Créer le règlement lié à la facture
            if partner:
                self.env['max.immo.payment'].create({
                    'partner_id': partner.id,
                    'occupation_id': bill.room_id.current_occupation_id.id or False,
                    'bill_id': bill.id,
                    'payment_type': 'charge',
                    'amount': bill.amount,
                    'payment_datetime': fields.Datetime.now(),
                    'period_label': bill.display_name,
                    'state': 'confirmed',
                })

            bill.write({
                'state': 'paid',
                'payment_date': fields.Date.today(),
            })

    def action_reset_to_pending(self):
        for bill in self:
            if bill.state == 'cancelled':
                raise UserError(_("Une facture annulée ne peut pas être remise en attente."))
            bill.write({
                'state': 'pending',
                'payment_date': False,
                'payment_ref': False,
            })

    def action_cancel(self):
        for bill in self:
            if bill.state == 'paid':
                raise UserError(_("Une facture payée ne peut pas être annulée directement. Remettez-la d'abord en attente."))
            bill.write({'state': 'cancelled'})
