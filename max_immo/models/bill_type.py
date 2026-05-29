# -*- coding: utf-8 -*-
from odoo import models, fields


class MaxImmoBillType(models.Model):
    _name = 'max.immo.bill.type'
    _description = 'Type de Facture / Charge'
    _order = 'sequence, name'

    name = fields.Char(string='Type', required=True, translate=True)
    sequence = fields.Integer(string='Séquence', default=10)
    description = fields.Text(string='Description')
    color = fields.Integer(string='Couleur', default=0)
    active = fields.Boolean(default=True)

    default_frequency = fields.Selection([
        ('monthly', 'Mensuelle'),
        ('quarterly', 'Trimestrielle'),
        ('biannual', 'Semestrielle'),
        ('annual', 'Annuelle'),
        ('one_time', 'Ponctuelle'),
    ], string='Fréquence par défaut', default='monthly')

    bill_count = fields.Integer(
        string='Nb. Factures',
        compute='_compute_bill_count',
    )

    def _compute_bill_count(self):
        data = self.env['max.immo.bill']._read_group(
            [('bill_type_id', 'in', self.ids)],
            ['bill_type_id'],
            ['__count'],
        )
        count_map = {btype.id: count for btype, count in data}
        for btype in self:
            btype.bill_count = count_map.get(btype.id, 0)
