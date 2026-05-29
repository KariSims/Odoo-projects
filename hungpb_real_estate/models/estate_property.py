from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

class EstateProperty(models.Model):
   _name = 'estate.property'
   _description = 'Real Estate Property'
   _order = 'id desc'

   name = fields.Char(string='Title', required=True)
   description = fields.Text(string='Description')
   postcode = fields.Char(string='Postcode')
   date_availability = fields.Date(
      string='Available From',
      copy=False,
      default=lambda self: fields.Date.add(fields.Date.today(), days=90)
   )
   expected_price = fields.Float(string='Expected Price', required=True)
   selling_price = fields.Float(string='Selling Price', readonly=True, copy=False)
   bedrooms = fields.Integer(string='Bedrooms', default=2)
   living_area = fields.Integer(string='Living Area (sqm)')
   facades = fields.Integer(string='Facades')
   garage = fields.Boolean(string='Garage')
   garden = fields.Boolean(string='Garden')
   garden_area = fields.Integer(string='Garden Area (sqm)')
   garden_orientation = fields.Selection(
         string='Garden Orientation',
         selection=[
            ('north', 'North'),
            ('south', 'South'),
            ('east', 'East'),
            ('west', 'West')
         ]
   )
   total_area = fields.Integer(string='Total Area (sqm)', compute='_compute_total_area', store=True)
   active = fields.Boolean(string='Active', default=True)
   state = fields.Selection(
      string='Status',
      selection=[
         ('new', 'New'),
         ('offer_received', 'Offer Received'),
         ('offer_accepted', 'Offer Accepted'),
         ('sold', 'Sold'),
         ('canceled', 'Canceled')
      ]   ,
      required=True,
      copy=False,
      default='new'
   )
   property_type_id = fields.Many2one('estate.property.type', string='Property Type', required=True)
   property_tag_ids = fields.Many2many('estate.property.tag', string='Property Tags')
   salesperson_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
   buyer_id = fields.Many2one('res.partner', string='Buyer', copy=False)
   property_offer_ids = fields.One2many('estate.property.offer', 'property_id', string='Property Offers')
   best_offer = fields.Float(string='Best Offer', compute='_compute_best_offer', store=True)

   # FROM ESTATE PROPERTY :
   price = fields.Float(string='Price', required=True)
   status = fields.Selection(
      string='Status',
      selection=[
         ('accepted', 'Accepted'),
         ('refused', 'Refused'),
         ],
      copy=False,
	)
   partner_id = fields.Many2one('res.partner', string='Partner', required=True)
   property_id = fields.Many2one('estate.property', string='Property', required=True)
   validity = fields.Integer(string='Validity (days)', default=7)
   date_deadline = fields.Date(
      string='Deadline',
      compute='_compute_date_deadline',
      inverse='_inverse_date_deadline',
      store=True
	)
   property_type_id = fields.Many2one(
      'estate.property.type',
      string='Property Type',
      # related='property_id.property_type_id',
      store=True
      )

   _sql_constraints = [
      ('check_expected_price_positive', 'CHECK(expected_price > 0)', 'The expected price must be strictly positive.'),
      ('check_selling_price_positive', 'CHECK(selling_price >= 0)', 'The selling price must be positive.')
   ]


   @api.constrains('selling_price', 'expected_price')
   def _check_selling_price_percentage(self):
      for record in self:
         # Skip check if selling_price is zero (no validated offer)
         if not float_is_zero(record.selling_price, precision_digits=2):
            min_price = 0.9 * record.expected_price
         if float_compare(record.selling_price, min_price, precision_digits=2) == -1:
            raise ValidationError("Selling price cannot be lower than 90% of the expected price.")
   
   
   @api.depends('living_area', 'garden_area')
   def _compute_total_area(self):
      for record in self:
         record.total_area = record.living_area + record.garden_area

   
   @api.depends('property_offer_ids.price')
   def _compute_best_offer(self):
      for record in self:  
         best_offer = max(record.property_offer_ids.mapped('price'), default=0.0)
         record.best_offer = best_offer


   @api.onchange('garden')
   def _onchange_garden(self):
      for record in self:
         if record.garden:
            record.garden_area = 10
            record.garden_orientation = 'north'
         else:
            record.garden_area = 0
            record.garden_orientation = False


   def action_set_sold(self):
      for record in self:
         if record.state == 'canceled':
            raise UserError("A canceled property cannot be set as sold.")
         if not record.property_offer_ids.filtered(lambda offer: offer.status == 'accepted'):
            raise UserError("A property cannot be set as sold without an accepted offer.")
         record.state = 'sold'


   def action_set_canceled(self):
      for record in self:
         if record.state == 'sold':
            raise UserError("A sold property cannot be canceled.")
         record.state = 'canceled'


   def action_accept(self):
      for record in self:
         if record.status in ['accepted', 'refused']:
            raise UserError("This offer has already been processed.")
            # Check if another offer is already accepted
         accepted_offer = record.property_id.property_offer_ids.filtered(lambda o: o.status == 'accepted')
         if accepted_offer:
            raise UserError("Only one offer can be accepted per property.")
         record.status = 'accepted'
         # Update property
         record.property_id.selling_price = record.price
         record.property_id.buyer_id = record.partner_id.id
         record.property_id.state = 'offer_accepted'


   def action_refuse(self):
      for record in self:
         if record.status in ['accepted', 'refused']:
            raise UserError("This offer has already been processed.")
         record.status = 'refused'