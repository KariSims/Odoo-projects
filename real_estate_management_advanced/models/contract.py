from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class RealEstateContract(models.Model):
    _name = 'real.estate.contract'
    _description = 'Real Estate Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    contract_number = fields.Char(string='Contract Number', readonly=True, default=lambda self: _('New'), copy=False)
    property_id = fields.Many2one('real.estate.property', string='Property', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer (Tenant/Buyer)', required=True, tracking=True)
    
    contract_type = fields.Selection([
        ('rent', 'Rent'),
        ('sell', 'Sell')
    ], string='Contract Type', required=True, tracking=True)
    
    start_date = fields.Date(string='Start Date', default=fields.Date.today)
    end_date = fields.Date(string='End Date')
    
    monthly_rent = fields.Float(string='Monthly Rent')
    selling_price = fields.Float(string='Selling Price') # Added to capture sale price if selling
    
    payment_method = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('full_payment', 'Full Payment')
    ], string='Payment Method')
    
    notes = fields.Text(string='Notes')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='State', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('contract_number', _('New')) == _('New'):
            vals['contract_number'] = self.env['ir.sequence'].next_by_code('real.estate.contract.code') or _('New')
        return super(RealEstateContract, self).create(vals)

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                continue
                
            record.state = 'confirmed'
            
            if record.contract_type == 'rent':
                record.property_id.write({
                    'status': 'rented',
                    'tenant_id': record.partner_id.id,
                })
            elif record.contract_type == 'sell':
                record.property_id.write({
                    'status': 'sold',
                    'owner_id': record.partner_id.id, # Transfer ownership
                    'tenant_id': False, # Clear tenant if sold
                })
                
    def action_cancel(self):
        self.write({'state': 'cancelled'})
