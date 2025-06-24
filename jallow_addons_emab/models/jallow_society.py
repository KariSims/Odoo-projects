from odoo import fields, models, api

class PartnerSociety(models.Model):
    _name = 'jallow.society'
    _description = 'Société'

    name = fields.Char(string='Société')

    id_ese = fields.Char(string='ID Société', default='/', readonly=True)
    commercial_ids = fields.One2many("jallow.commercial", "ese", string="Commercial")
    supervisor_ids = fields.One2many("jallow.supervisor", "ese", string="Superviseur")
    soldier_ids = fields.One2many("jallow.soldier", "ese", string="Merchandiser")
    team_co_required = fields.Boolean(compute="_compute_required")
    team_su_required = fields.Boolean(compute="_compute_required")
    team_so_required = fields.Boolean(compute="_compute_required")
    team_so2_required = fields.Boolean(compute="_compute_required")
    
    @api.depends('commercial_ids',
                 'supervisor_ids',
                 'soldier_ids')
    # @api.depends('commercial_ids')
    def _compute_required(self):
        for record in self:
            record.team_co_required = False
            record.team_su_required = False
            record.team_so_required = False
            record.team_so2_required = False
            if record.commercial_ids:
                record.team_co_required = True
            if record.supervisor_ids:
                record.team_su_required = True
            if record.soldier_ids:
                record.team_so_required = True
            if record.soldier_ids2:
                record.team_so2_required = True
                
    @api.model
    def create(self, vals):
        if vals.get('id_ese', '/') == '/':  # Si id_ese non défini
            vals['id_ese'] = self.env['ir.sequence'].next_by_code('jallow.society.seq') or '/'
        return super(PartnerSociety, self).create(vals)
    