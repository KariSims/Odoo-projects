from odoo import fields, models, api

class PartnerSociety(models.Model):
    _name = 'jallow.society'
    _description = 'Société'

    name = fields.Char(string='Société')

    id_ese = fields.Char(string='ID Société', default='/', readonly=True)
    commercial_ids = fields.One2many("jallow.commercial", "ese", string="Commercial")
    commercial_required = fields.Boolean(compute="_compute_required")
    
    @api.depends("commercial_ids")
    def _compute_required(self):
        for record in self:
            record.commercial_required = False
            if record.commercial_ids:
                record.commercial_required = True

    @api.model
    def create(self, vals):
        if vals.get('id_ese', '/') == '/':  # Si id_ese non défini
            vals['id_ese'] = self.env['ir.sequence'].next_by_code('jallow.society.seq') or '/'
        return super(PartnerSociety, self).create(vals)
    