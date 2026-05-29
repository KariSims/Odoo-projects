from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo import _
from datetime import datetime


class HotelBooking(models.Model):
    _name = 'hotel.booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hotel Booking'


    name = fields.Char(string='Booking ID', required=True, copy=False, readonly=True, default=lambda self: 'New')
    guest_id = fields.Many2one('hotel.customer', string='Customer', required=True, ondelete='cascade')
    room_type = fields.Selection([
        ('single', 'Single'),
        ('double', 'Double'),
        ('suite', 'Suite')
    ], string='Room Type')
    room_id = fields.Many2one('hotel.room', string="Room")
    room_number = fields.Char(string="Room Number", readonly=True)
    is_ac = fields.Selection([
        ('ac', 'AC'),
        ('non_ac', 'Non AC')
    ], string="AC/Non-AC")
    adults = fields.Integer(string="Adults", compute='_compute_adults', inverse='_inverse_adults', store=True)
    kids = fields.Integer(string="Kids", compute='_compute_kids', inverse='_inverse_kids', store=True)
    kids_above_6 = fields.Integer(string="Kids Above 6 Years", compute='_compute_kids_above_6', inverse='_inverse_kids_above_6', store=True)
    no_of_persons = fields.Char(string="No of Person's", readonly=True)
    check_in = fields.Datetime(string='Check In', required=True)
    check_out = fields.Datetime(string='Check Out', required=True)
    total_nights = fields.Integer(string='Total Nights', compute='_compute_total_nights', store=True)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='status')
    available_room_ids = fields.Many2many('hotel.room', string='Available Rooms', compute='_compute_available_rooms')
    invoice_ids = fields.One2many(
        'account.move',
        'hotel_booking_id',
        string="Invoices"
    )
    is_invoice_created = fields.Boolean(string="Invoice Created", default=False)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    invoice_count = fields.Integer(string='Invoice Count',compute='_compute_invoice_count')
    extra_beds = fields.Integer(string='Extra Beds', default=0)
    extra_bed_charge = fields.Float(string='Extra Bed Charge', compute='_compute_extra_bed_charge', store=True)
    booking_ids = fields.One2many('hotel.booking', 'guest_id', string='Bookings')
    booking_count = fields.Integer(string='Booking Count', compute='_compute_booking_count')

    def _compute_invoice_count(self):
        for record in self:
            invoices = self.env['account.move'].search([
                ('hotel_booking_id', '=', record.id),
                ('move_type', '=', 'out_invoice')
            ])
            record.invoice_count = len(invoices)

    def action_print_booking_report(self):
        self.ensure_one()
        return self.env.ref('hotel_management.report_action_hotel_booking_pdf').report_action(self)

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for customer in self:
            customer.booking_count = len(customer.booking_ids)

    @api.depends('guest_id')
    def _compute_adults(self):
        for booking in self:
            if booking.guest_id:
                booking.adults = booking.guest_id.adults
            else:
                booking.adults = 1

    def _inverse_adults(self):
        for booking in self:
            if booking.guest_id:
                booking.guest_id.adults = booking.adults

    @api.depends('guest_id')
    def _compute_kids(self):
        for booking in self:
            booking.kids = booking.guest_id.kids if booking.guest_id else 0

    def _inverse_kids(self):
        for booking in self:
            if booking.guest_id:
                booking.guest_id.kids = booking.kids

    @api.depends('guest_id')
    def _compute_kids_above_6(self):
        for booking in self:
            booking.kids_above_6 = booking.guest_id.kids_above_6 if booking.guest_id else 0

    def _inverse_kids_above_6(self):
        for booking in self:
            if booking.guest_id:
                booking.guest_id.kids_above_6 = booking.kids_above_6

    @api.depends('extra_beds', 'room_id.extra_bed_charge')
    def _compute_extra_bed_charge(self):
        for rec in self:
            rec.extra_bed_charge = rec.extra_beds * rec.room_id.extra_bed_charge

    @api.depends('check_in', 'check_out')
    def _compute_total_nights(self):
        for booking in self:
            if booking.check_in and booking.check_out:
                delta = booking.check_out - booking.check_in
                booking.total_nights = delta.days
            else:
                booking.total_nights = 0

    @api.depends('check_in', 'check_out', 'room_id.price_per_night', 'room_id.extra_bed_charge', 'adults', 'kids_above_6', 'extra_beds')
    def _compute_total_amount(self):
        for rec in self:
            if rec.check_in and rec.check_out and rec.room_id:
                duration = (rec.check_out - rec.check_in).days or 1
                adult_price = rec.adults * rec.room_id.price_per_night * duration
                kids_price = rec.kids_above_6 * (rec.room_id.price_per_night / 2) * duration
                extra_bed_price = rec.extra_beds * rec.room_id.extra_bed_charge * duration
                rec.total_amount = adult_price + kids_price + extra_bed_price
            else:
                rec.total_amount = 0.0

    @api.depends('room_type', 'is_ac', 'check_in', 'check_out')
    def _compute_available_rooms(self):
        for booking in self:
            if booking.room_type and booking.is_ac and booking.check_in and booking.check_out:
                booking.available_room_ids = self._get_available_rooms(
                    booking.room_type,
                    booking.is_ac,
                    booking.check_in,
                    booking.check_out
                )
            else:
                booking.available_room_ids = False


    def _get_available_rooms(self, room_type, is_ac, check_in, check_out):
        domain = [
            ('room_type', '=', room_type),
            ('is_ac', '=', is_ac),
            ('status', '=', 'available')
        ]
        potential_rooms = self.env['hotel.room'].search(domain)
        available_rooms = self.env['hotel.room']
        for room in potential_rooms:
            overlap = self.search_count([
                ('room_id', '=', room.id),
                ('state', 'in', ['confirmed', 'paid']),
                ('check_in', '<', check_out),
                ('check_out', '>', check_in)
            ])
            if not overlap:
                available_rooms += room
        return available_rooms

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.booking') or '/'

            if vals.get('room_type') and vals.get('is_ac'):
                available_rooms = self._get_available_rooms(
                    vals['room_type'],
                    vals['is_ac'],
                    vals.get('check_in'),
                    vals.get('check_out')
                )

                if available_rooms:
                    room = available_rooms[0]
                    vals.update({
                        'room_id': room.id,
                        'room_number': room.name
                    })
                    room.status = 'not_available'
                else:
                    raise ValidationError(
                        "No available rooms matching your criteria. \n\n"
                        "Suggestions:\n"
                        "- Try different dates\n"
                        "- Consider a different room type\n"
                        "- Contact reception for assistance"
                    )


        records = super().create(vals_list)
        for record in records:
            if record.room_id:
                record.room_id.status = 'not_available'

        return records
    @api.onchange('guest_id')
    def _onchange_guest_id(self):
        if self.guest_id:
            self.adults = self.guest_id.adults


    @api.constrains('room_id', 'check_in', 'check_out')
    def _check_room_double_booking(self):
        for rec in self:
            if rec.room_id and rec.check_in and rec.check_out:
                overlap = self.search([
                    ('id', '!=', rec.id),
                    ('room_id', '=', rec.room_id.id),
                    ('state', 'in', ['confirmed', 'paid']),
                    ('check_in', '<=', rec.check_out),
                    ('check_out', '>=', rec.check_in)
                ])
                if overlap:
                    raise ValidationError(f"Room '{rec.room_id.name}' is already booked during this period.")


    def action_confirm(self):
        for rec in self:
            if not rec.room_id:
                available_rooms = self._get_available_rooms(
                    rec.room_type,
                    rec.is_ac,
                    rec.check_in,
                    rec.check_out
                )
                if available_rooms:
                    rec.room_id = available_rooms[0]
                    rec.room_number = available_rooms[0].name
                else:
                    raise UserError("No available rooms found. Please contact reception.")

            rec.state = 'confirmed'
            if rec.room_id:
                rec.room_id.status = 'not_available'

    def action_paid(self):
        for rec in self:
            rec.state = 'paid'
            if rec.room_id:
                rec.room_id.status = 'not_available'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.is_invoice_created = False

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            if rec.room_id:
                rec.room_id.status = 'available'

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('hotel_booking_id', '=', self.id)],
            'target': 'current',
            'context': {'create': False}
        }

    def create_invoice(self):
        self.ensure_one()

        if not self.guest_id.partner_id:
            raise UserError(_("Customer must have a linked partner!"))

        if self.is_invoice_created:
            raise UserError(_("Invoice already created for this booking!"))

        invoice_lines = [{
            'name': f"Room {self.room_number} ({self.room_type}) - {self.total_nights} nights",
            'quantity': 1,
            'price_unit': self.total_amount,
            'account_id': self._get_income_account().id,
        }]

        if self.extra_beds > 0:
            invoice_lines.append({
                'name': f"Extra beds ({self.extra_beds})",
                'quantity': self.extra_beds,
                'price_unit': self.room_id.extra_bed_charge,
                'account_id': self._get_income_account().id,
            })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.guest_id.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': self.name,
            'hotel_booking_id': self.id,
            'invoice_line_ids': [(0, 0, line) for line in invoice_lines],
        })

        # Mark invoice as created
        self.is_invoice_created = True

        return {
            'name': 'Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_income_account(self):
        account = self.env['account.account'].search([
            '|',
            ('name', 'ilike', 'Sales'),
            ('code', 'ilike', '700'),
            ('deprecated', '=', False)
        ], limit=1)

        if not account:
            raise UserError(
                _("No valid income account found. Please configure a Sales account in Accounting > Chart of Accounts."))

        return account


    @api.model
    def update_all_room_availabilities(self):
        rooms = self.env['hotel.room'].search([])
        for room in rooms:
            active_booking = self.search([
                ('room_id', '=', room.id),
                ('state', 'in', ['confirmed', 'paid']),
                ('check_out', '>', fields.Datetime.now())
            ], limit=1)
            room.status = not bool(active_booking)


