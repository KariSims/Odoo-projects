from odoo import models, fields, api, _

class RealEstateMaintenance(models.Model):
    _name = 'real.estate.maintenance'
    _description = 'Real Estate Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    request_number = fields.Char(string='Request Number', readonly=True, default=lambda self: _('New'), copy=False)
    property_id = fields.Many2one('real.estate.property', string='Property', required=True, tracking=True)
    
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    maintenance_type = fields.Selection([
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('hvac', 'HVAC'),
        ('cleaning', 'Cleaning'),
        ('other', 'Other')
    ], string='Type', required=True)
    
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    cost = fields.Float(string='Cost', tracking=True)
    description = fields.Text(string='Description')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], string='State', default='draft', tracking=True, group_expand='_expand_states')

    @api.model
    def create(self, vals):
        if vals.get('request_number', _('New')) == _('New'):
            vals['request_number'] = self.env['ir.sequence'].next_by_code('real.estate.maintenance.code') or _('New')
        return super(RealEstateMaintenance, self).create(vals)

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})
    
    def action_draft(self):
        self.write({'state': 'draft'})
