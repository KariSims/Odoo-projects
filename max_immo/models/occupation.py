# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date
from dateutil.relativedelta import relativedelta


class MaxImmoOccupation(models.Model):
    _name = 'max.immo.occupation'
    _description = 'Occupation / Location'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'
    _rec_name = 'name'

    reference = fields.Char(
        string='Référence', readonly=True, default='/',
        copy=False, tracking=True,
    )
    # Nom lisible pour les vues Calendrier et Gantt
    name = fields.Char(
        string='Désignation',
        compute='_compute_name', store=True,
        help="Affiché dans les vues Calendrier et Gantt.",
    )
    property_id = fields.Many2one(
        'max.immo.property', string='Propriété',
        related='room_id.property_id', store=True, readonly=True,
    )
    room_id = fields.Many2one(
        'max.immo.room', string='Chambre / Unité',
        required=True, ondelete='restrict', tracking=True,
        domain="[('state', 'in', ['available', 'reserved'])]",
    )
    room_type_id = fields.Many2one(
        'max.immo.room.type', string='Type',
        related='room_id.room_type_id', store=True, readonly=True,
    )
    tenant_id = fields.Many2one(
        'res.partner', string='Locataire',
        required=True, tracking=True,
    )

    start_date = fields.Date(
        string='Date d\'entrée',
        required=True, default=fields.Date.today, tracking=True,
    )
    expected_end_date = fields.Date(
        string='Date de sortie prévue', tracking=True,
    )
    actual_end_date = fields.Date(
        string='Date de sortie effective', tracking=True,
        readonly=True,
    )

    state = fields.Selection([
        ('active', 'En cours'),
        ('ended', 'Terminée'),
        ('cancelled', 'Annulée'),
    ], string='État', default='active', required=True, tracking=True)

    rent_amount = fields.Float(
        string='Loyer Mensuel',
        related='room_id.rent_price', store=True, readonly=False,
        digits=(15, 0),
    )
    notes = fields.Text(string='Notes')

    # ── Règlements ─────────────────────────────────────────────────────
    payment_ids = fields.One2many(
        'max.immo.payment', 'occupation_id',
        string='Règlements',
    )
    payment_count = fields.Integer(
        string='Nb. règlements',
        compute='_compute_payment_stats',
    )
    total_paid = fields.Float(
        string='Total encaissé (FCFA)',
        compute='_compute_payment_stats',
        digits=(15, 0),
        help="Somme de tous les règlements confirmés sur cette occupation.",
    )
    last_payment_datetime = fields.Datetime(
        string='Dernier règlement le',
        compute='_compute_payment_stats',
        store=True,
    )
    months_elapsed = fields.Integer(
        string='Mois écoulés',
        compute='_compute_balance',
        help="Nombre de mois depuis la date d'entrée (ou jusqu'à la sortie effective).",
    )
    total_expected = fields.Float(
        string='Total attendu (FCFA)',
        compute='_compute_balance',
        digits=(15, 0),
        help="Loyer mensuel × mois écoulés.",
    )
    balance_due = fields.Float(
        string='Solde restant dû (FCFA)',
        compute='_compute_balance',
        digits=(15, 0),
        help="Total attendu − Total encaissé. Positif = locataire doit encore payer.",
    )

    # ── Champs pour Calendrier et Gantt ───────────────────────────────
    display_end_date = fields.Date(
        string='Date de fin (affichage)',
        compute='_compute_display_end_date', store=True,
        help="Utilisée pour les vues Calendrier et Gantt : "
             "date de sortie effective → prévue → date d'entrée.",
    )
    color_code = fields.Integer(
        string='Code couleur',
        compute='_compute_color_code', store=True,
        help="Couleur Gantt/Calendrier :\n"
             "10 = vert (actif, normal)\n"
             " 2 = orange (fin dans ≤ 30 j)\n"
             " 1 = rouge (en retard)\n"
             " 5 = gris (terminée)\n"
             " 9 = gris clair (annulée)",
    )

    # --- Durées calculées ---
    duration_days = fields.Integer(
        string='Durée totale (jours)',
        compute='_compute_duration',
        help="Jours entre la date d'entrée et la date de sortie (ou aujourd'hui).",
    )
    is_overdue = fields.Boolean(
        string='Délai dépassé',
        compute='_compute_is_overdue',
        help="La date de sortie prévue est dépassée et l'occupation est encore active.",
    )
    days_remaining = fields.Integer(
        string='Jours restants',
        compute='_compute_days_remaining',
        help="Jours restants avant la date de sortie prévue (négatif si dépassé).",
    )

    # ── Computed : nom, dates et couleur pour planning ────────────────

    @api.depends('tenant_id', 'room_id', 'reference')
    def _compute_name(self):
        for occ in self:
            parts = [
                occ.tenant_id.name or '',
                occ.room_id.name or '',
            ]
            occ.name = ' — '.join(filter(None, parts)) or occ.reference or '/'

    @api.depends('actual_end_date', 'expected_end_date', 'start_date')
    def _compute_display_end_date(self):
        for occ in self:
            occ.display_end_date = (
                occ.actual_end_date
                or occ.expected_end_date
                or occ.start_date
            )

    @api.depends('state', 'expected_end_date')
    def _compute_color_code(self):
        today = date.today()
        for occ in self:
            if occ.state == 'cancelled':
                occ.color_code = 9    # gris clair
            elif occ.state == 'ended':
                occ.color_code = 5    # gris
            elif occ.state == 'active':
                if occ.expected_end_date and occ.expected_end_date < today:
                    occ.color_code = 1   # rouge   — en retard
                elif occ.expected_end_date and (occ.expected_end_date - today).days <= 30:
                    occ.color_code = 2   # orange  — fin proche (≤ 30 j)
                else:
                    occ.color_code = 10  # vert    — occupation normale
            else:
                occ.color_code = 0

    # ── Computed règlements ────────────────────────────────────────────

    @api.depends('payment_ids', 'payment_ids.state', 'payment_ids.amount',
                 'payment_ids.payment_datetime')
    def _compute_payment_stats(self):
        for occ in self:
            confirmed = occ.payment_ids.filtered(lambda p: p.state == 'confirmed')
            occ.payment_count = len(occ.payment_ids)
            occ.total_paid = sum(confirmed.mapped('amount'))
            dates = [p.payment_datetime for p in confirmed if p.payment_datetime]
            occ.last_payment_datetime = max(dates) if dates else False

    @api.depends('start_date', 'actual_end_date', 'state',
                 'rent_amount', 'total_paid')
    def _compute_balance(self):
        today = date.today()
        for occ in self:
            if occ.start_date:
                end = occ.actual_end_date or today
                # Nombre de mois complets (au moins 1)
                delta = relativedelta(end, occ.start_date)
                months = delta.years * 12 + delta.months + (1 if delta.days >= 0 else 0)
                months = max(months, 1)
            else:
                months = 0
            occ.months_elapsed = months
            occ.total_expected = months * (occ.rent_amount or 0.0)
            occ.balance_due = occ.total_expected - occ.total_paid

    # --- Computed ---

    @api.depends('start_date', 'actual_end_date', 'state')
    def _compute_duration(self):
        today = date.today()
        for occ in self:
            if occ.start_date:
                end = occ.actual_end_date if occ.actual_end_date else today
                occ.duration_days = (end - occ.start_date).days
            else:
                occ.duration_days = 0

    @api.depends('expected_end_date', 'state')
    def _compute_is_overdue(self):
        today = date.today()
        for occ in self:
            occ.is_overdue = (
                occ.state == 'active'
                and bool(occ.expected_end_date)
                and occ.expected_end_date < today
            )

    @api.depends('expected_end_date', 'state')
    def _compute_days_remaining(self):
        today = date.today()
        for occ in self:
            if occ.state == 'active' and occ.expected_end_date:
                occ.days_remaining = (occ.expected_end_date - today).days
            else:
                occ.days_remaining = 0

    # --- Contraintes ---

    @api.constrains('start_date', 'expected_end_date')
    def _check_dates(self):
        for occ in self:
            if occ.expected_end_date and occ.start_date > occ.expected_end_date:
                raise ValidationError(_(
                    "La date de sortie prévue doit être postérieure à la date d'entrée."
                ))

    @api.constrains('room_id', 'state')
    def _check_room_availability(self):
        for occ in self:
            if occ.state == 'active':
                conflict = self.search([
                    ('room_id', '=', occ.room_id.id),
                    ('state', '=', 'active'),
                    ('id', '!=', occ.id),
                ])
                if conflict:
                    raise ValidationError(_(
                        "La pièce '%s' est déjà occupée (occupation %s en cours)."
                    ) % (occ.room_id.name, conflict[0].reference))

    # --- CRUD overrides ---

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', '/') == '/':
                vals['reference'] = (
                    self.env['ir.sequence'].next_by_code('max.immo.occupation') or '/'
                )
        records = super().create(vals_list)
        for rec in records:
            if rec.state == 'active':
                rec.room_id.write({'state': 'occupied'})
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'state' in vals:
            for occ in self:
                if vals['state'] == 'active':
                    occ.room_id.write({'state': 'occupied'})
                elif vals['state'] in ('ended', 'cancelled'):
                    other_active = self.search([
                        ('room_id', '=', occ.room_id.id),
                        ('state', '=', 'active'),
                        ('id', '!=', occ.id),
                    ])
                    if not other_active:
                        occ.room_id.write({'state': 'available'})
        return result

    # --- Boutons d'action ---

    def action_end_occupation(self):
        for occ in self:
            if occ.state != 'active':
                raise UserError(_("Seules les occupations en cours peuvent être terminées."))
            occ.write({
                'state': 'ended',
                'actual_end_date': fields.Date.today(),
            })
        return True

    def action_cancel(self):
        for occ in self:
            if occ.state == 'ended':
                raise UserError(_("Une occupation terminée ne peut pas être annulée."))
            occ.write({'state': 'cancelled'})
        return True

    def action_add_payment(self):
        """Ouvre le formulaire de saisie d'un nouveau règlement."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Enregistrer un Règlement',
            'res_model': 'max.immo.payment',
            'view_mode': 'form',
            'context': {
                'default_occupation_id': self.id,
                'default_partner_id': self.tenant_id.id,
                'default_payment_type': 'rent',
                'default_amount': self.rent_amount,
            },
            'target': 'new',
        }

    def action_view_payments(self):
        """Vue liste de tous les règlements de cette occupation."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Règlements — {self.reference}',
            'res_model': 'max.immo.payment',
            'view_mode': 'list,form,graph',
            'domain': [('occupation_id', '=', self.id)],
            'context': {
                'default_occupation_id': self.id,
                'default_partner_id': self.tenant_id.id,
            },
        }

    def action_reactivate(self):
        for occ in self:
            if occ.state not in ('cancelled',):
                raise UserError(_("Seules les occupations annulées peuvent être réactivées."))
            occ.write({
                'state': 'active',
                'actual_end_date': False,
            })
        return True
