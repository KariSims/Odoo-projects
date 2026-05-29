from odoo import models, fields, api, _

class RealEstateProperty(models.Model):
    _name = 'real.estate.property'
    _description = 'Real Estate Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    reference = fields.Char(string='Reference', readonly=True, default=lambda self: _('New'), copy=False)
    property_type = fields.Selection([
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('studio', 'Studio'),
        ('commercial', 'Commercial'),
        ('land', 'Land')
    ], string='Property Type', required=True, tracking=True)
    
    status = fields.Selection([
        ('available', 'Available'),
        ('rented', 'Rented'),
        ('sold', 'Sold'),
        ('reserved', 'Reserved')
    ], string='Status', default='available', tracking=True)

    price = fields.Float(string='Selling Price', tracking=True)
    rent_price = fields.Float(string='Monthly Rent', tracking=True)
    
    bedrooms = fields.Integer(string='Bedrooms')
    bathrooms = fields.Integer(string='Bathrooms')
    surface = fields.Float(string='Surface (sqm)')
    furnished = fields.Boolean(string='Furnished')
    
    description = fields.Text(string='Description')
    
    owner_id = fields.Many2one('res.partner', string='Owner', required=True, tracking=True)
    tenant_id = fields.Many2one('res.partner', string='Tenant', tracking=True)
    
    property_image = fields.Binary(string='Image', attachment=True)
    
    address = fields.Char(string='Address')
    city = fields.Char(string='City')
    country_id = fields.Many2one('res.country', string='Country')

    contract_count = fields.Integer(string="Contract Count", compute='_compute_counts')
    maintenance_count = fields.Integer(string="Maintenance Count", compute='_compute_counts')

    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('real.estate.property.code') or _('New')
        return super(RealEstateProperty, self).create(vals)

    def _compute_counts(self):
        for record in self:
            record.contract_count = self.env['real.estate.contract'].search_count([('property_id', '=', record.id)])
            record.maintenance_count = self.env['real.estate.maintenance'].search_count([('property_id', '=', record.id)])

    def action_view_contracts(self):
        return {
            'name': _('Contracts'),
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.contract',
            'view_mode': 'list,form',
            'views': [[False, 'list'], [False, 'form']],
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_view_maintenance(self):
        return {
            'name': _('Maintenance Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.maintenance',
            'view_mode': 'list,form',
            'views': [[False, 'list'], [False, 'form']],
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    @api.model
    def get_dashboard_stats(self):
        # Counts
        total_properties = self.search_count([])
        available_properties = self.search_count([('status', '=', 'available')])
        rented_properties = self.search_count([('status', '=', 'rented')])
        
        # Financials - Monthly Rent Income (from Rented properties)
        # We sum the rent_price of properties that are currently rented
        rented_props = self.search([('status', '=', 'rented')])
        total_rent_income = sum(rented_props.mapped('rent_price'))
        
        # Financials - Total Maintenance Cost
        # Sum of cost of all maintenance requests
        total_maintenance_cost = sum(self.env['real.estate.maintenance'].search([]).mapped('cost'))
        
        return {
            'total_properties': total_properties,
            'available_properties': available_properties,
            'rented_properties': rented_properties,
            'total_rent_income': total_rent_income,
            'total_maintenance_cost': total_maintenance_cost,
        }
