# -*- coding: utf-8 -*-
from odoo import models, fields


class MaxImmoRoomType(models.Model):
    _name = 'max.immo.room.type'
    _description = 'Type de Pièce'
    _order = 'sequence, name'

    name = fields.Char(string='Type', required=True, translate=True)
    sequence = fields.Integer(string='Séquence', default=10)
    description = fields.Text(string='Description')
    color = fields.Integer(string='Couleur', default=0)
    active = fields.Boolean(default=True)

    room_count = fields.Integer(
        string='Nb. Pièces',
        compute='_compute_room_count',
    )

    def _compute_room_count(self):
        room_data = self.env['max.immo.room']._read_group(
            [('room_type_id', 'in', self.ids)],
            ['room_type_id'],
            ['__count'],
        )
        count_map = {rtype.id: count for rtype, count in room_data}
        for rtype in self:
            rtype.room_count = count_map.get(rtype.id, 0)
