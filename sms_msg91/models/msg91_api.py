# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import json


class Msg91SmsConfig(models.Model):
    _name = 'msg91.sms.config'
    _description = 'MSG91 SMS Configuration'
    _rec_name = 'url'

    active = fields.Boolean(default=True)
    api_key = fields.Char("API Key", help="MSG91 API key", required=True)
    sender = fields.Char("Sender ID", help="Registered MSG91 sender ID", required=True)
    route = fields.Char("Route", default="4", help="Route type (1=Promotional, 4=Transactional)")
    template_id = fields.Char("Template ID", help="Template ID", required=True)
    country = fields.Char("Country Code", default="221", help="Country code (e.g. 91 for India, 221 for Senegal)")
    url = fields.Char(
        "URL",
        default="https://api.msg91.com/api/v5/flow/",
        required=True,
        help="MSG91 API endpoint URL"
    )
    test_to = fields.Char("Test Recipient", help="Recipient phone number for testing")
    test_content = fields.Text("Test Message", help="Test message content")

    @api.constrains('active')
    def _check_single_active(self):
        """Ensure only one active configuration exists."""
        if self.active and self.search_count([('active', '=', True), ('id', '!=', self.id)]):
            raise ValidationError(_('Only one configuration can be active at a time!'))

    def test_sms(self):
        """Send a test SMS using the configured MSG91 settings."""
        if not self.test_to or not self.test_content:
            raise ValidationError(_('Test recipient and message content are required!'))

        response = self.env['msg91.sms.service'].send_sms(
            recipients=self.test_to,
            content=self.test_content,
            sender=self.sender,
            api_key=self.api_key,
            template_id=self.template_id,
            route=self.route,
            country=self.country,
            url=self.url
        )
        self.test_to = ''
        self.test_content = ''
        if response.get('error'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': response.get('error'),
                    'type': 'danger',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Test message sent successfully!'),
                'type': 'success',
                'sticky': False,
            },
        }


class Msg91SmsService(models.Model):
    _name = 'msg91.sms.service'
    _description = 'MSG91 SMS Service (API v5)'
    _rec_name = 'message_id'

    to_list = fields.Many2many("res.partner", string="Partners")
    to_text = fields.Text("Recipients")
    content = fields.Text("Message Content")
    status = fields.Selection([('sent', 'Sent'), ('fail', 'Failed'), ('draft', 'Draft')], default='draft')
    message_id = fields.Char(string="Message ID")
    message_log = fields.Text(string="Message Log")

    def retry_sms(self):
        """Retry sending failed SMS."""
        if self.status != 'fail':
            raise ValidationError(_('Only failed SMS can be retried!'))
        return self.send_sms_wizard()

    def send_sms_wizard(self):
        """Send SMS using selected configuration."""
        config = self.env['msg91.sms.config'].search([('active', '=', True)], limit=1)
        if not config:
            raise UserError(_('No active MSG91 configuration found!'))

        if not self.to_list:
            raise ValidationError(_('Please select at least one recipient!'))
        if not self.content:
            raise ValidationError(_('Message content is required!'))

        recipients = []
        for partner in self.to_list:
            if partner.mobile:
                recipients.append(partner.mobile)
            elif partner.phone:
                recipients.append(partner.phone)
        if not recipients:
            raise ValidationError(_('No valid phone numbers found for selected partners!'))

        response = self.send_sms(
            recipients=recipients,
            content=self.content,
            sender=config.sender,
            api_key=config.api_key,
            template_id=config.template_id,
            route=config.route,
            country=config.country,
            url=config.url
        )

        if response.get('error'):
            self.write({'status': 'fail', 'message_log': response.get('error')})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': response.get('error'),
                    'type': 'danger',
                    'sticky': False,
                },
            }

        self.write({'status': 'sent', 'message_log': json.dumps(response)})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('SMS sent successfully!'),
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def send_sms(self,
             recipients,
             content,
             sender,
             api_key,
             template_id,
             route='4',
             country='221',
             url='https://api.msg91.com/api/v5/flow/',
             timeout=30,
             extra_headers=None):

        if isinstance(recipients, str):
            recipients = [recipients]
        recipients = [r.strip() for r in recipients if r.strip()]

        if not recipients:
            raise ValidationError(_("No valid recipients provided."))

        payload = {
            "template_id": template_id,
            "recipients": []
        }

        for number in recipients:
            payload["recipients"].append({
                "mobiles": str(number),
                # si ton template a des variables dynamiques :
                # "VAR1": content
            })

        headers = {
            'accept': 'application/json',
            'authkey': api_key,
            'content-type': 'application/json'
        }
        if isinstance(extra_headers, dict):
            headers.update(extra_headers)

        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
            resp_payload = resp.json()
        except Exception as exc:
            self.write({'status': 'fail', 'message_log': str(exc)})
            return {"error": str(exc)}

        if not resp.ok:
            msg = json.dumps(resp_payload)
            self.write({'status': 'fail', 'message_log': msg})
            return {"error": f"MSG91 API error (HTTP {resp.status_code}): {msg}"}

        self.write({
            'status': 'sent',
            'message_id': resp_payload.get('request_id'),
            'message_log': json.dumps(resp_payload)
        })
        return resp_payload