from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MicroZone(models.Model):
    _name = 'micro.zone'
    _description = 'Zone de Collecte'
    _rec_name = 'complete_name'
    _parent_name = 'parent_id'
    _order = 'complete_name'

    name = fields.Char(string="Nom de la zone", required=True)
    code = fields.Char(string="Code", required=True, size=10)
    commission_rate = fields.Float(string="Taux de commission (%)", default=0.0)
    active = fields.Boolean(default=True)

    parent_id = fields.Many2one(
        'micro.zone', string="Zone parente",
        ondelete='restrict', index=True,
    )
    child_ids = fields.One2many('micro.zone', 'parent_id', string="Sous-zones")
    complete_name = fields.Char(
        string="Nom complet",
        compute='_compute_complete_name',
        store=True,
        recursive=True,
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for zone in self:
            if zone.parent_id:
                zone.complete_name = f"{zone.parent_id.complete_name} / {zone.name}"
            else:
                zone.complete_name = zone.name

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(
                "Impossible de créer une hiérarchie circulaire de zones."
            )
