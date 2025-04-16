from odoo import _, api, fields, models, registry, Command, SUPERUSER_ID
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)


class AccountPartner(models.Model):
    _inherit = "res.partner"
    
    city_id = fields.Many2one("res.city", string="Ville")
    municipality_id = fields.Many2one("res.municipality", string="Commune")    

    @api.model
    def _get_address_format(self):
        return "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s\n%(municipality_name)s"
        
    def _prepare_display_address(self, without_company=False):
        # get the information that will be injected into the display format
        # get the address format
        address_format = self._get_address_format()
        args = defaultdict(str, {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name(),
            'company_name': self.commercial_company_name or '',
            'city': self.city_id.name or '',
            'municipality_name': self.municipality_id.name or '',
        })
        for field in self._formatting_address_fields():
            if not field == 'city':
                args[field] = self[field] or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format, args
    