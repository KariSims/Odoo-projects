# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
_logger = logging.getLogger("__name__")
from datetime import datetime
from odoo.http import request, route
from odoo.exceptions import ValidationError
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.tools import clean_context, str2bool, single_email_re
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.translate import _
import json
#from odoo.http import request, route

class WebsiteSaleInherited(WebsiteSale):
    
    def _get_country_related_render_values(self, kw, render_values):
        """ Provide the fields related to the country to render the website sale form """
        values = render_values['checkout']
        mode = render_values['mode']
        order = render_values['website_sale_order']

        def_country_id = order.partner_id.country_id
        if order._is_public_order():
            if request.geoip.country_code:
                def_country_id = request.env['res.country'].search([('code', '=', request.geoip.country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id

        country = 'country_id' in values and values['country_id'] != '' and request.env['res.country'].browse(int(values['country_id']))
        country = country and country.exists() or def_country_id
        #_logger.error("Je suis dans le chargement du pays")
        res = {
            'country': country,
            'country_states': country.get_website_sale_states(mode=mode[1]),
            'countries': country.get_website_sale_countries(mode=mode[1]),
            'country_cities': country.get_website_sale_cities(mode=mode[1]),
            'country_municipalities': country.get_website_sale_municipalities(mode=mode[1]),
        }
        return res
    

    def _prepare_address_form_values(
        self, order_sudo, partner_sudo, address_type, use_delivery_as_billing, callback='', **kwargs
    ):
        """ Prepare and return the values to use to render the address form.

        :param sale.order order_sudo: The current cart.
        :param partner_sudo: The partner whose address to update through the address form.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param bool use_delivery_as_billing: Whether the provided address should be used as both the
                                             billing and the delivery address.
        :param str callback:
        :return: The checkout page values.
        :rtype: dict
        """
        can_edit_vat = (
            (address_type == 'billing' or use_delivery_as_billing)
            and (not partner_sudo or partner_sudo.can_edit_vat())
        )
        is_anonymous_cart = order_sudo._is_anonymous_cart()

        ResCountrySudo = request.env['res.country'].sudo()
        country_sudo = partner_sudo.country_id
        if not country_sudo:
            if is_anonymous_cart:
                if request.geoip.country_code:
                    country_sudo = ResCountrySudo.search([
                        ('code', '=', request.geoip.country_code),
                    ], limit=1)
                else:
                    country_sudo = order_sudo.website_id.user_id.country_id
            else:
                country_sudo = order_sudo.partner_id.country_id

        state_id = partner_sudo.state_id.id
        city_id = partner_sudo.city_id.id
        municipality_id = partner_sudo.municipality_id.id

        address_fields = country_sudo and country_sudo.get_address_fields() or ['city', 'zip']
        ResCitySudo = request.env['res.city'].sudo().search([])
        ResMunicipalitySudo = request.env['res.municipality'].sudo().search([])
        if country_sudo:
            ResCitySudo = request.env['res.city'].sudo().search([('country_id', '=', country_sudo.id)])
        if city_id:
            ResMunicipalitySudo = request.env['res.municipality'].sudo().search([('city_id', '=', city_id)])
        
        return {
            'website_sale_order': order_sudo,
            'partner_sudo': partner_sudo,  # If set, customer is editing an existing address
            'partner_id': partner_sudo.id,
            'address_type': address_type,  # 'billing' or 'delivery'
            'can_edit_vat': can_edit_vat,
            'callback': callback,
            'only_services': order_sudo.only_services,
            'is_anonymous_cart': is_anonymous_cart,
            'use_delivery_as_billing': use_delivery_as_billing,
            'discard_url': is_anonymous_cart and '/shop/cart' or '/shop/checkout',
            'country': country_sudo,
            'countries': ResCountrySudo.search([]),
            'cities': ResCitySudo,
            'municipalities': ResMunicipalitySudo,
            'state_id': state_id,
            'city_id': city_id,
            'municipality_id': municipality_id,
            'country_states': country_sudo.state_ids,
            'zip_before_city': (
                'zip' in address_fields
                and address_fields.index('zip') < address_fields.index('city')
            ),
            'show_vat': (
                (address_type == 'billing' or use_delivery_as_billing)
                and (
                    is_anonymous_cart  # Allow inputting VAT on the new main address.
                    or (
                        partner_sudo == order_sudo.partner_id
                        and (can_edit_vat or partner_sudo.vat)
                    )  # On the main partner only, if the VAT was set.
                )
            ),
            'vat_label': request.env._("VAT"),
        }
        
    @route(['/shop/country_info/<model("res.country"):country>', '/shop/city_info/<model("res.city"):city>'], type='json', auth="public", methods=['POST'], website=True, readonly=True)
    def shop_country_info(self, address_type, country=None, city=None, **kw):
        if country:
            address_fields = country.get_address_fields()
            if address_type == 'billing':
                required_fields = self._get_mandatory_billing_address_fields(country)
            else:
                required_fields = self._get_mandatory_delivery_address_fields(country)
            return {
                'fields': address_fields,
                'zip_before_city': (
                    'zip' in address_fields
                    and address_fields.index('zip') < address_fields.index('city')
                ),
                'states': [(st.id, st.name, st.code) for st in country.sudo().state_ids],
                'cities': [(city.id, city.name) for city in country.sudo().city_ids],
                'phone_code': country.phone_code,
                'required_fields': list(required_fields),
            }
        if city:
            required_fields = self._get_mandatory_city_address_fields(city.sudo())
            return {
                'municipalities': [(muni.id, muni.name) for muni in city.sudo().municipality_ids],
                'required_fields': list(required_fields),
            }          
            

    def _get_mandatory_city_address_fields(self, city_sudo):
        field_names = {}
        if city_sudo.municipality_required:
            field_names = {'municipality_id'}
        return field_names
            

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """ Return the set of common mandatory address fields.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of common mandatory address field names.
        :rtype: set
        """
        field_names = {'name', 'street', 'country_id', 'phone'}
        if country_sudo.state_required and not country_sudo.city_required:
            field_names.add('state_id')
        if country_sudo.zip_required:
            field_names.add('zip')
        if country_sudo.city_required and not country_sudo.state_required:
            field_names.add('city_id')
        if country_sudo.state_required and country_sudo.city_required:
            field_names.add('state_id')
            field_names.add('city_id')
        return field_names
            
    def _get_mandatory_address_fields(self, country_sudo):
        """ Return the set of common mandatory address fields.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of common mandatory address field names.
        :rtype: set
        """
        field_names = {'name', 'street', 'country_id', 'phone'}
        if country_sudo.state_required and not country_sudo.city_required:
            field_names.add('state_id')
        if country_sudo.zip_required:
            field_names.add('zip')
        if country_sudo.city_required and not country_sudo.state_required:
            field_names.add('city_id')
        if country_sudo.state_required and country_sudo.city_required:
            field_names.add('state_id')
            field_names.add('city_id')
        return field_names
    
    
    @route(
        '/shop/address/submit', type='http', methods=['POST'], auth='public', website=True,
        sitemap=False
    )
    def shop_address_submit(
        self, partner_id=None, address_type='billing', use_delivery_as_billing=None, callback=None,
        required_fields=None, **form_data
    ):
        """ Create or update an address.

        If it succeeds, it returns the URL to redirect (client-side) to. If it fails (missing or
        invalid information), it highlights the problematic form input with the appropriate error
        message.

        :param str partner_id: The partner whose address to update with the address form, if any.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param str use_delivery_as_billing: Whether the provided address should be used as both the
                                            billing and the delivery address. 'true' or 'false'.
        :param str callback: The URL to redirect to in case of successful address creation/update.
        :param str required_fields: The additional required address values, as a comma-separated
                                    list of `res.partner` fields.
        :param dict form_data: The form data to process as address values.
        :return: A JSON-encoded feedback, with either the success URL or an error message.
        :rtype: str
        """
        order_sudo = request.website.sale_get_order()
        if redirection := self._check_cart(order_sudo):
            return redirection

        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id and int(partner_id), address_type=address_type
        )
        use_delivery_as_billing = str2bool(use_delivery_as_billing or 'false')
        required_fields = required_fields or ''

        # Parse form data into address values, and extract incompatible data as extra form data.
        address_values, extra_form_data = self._parse_form_data(form_data)

        is_anonymous_cart = order_sudo._is_anonymous_cart()
        is_main_address = is_anonymous_cart or order_sudo.partner_id.id == partner_sudo.id
        # Validate the address values and highlights the problems in the form, if any.
        invalid_fields, missing_fields, error_messages = self._validate_address_values(
            address_values,
            partner_sudo,
            address_type,
            use_delivery_as_billing,
            required_fields,
            is_main_address=is_main_address,
            **extra_form_data,
        )
        _logger.error("invalid_fields init %s", invalid_fields)
        _logger.error("missing_fields init %s", missing_fields)
        if error_messages:
            return json.dumps({
                'invalid_fields': list(invalid_fields | missing_fields),
                'messages': error_messages,
            })
        _logger.error("invalid_fields 2 %s", invalid_fields)
        is_new_address = False
        if not partner_sudo:  # Creation of a new address.
            is_new_address = True
            self._complete_address_values(
                address_values, address_type, use_delivery_as_billing, order_sudo
            )
            create_context = clean_context(request.env.context)
            create_context.update({
                'tracking_disable': True,
                'no_vat_validation': True,  # Already verified in _validate_address_values
            })
            partner_sudo = request.env['res.partner'].sudo().with_context(
                create_context
            ).create(address_values)
        elif not self._are_same_addresses(address_values, partner_sudo):
            partner_sudo.write(address_values)  # Keep the same partner if nothing changed.
        _logger.error("invalid_fields 3 %s", invalid_fields)
        partner_fnames = set()
        if is_main_address:  # Main address updated.
            partner_fnames.add('partner_id')  # Force the re-computation of partner-based fields.

        if address_type == 'billing':
            partner_fnames.add('partner_invoice_id')
            if is_new_address and order_sudo.only_services:
                # The delivery address is required to make the order.
                partner_fnames.add('partner_shipping_id')
            callback = callback or self._get_extra_billing_info_route(order_sudo)
        elif address_type == 'delivery':
            partner_fnames.add('partner_shipping_id')
            if use_delivery_as_billing:
                partner_fnames.add('partner_invoice_id')

        order_sudo._update_address(partner_sudo.id, partner_fnames)

        if is_anonymous_cart:
            # Unsubscribe the public partner if the cart was previously anonymous.
            order_sudo.message_unsubscribe(order_sudo.website_id.partner_id.ids)

        if is_new_address or order_sudo.only_services:
            callback = callback or '/shop/checkout?try_skip_step=true'
        else:
            callback = callback or '/shop/checkout'

        self._handle_extra_form_data(extra_form_data, address_values)

        return json.dumps({
            'successUrl': callback,
        })
        
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
        """ Validate the address values and return the invalid fields, the missing fields, and any
        error messages.

        :param dict address_values: The address values to validates.
        :param res.partner partner_sudo: The partner whose address values to validate, if any (can
                                         be empty).
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param bool use_delivery_as_billing: Whether the provided address should be used as both the
                                             billing and the delivery address.
        :param str required_fields: The additional required address values, as a comma-separated
                                    list of `res.partner` fields.
        :param bool is_main_address: Whether the provided address is meant to be the main address of
                                     the customer.
        :param dict _kwargs: Locally unused parameters including the extra form data.
        :return: The invalid fields, the missing fields, and any error messages.
        :rtype: tuple[set, set, list]
        """
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

        # Verify that no required field has been left empty.
        for field_name in required_field_set:
            if not address_values.get(field_name):
                missing_fields.add(field_name)
        if missing_fields:
            error_messages.append(_("Some required fields are empty."))

        return invalid_fields, missing_fields, error_messages