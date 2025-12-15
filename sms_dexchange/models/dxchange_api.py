# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import json


class DexchangeSmsConfig(models.Model):
    _name = 'dexchange.sms.config'
    _description = 'Dexchange SMS Configuration'
    _rec_name = 'url'

    active = fields.Boolean(default=True)
    api_key = fields.Char("API Key", required=True, help="Dexchange API key")
    sender = fields.Char("Sender ID", help="Sender name registered on Dexchange")
    url = fields.Char(
        "API URL",
        default="https://api-v2.dexchange-sms.com/api/v1/send/sms",
        required=True,
        help="Dexchange SMS endpoint"
    )
    test_to = fields.Char("Test Recipient")
    test_content = fields.Text("Test Message")

    @api.constrains('active')
    def _check_single_active(self):
        if self.active and self.search_count([('active', '=', True), ('id', '!=', self.id)]):
            raise ValidationError(_('Only one configuration can be active at a time!'))

    def test_sms(self):
        if not self.test_to or not self.test_content:
            raise ValidationError(_('Test recipient and message content are required!'))

        response = self.env['dexchange.sms.service'].send_sms(
            recipients=self.test_to,
            content=self.test_content,
            sender=self.sender,
            api_key=self.api_key,
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

class DexchangeSmsService(models.Model):
    _name = 'dexchange.sms.service'
    _description = 'Dexchange SMS Service'
    _rec_name = 'message_id'

    to_list = fields.Many2many("res.partner", string="Partners")
    test_to = fields.Char("Test Recipient")
    content = fields.Text("Message Content")
    status = fields.Selection([('sent', 'Sent'), ('fail', 'Failed'), ('draft', 'Draft')], default='draft')
    message_id = fields.Char("Message ID")
    message_log = fields.Text("Message Log")

    def retry_sms(self):
        if self.status != 'fail':
            raise ValidationError(_('Only failed SMS can be retried!'))
        return self.send_sms_wizard()

    def send_sms_wizard(self):
        config = self.env['dexchange.sms.config'].search([('active', '=', True)], limit=1)
        if not config:
            raise UserError(_('No active Dexchange configuration found!'))

        if not self.to_list:
            raise ValidationError(_('Please select at least one recipient!'))
        if not self.content:
            raise ValidationError(_('Message content is required!'))

        recipients = [
            partner.mobile or partner.phone
            for partner in self.to_list
            if partner.mobile or partner.phone
        ]

        if not recipients:
            raise ValidationError(_('No valid phone numbers found for selected partners!'))

        response = self.send_sms(
            recipients=recipients,
            content=self.content,
            sender=config.sender,
            api_key=config.api_key,
            url=config.url
        )

        if response.get('error'):
            self.write({'status': 'fail', 'message_log': response.get('error')})
        else:
            self.write({
                'status': 'sent',
                'message_id': response.get('uuid', 'N/A'),
                'message_log': json.dumps(response)
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Error') if response.get('error') else _('Success'),
                'message': response.get('error') or _('SMS sent successfully!'),
                'type': 'danger' if response.get('error') else 'success',
                'sticky': False,
            },
        }

    @api.model
    def send_sms(self, recipients, content, sender, api_key, url=None, timeout=30):
        if isinstance(recipients, str):
            recipients = [recipients]

        recipients = [r.strip() for r in recipients if r.strip()]

        if not recipients:
            return {"error": "No valid recipients provided."}

        if not url:
            url = "https://api-v2.dexchange-sms.com/api/v1/send/sms"

        payload = {
            "signature": sender,
            "content": content,
            "number": recipients
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            return {"error": "Request timed out. Please try again later."}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}

        try:
            resp_json = resp.json()
        except ValueError:
            return {"error": f"Invalid response from server: {resp.text[:500]}"}

        if resp_json.get('error'):
            return {"error": resp_json['error']}
            print(resp.text)

        return resp_json