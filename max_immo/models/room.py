# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date


class MaxImmoRoom(models.Model):
    _name = 'max.immo.room'
    _description = 'Chambre / Unité'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'property_id, floor, name'

    name = fields.Char(string='Nom / Numéro', required=True, tracking=True)
    property_id = fields.Many2one(
        'max.immo.property', string='Propriété',
        required=True, ondelete='cascade', tracking=True,
        index=True,
    )
    room_type_id = fields.Many2one(
        'max.immo.room.type', string='Type',
        tracking=True,
    )
    floor = fields.Integer(string='Étage', default=0)
    area = fields.Float(string='Surface (m²)', digits=(6, 1))
    rent_price = fields.Float(string='Loyer Mensuel', digits=(10, 2))
    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes internes')
    active = fields.Boolean(default=True)

    state = fields.Selection([
        ('available', 'Disponible'),
        ('occupied', 'Occupée'),
        ('reserved', 'Réservée'),
        ('maintenance', 'En Maintenance'),
    ], string='État', default='available', required=True, tracking=True)

    # Kanban color based on state
    color = fields.Integer(string='Couleur', compute='_compute_color')

    occupation_ids = fields.One2many(
        'max.immo.occupation', 'room_id',
        string='Historique Occupations',
    )
    occupation_count = fields.Integer(
        string='Nb. Occupations',
        compute='_compute_occupation_count',
    )

    # --- Factures / Charges ---
    bill_ids = fields.One2many(
        'max.immo.bill', 'room_id',
        string='Factures',
    )
    pending_bills_count = fields.Integer(
        string='Factures en attente',
        compute='_compute_bill_stats',
    )
    overdue_bills_count = fields.Integer(
        string='Factures en retard',
        compute='_compute_bill_stats',
    )

    # --- Occupation actuelle (calculé) ---
    current_occupation_id = fields.Many2one(
        'max.immo.occupation',
        string='Occupation en cours',
        compute='_compute_current_occupation',
        store=True,
    )
    current_tenant_id = fields.Many2one(
        'res.partner', string='Locataire actuel',
        compute='_compute_current_occupation',
        store=True,
    )
    occupation_start_date = fields.Date(
        string='Occupée depuis',
        compute='_compute_current_occupation',
        store=True,
    )

    # --- Durées (non stockées — toujours à jour) ---
    occupation_duration_days = fields.Integer(
        string='Durée occupation (jours)',
        compute='_compute_durations',
        help="Nombre de jours depuis le début de l'occupation en cours.",
    )
    days_since_vacant = fields.Integer(
        string='Inoccupée depuis (jours)',
        compute='_compute_durations',
        help="Nombre de jours depuis la dernière libération.",
    )

    # Date de dernière libération (stockée pour faciliter les recherches)
    last_vacated_date = fields.Date(
        string='Dernière libération',
        compute='_compute_last_vacated',
        store=True,
    )

    # --- Computed methods ---

    @api.depends('occupation_ids', 'occupation_ids.state')
    def _compute_current_occupation(self):
        for room in self:
            active_occ = room.occupation_ids.filtered(lambda o: o.state == 'active')
            occ = active_occ[:1]
            room.current_occupation_id = occ
            room.current_tenant_id = occ.tenant_id if occ else False
            room.occupation_start_date = occ.start_date if occ else False

    @api.depends('occupation_ids.state', 'occupation_ids.actual_end_date')
    def _compute_last_vacated(self):
        for room in self:
            ended = room.occupation_ids.filtered(
                lambda o: o.state == 'ended' and o.actual_end_date
            )
            if ended:
                last = ended.sorted('actual_end_date', reverse=True)[:1]
                room.last_vacated_date = last.actual_end_date
            else:
                room.last_vacated_date = False

    @api.depends('state', 'occupation_start_date', 'last_vacated_date')
    def _compute_durations(self):
        today = date.today()
        for room in self:
            if room.state == 'occupied' and room.occupation_start_date:
                room.occupation_duration_days = (today - room.occupation_start_date).days
                room.days_since_vacant = 0
            elif room.state in ('available', 'reserved') and room.last_vacated_date:
                room.days_since_vacant = (today - room.last_vacated_date).days
                room.occupation_duration_days = 0
            else:
                room.occupation_duration_days = 0
                room.days_since_vacant = 0

    @api.depends('state')
    def _compute_color(self):
        color_map = {
            'available': 10,     # vert
            'occupied': 1,       # rouge
            'reserved': 3,       # jaune
            'maintenance': 2,    # orange
        }
        for room in self:
            room.color = color_map.get(room.state, 0)

    def _compute_occupation_count(self):
        occ_data = self.env['max.immo.occupation']._read_group(
            [('room_id', 'in', self.ids)],
            ['room_id'],
            ['__count'],
        )
        count_map = {room.id: count for room, count in occ_data}
        for room in self:
            room.occupation_count = count_map.get(room.id, 0)

    def _compute_bill_stats(self):
        today = date.today()
        for room in self:
            pending = room.bill_ids.filtered(lambda b: b.state == 'pending')
            room.pending_bills_count = len(pending)
            room.overdue_bills_count = len(
                pending.filtered(lambda b: b.due_date and b.due_date < today)
            )

    # --- Actions ---

    def action_set_available(self):
        self.write({'state': 'available'})

    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_set_reserved(self):
        self.write({'state': 'reserved'})

    def action_new_occupation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvelle Occupation',
            'res_model': 'max.immo.occupation',
            'view_mode': 'form',
            'context': {
                'default_room_id': self.id,
                'default_property_id': self.property_id.id,
            },
            'target': 'new',
        }

    def action_view_occupations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Occupations — {self.name}',
            'res_model': 'max.immo.occupation',
            'view_mode': 'list,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }

    def action_view_bills(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Factures — {self.name}',
            'res_model': 'max.immo.bill',
            'view_mode': 'list,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }

    def action_new_bill(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvelle Facture',
            'res_model': 'max.immo.bill',
            'view_mode': 'form',
            'context': {
                'default_room_id': self.id,
                'default_property_id': self.property_id.id,
            },
            'target': 'new',
        }
