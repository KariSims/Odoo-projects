# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MaxImmoProperty(models.Model):
    _name = 'max.immo.property'
    _description = 'Propriété Immobilière'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Nom', required=True, tracking=True)
    reference = fields.Char(string='Référence', readonly=True, default='/')
    property_type = fields.Selection([
        ('building', 'Immeuble'),
        ('villa', 'Villa'),
        ('house', 'Maison'),
        ('commercial', 'Local Commercial'),
        ('other', 'Autre'),
    ], string='Type', required=True, default='building', tracking=True)

    address = fields.Char(string='Adresse')
    city = fields.Char(string='Ville')
    country_id = fields.Many2one('res.country', string='Pays')
    description = fields.Text(string='Description')
    image = fields.Image(string='Photo', max_width=1024, max_height=1024)
    active = fields.Boolean(default=True)

    owner_id = fields.Many2one('res.partner', string='Propriétaire', tracking=True)
    manager_id = fields.Many2one('res.users', string='Gestionnaire',
                                  default=lambda self: self.env.user, tracking=True)

    room_ids = fields.One2many('max.immo.room', 'property_id', string='Pièces / Unités')

    # Statistiques calculées
    total_rooms = fields.Integer(
        string='Total Unités',
        compute='_compute_room_stats', store=True,
    )
    available_rooms = fields.Integer(
        string='Disponibles',
        compute='_compute_room_stats', store=True,
    )
    occupied_rooms = fields.Integer(
        string='Occupées',
        compute='_compute_room_stats', store=True,
    )
    reserved_rooms = fields.Integer(
        string='Réservées',
        compute='_compute_room_stats', store=True,
    )
    maintenance_rooms = fields.Integer(
        string='En Maintenance',
        compute='_compute_room_stats', store=True,
    )
    occupancy_rate = fields.Float(
        string='Taux d\'Occupation (%)',
        compute='_compute_room_stats', store=True,
        digits=(5, 1),
    )

    # --- Statistiques factures (toujours fraîches) ---
    pending_bills_count = fields.Integer(
        string='Factures en attente',
        compute='_compute_bill_stats',
    )
    overdue_bills_count = fields.Integer(
        string='Factures en retard',
        compute='_compute_bill_stats',
    )

    @api.depends('room_ids', 'room_ids.state')
    def _compute_room_stats(self):
        for prop in self:
            rooms = prop.room_ids
            total = len(rooms)
            occupied = len(rooms.filtered(lambda r: r.state == 'occupied'))
            available = len(rooms.filtered(lambda r: r.state == 'available'))
            reserved = len(rooms.filtered(lambda r: r.state == 'reserved'))
            maintenance = len(rooms.filtered(lambda r: r.state == 'maintenance'))
            prop.total_rooms = total
            prop.available_rooms = available
            prop.occupied_rooms = occupied
            prop.reserved_rooms = reserved
            prop.maintenance_rooms = maintenance
            prop.occupancy_rate = (occupied / total * 100.0) if total > 0 else 0.0

    def _compute_bill_stats(self):
        from datetime import date
        today = date.today()
        for prop in self:
            all_bills = self.env['max.immo.bill'].search([
                ('property_id', '=', prop.id),
                ('state', '=', 'pending'),
            ])
            prop.pending_bills_count = len(all_bills)
            prop.overdue_bills_count = len(
                all_bills.filtered(lambda b: b.due_date and b.due_date < today)
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', '/') == '/':
                vals['reference'] = self.env['ir.sequence'].next_by_code('max.immo.property') or '/'
        return super().create(vals_list)

    def action_view_rooms(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Pièces — {self.name}',
            'res_model': 'max.immo.room',
            'view_mode': 'kanban,list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_view_occupations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Occupations — {self.name}',
            'res_model': 'max.immo.occupation',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_view_bills(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Factures — {self.name}',
            'res_model': 'max.immo.bill',
            'view_mode': 'list,form,graph',
            'domain': [('property_id', '=', self.id)],
            'context': {
                'default_property_id': self.id,
                'search_default_group_room': 1,
            },
        }

    def action_view_overdue_bills(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Factures en retard — {self.name}',
            'res_model': 'max.immo.bill',
            'view_mode': 'list,form',
            'domain': [
                ('property_id', '=', self.id),
                ('state', '=', 'pending'),
                ('due_date', '<', fields.Date.today()),
            ],
            'context': {'default_property_id': self.id},
        }
