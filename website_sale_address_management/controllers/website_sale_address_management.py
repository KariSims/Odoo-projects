# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Sruthi Renjith (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.tools import single_email_re


class CustomWebsiteSale(WebsiteSale):
    """class used to monkey patch functions in class WebsiteSale"""

    def _get_mandatory_delivery_address_fields(self, country_sudo):
        """ Function to get all the mandatory fields of delivery address """
        mandatory_fields = super()._get_mandatory_delivery_address_fields(country_sudo)
        # Checking for custom mandatory fields.
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_shipping_phone_is_required'):
            mandatory_fields.remove('phone')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_shipping_zip_code_is_required'):
            if "zip" in mandatory_fields:
                mandatory_fields.remove('zip')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_shipping_street_is_required'):
            mandatory_fields.remove('street')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_shipping_city_is_required'):
            mandatory_fields.remove('city')
        return mandatory_fields

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """ Function to get all the mandatory fields of billing address """
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo)
        # Checking for custom mandatory fields.
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_billing_phone_is_required'):
            mandatory_fields.remove('phone')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_billing_zip_code_is_required'):
            if "zip" in mandatory_fields:
                mandatory_fields.remove('zip')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_billing_street_is_required'):
            mandatory_fields.remove('street')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_billing_city_is_required'):
            mandatory_fields.remove('city')
        return mandatory_fields

    def _validate_address_values(
        self,
        address_values,
        partner_sudo,
        address_type,
        use_delivery_as_billing,
        required_fields,
        is_main_address,
        **_kwargs,
    ):
        """ Function for validating fields """
        # data: values after preprocess
        invalid_fields = set()
        missing_fields = set()
        error_messages = []
        if partner_sudo:
            name_change = (
                'name' in address_values
                and partner_sudo.name
                and address_values['name'] != partner_sudo.name
            )
            email_change = (
                'email' in address_values
                and partner_sudo.email
                and address_values['email'] != partner_sudo.email
            )
            # Prevent changing the partner name if invoices have been issued.
            if name_change and not partner_sudo._can_edit_name():
                invalid_fields.add('name')
                error_messages.append(_(
                    "Changing your name is not allowed once invoices have been issued for your"
                    " account. Please contact us directly for this operation."
                ))
            # Prevent changing the partner name or email if it is an internal user.
            if (name_change or email_change) and not all(partner_sudo.user_ids.mapped('share')):
                if name_change:
                    invalid_fields.add('name')
                if email_change:
                    invalid_fields.add('email')
                error_messages.append(_(
                    "If you are ordering for an external person, please place your order via the"
                    " backend. If you wish to change your name or email address, please do so in"
                    " the account settings or contact your administrator."
                ))
            # Prevent changing the VAT number if invoices have been issued.
            if (
                'vat' in address_values
                and address_values['vat'] != partner_sudo.vat
                and not partner_sudo.can_edit_vat()
            ):
                invalid_fields.add('vat')
                error_messages.append(_(
                    "Changing VAT number is not allowed once document(s) have been issued for your"
                    " account. Please contact us directly for this operation."
                ))
        # Validate the email.
        if address_values.get('email') and not single_email_re.match(address_values['email']):
            invalid_fields.add('email')
            error_messages.append(_("Invalid Email! Please enter a valid email address."))
        # Validate the VAT number.
        ResPartnerSudo = request.env['res.partner'].sudo()
        if (
            address_values.get('vat') and hasattr(ResPartnerSudo, 'check_vat')
            and 'vat' not in invalid_fields
        ):
            partner_dummy = ResPartnerSudo.new({
                fname: address_values[fname]
                for fname in self._get_vat_validation_fields()
                if fname in address_values
            })
            try:
                partner_dummy.check_vat()
            except ValidationError as exception:
                invalid_fields.add('vat')
                error_messages.append(exception.args[0])
        # Build the set of required fields from the address form's requirements.
        required_field_set = {f for f in required_fields.split(',') if f}
        # Complete the set of required fields based on the address type.
        country_id = address_values.get('country_id')
        country = request.env['res.country'].browse(country_id)
        if address_type == 'delivery' or use_delivery_as_billing:
            required_field_set |= self._get_mandatory_delivery_address_fields(country)
        if address_type == 'billing' or use_delivery_as_billing:
            required_field_set |= self._get_mandatory_billing_address_fields(country)
            if not is_main_address:
                commercial_fields = ResPartnerSudo._commercial_fields()
                for fname in commercial_fields:
                    if fname in required_field_set and fname not in address_values:
                        required_field_set.remove(fname)
        if address_type == 'delivery':
            # Checking for delivery address required fields and removing it if
            # present in the required fields list.
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_shipping_phone_is_required'):
                if 'phone' in required_field_set:
                    required_field_set.remove('phone')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_shipping_zip_code_is_required'):
                if 'zip' in required_field_set:
                    required_field_set.remove('zip')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_shipping_street_is_required'):
                if 'street' in required_field_set:
                    required_field_set.remove('street')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_shipping_city_is_required'):
                if 'city' in required_field_set:
                    required_field_set.remove('city')
        elif address_type == 'billing':
            # Checking for billing address required fields and removing it if
            # present in the required fields list.
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_billing_phone_is_required'):
                if 'phone' in required_field_set:
                    required_field_set.remove('phone')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_billing_zip_code_is_required'):
                if 'zip' in required_field_set:
                    required_field_set.remove('zip')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_billing_street_is_required'):
                if 'street' in required_field_set:
                    required_field_set.remove('street')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_billing_city_is_required'):
                if 'city' in required_field_set:
                    required_field_set.remove('city')
        # Verify that no required field has been left empty.
        for field_name in required_field_set:
            if not address_values.get(field_name):
                missing_fields.add(field_name)
        if missing_fields:
            error_messages.append(_("Some required fields are empty."))
        return invalid_fields, missing_fields, error_messages
