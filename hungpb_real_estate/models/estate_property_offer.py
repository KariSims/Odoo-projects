from odoo import models, fields, api
from odoo.exceptions import UserError

class EstatePropertyOffer(models.Model):
	_name = 'estate.property.offer'
	_description = 'Real Estate Property Offer'
	_order = 'price desc'

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
		('check_price_positive', 'CHECK(price > 0)', 'The offer price must be strictly positive.')
	]


	@api.depends('create_date', 'validity')
	def _compute_date_deadline(self):
		for record in self:
			if not record.create_date:
				start_date = fields.Date.today()
			else:
				start_date = record.create_date             
			record.date_deadline = fields.Date.add(start_date, days=record.validity)


	def _inverse_date_deadline(self):
		for record in self:
			if not record.create_date:
				start_date = fields.Date.today()
			else:
				start_date = record.create_date 
			if record.date_deadline:
				delta = (record.date_deadline - start_date.date()).days
				record.validity = delta if delta >= 0 else 0
			else:
					record.validity = 0

	
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


	@api.model
	def create(self, vals):
		# Tạo offer
		offer = super().create(vals)
		# Cập nhật state của property thành 'offer_received'
		if offer.property_id and offer.property_id.state == 'new':
				offer.property_id.state = 'offer_received'
		return offer
