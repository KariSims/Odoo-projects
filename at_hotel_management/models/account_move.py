from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    hotel_booking_id = fields.Many2one(
        'hotel.booking',
        string='Hotel Booking',
        tracking=True
    )
    booking_id = fields.Many2one('hotel.booking', string='Booking Reference')
    guest_id = fields.Many2one('hotel.customer', string="Guest")
    room_id = fields.Many2one('hotel.room', string="Room")
    room_type = fields.Many2one('hotel.room.type', string="Room Type")
    room_type_id = fields.Many2one('hotel.room.type', string="Room Type")
    check_in = fields.Datetime(related='booking_id.check_in', store=True)
    check_out = fields.Datetime(related='booking_id.check_out', store=True)
    total_amount = fields.Float(
        string='Booking Amount',
        related='hotel_booking_id.total_amount',
        readonly=True,
        store=True,
        help="Linked booking's total amount"
    )

    def action_view_hotel_booking(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hotel Booking',
            'res_model': 'hotel.booking',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.hotel_booking_id.id,
        }
