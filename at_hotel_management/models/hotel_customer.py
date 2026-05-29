from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HotelCustomer(models.Model):
    _name = 'hotel.customer'
    _description = 'Hotel Customer'

    name = fields.Char(string="Customer Name", required=True)
    phone = fields.Char(string="Phone Number")
    email = fields.Char(string="Email ID")
    address = fields.Text(string="Address")
    id_proof = fields.Binary(string="ID Proof")
    notes = fields.Text(string="Notes")
    image = fields.Image(string="Picture")
    adults = fields.Integer(string="Adults", default="1")
    kids = fields.Integer(string="Total Kids", default=0)
    kids_above_6 = fields.Integer(string="Kids Above 6 Years", default=0)
    no_of_persons = fields.Char(string="No of Person's")
    partner_id = fields.Many2one("res.partner", string="Customer")
    room_type = fields.Many2one('hotel.room', string="Room Type")
    room_id = fields.Many2one('hotel.room', string="Room")
    check_in = fields.Datetime(string="Check-In", default=fields.Datetime.now)
    check_out = fields.Datetime(string="Check-Out")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    total_amount = fields.Float(string="Total Amount")
    booking_ids = fields.One2many(
        'hotel.booking',
        'guest_id',
        string='Bookings History'
    )
    booking_count = fields.Integer(
        string='Booking Count',
        compute='_compute_booking_count'
    )

    def _compute_booking_count(self):
        for customer in self:
            customer.booking_count = self.env['hotel.booking'].search_count([
                ('guest_id', '=', customer.id)
            ])

    @api.depends('partner_id')
    def _compute_invoice_count(self):
        for guest in self:
            guest.invoice_count = self.env['account.move'].search_count([
                ('partner_id', '=', guest.partner_id.id),
                ('move_type', '=', 'out_invoice')
            ])

    def create(self, vals):
        partner = self.env['res.partner'].create({
            'name': vals.get('name'),
            'email': vals.get('email'),
            'phone': vals.get('phone'),
        })
        vals['partner_id'] = partner.id
        return super(HotelCustomer, self).create(vals)

    def action_view_customer_bookings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bookings',
            'view_mode': 'list,form',
            'res_model': 'hotel.booking',
            'domain': [('guest_id', '=', self.id)],
            'context': {'default_guest_id': self.id}
        }
