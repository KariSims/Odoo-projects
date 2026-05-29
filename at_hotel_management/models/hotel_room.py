from odoo import models, fields, api
from odoo.exceptions import UserError

class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'
    _order = 'name'

    name = fields.Char(string='Room Number', required=True)
    room_type = fields.Selection([
        ('single', 'Single'),
        ('double', 'Double'),
        ('suite', 'Suite')
    ], string='Room Type', required=True)
    is_ac = fields.Selection([
        ('ac', 'AC'),
        ('non_ac', 'Non AC')
    ], string='AC/Non-AC', required=True)

    price_per_night = fields.Float(string='Price Per Night', required=True)
    status = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ])
    description = fields.Text(string='Description')
    image = fields.Image(string="Image")
    extra_beds = fields.Integer(string='Max Extra Beds', default=0)
    extra_bed_charge = fields.Float(string='Extra Bed Charge', default=0.0)

    def unlink(self):
        for room in self:
            active_bookings = self.env['hotel.booking'].search([
                ('room_id', '=', room.id),
                ('state', 'in', ['draft', 'confirmed', 'paid'])
            ])
            if active_bookings:
                raise UserError(f"Cannot delete room '{room.name}' because it has active bookings.")
        return super(HotelRoom, self).unlink()

    def name_get(self):
        result = []
        for room in self:
            name = f"{room.name} ({room.room_type}, {'AC' if room.is_ac == 'ac' else 'Non-AC'})"
            result.append((room.id, name))
        return result



