# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from email.utils import formatdate

import requests

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

AMOJO_BASE_URL = 'https://amojo.kommo.com/v2/origin/custom/'


class KommoApiClient(models.AbstractModel):
    _name = 'kommo.api.client'
    _description = 'Cliente API Kommo Chats'

    @api.model
    def _is_mock_mode(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'ragnar_whatsapp.mock_mode', 'True'
        ) in ('True', 'true', '1')

    @api.model
    def _get_config(self):
        icp = self.env['ir.config_parameter'].sudo()
        return {
            'scope_id': icp.get_param('ragnar_whatsapp.kommo_scope_id'),
            'channel_secret': icp.get_param('ragnar_whatsapp.kommo_channel_secret'),
            'account_id': icp.get_param('ragnar_whatsapp.kommo_account_id'),
            'template_opening_id': icp.get_param('ragnar_whatsapp.kommo_template_opening_id'),
            'template_closing_id': icp.get_param('ragnar_whatsapp.kommo_template_closing_id'),
            'bot_sender_id': icp.get_param('ragnar_whatsapp.kommo_bot_sender_id', 'ragnar-bot'),
            'bot_sender_name': icp.get_param('ragnar_whatsapp.kommo_bot_sender_name', 'Ragnar Capital'),
            'mock_mode': self._is_mock_mode(),
        }

    @api.model
    def _sign_request(self, method, path, body_bytes, date_header, secret):
        content_md5 = hashlib.md5(body_bytes).hexdigest().lower()
        check_sum = '\n'.join([
            method.upper(),
            content_md5,
            'application/json',
            date_header,
            path,
        ])
        signature = hmac.new(
            secret.encode('utf-8'),
            check_sum.encode('utf-8'),
            hashlib.sha1,
        ).hexdigest().lower()
        return content_md5, signature

    @api.model
    def _request(self, path_suffix, payload):
        config = self._get_config()
        if config.get('mock_mode'):
            _logger.info('[MOCK Kommo] POST %s payload=%s', path_suffix or '/', payload)
            return {'mock': True, 'status': 'accepted'}
        if not config['scope_id'] or not config['channel_secret']:
            raise UserError(
                'Kommo no está configurado. Defina scope_id y channel_secret en Ajustes, '
                'o active el modo mock para pruebas locales.'
            )

        body_bytes = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        date_header = formatdate(timeval=None, localtime=False, usegmt=True)
        path = f'/v2/origin/custom/{config["scope_id"]}{path_suffix or ""}'
        content_md5, signature = self._sign_request(
            'POST',
            path,
            body_bytes,
            date_header,
            config['channel_secret'],
        )
        url = f'{AMOJO_BASE_URL}{config["scope_id"]}{path_suffix or ""}'
        headers = {
            'Date': date_header,
            'Content-Type': 'application/json',
            'Content-MD5': content_md5,
            'X-Signature': signature,
        }
        response = requests.post(url, data=body_bytes, headers=headers, timeout=30)
        if response.status_code >= 400:
            _logger.error('Kommo API error %s: %s', response.status_code, response.text)
            raise UserError(f'Error Kommo ({response.status_code}): {response.text[:500]}')
        try:
            return response.json()
        except ValueError:
            return {'raw_response': response.text}

    @api.model
    def verify_webhook_signature(self, raw_body, signature_header):
        if self._is_mock_mode():
            return True
        config = self._get_config()
        secret = config.get('channel_secret')
        if not secret or not signature_header:
            return False
        expected = hmac.new(
            secret.encode('utf-8'),
            raw_body,
            hashlib.sha1,
        ).hexdigest().lower()
        return hmac.compare_digest(expected, signature_header.lower())

    @api.model
    def _build_message_payload(self, partner, conversation, body, payload_type, operation_context):
        config = self._get_config()
        phone = partner.get_whatsapp_e164()
        msgid = str(uuid.uuid4())
        conversation_id = (
            conversation.kommo_conversation_id
            or f'ragnar-{partner.id}'
        )
        timestamp = int(datetime.now(timezone.utc).timestamp())

        message_content = {'type': 'text', 'text': body}
        if payload_type == 'template_opening' and config['template_opening_id']:
            message_content = {
                'type': 'text',
                'text': body,
                'template': {
                    'id': config['template_opening_id'],
                    'content': body,
                    'params': self._template_params(operation_context),
                },
            }
        elif payload_type == 'template_closing' and config['template_closing_id']:
            message_content = {
                'type': 'text',
                'text': body,
                'template': {
                    'id': config['template_closing_id'],
                    'content': body,
                    'params': self._template_params(operation_context),
                },
            }

        return {
            'event_type': 'new_message',
            'payload': {
                'timestamp': timestamp,
                'msgid': msgid,
                'conversation_id': conversation_id,
                'sender': {
                    'id': config['bot_sender_id'],
                    'name': config['bot_sender_name'],
                    'profile': {
                        'phone': phone,
                        'email': partner.email or '',
                    },
                },
                'receiver': {
                    'id': conversation.kommo_client_id or f'client-{partner.id}',
                    'phone': phone,
                    'name': partner.name,
                },
                'message': message_content,
                'silent': False,
            },
        }, msgid

    @api.model
    def _template_params(self, operation_context):
        if not operation_context:
            return []
        operation = operation_context.get('operation', operation_context)
        return [
            operation.get('operation_number', ''),
            str(operation.get('amount_from', '')),
            operation.get('currency_from_label', operation.get('currency_from', '')),
            str(operation.get('amount_to', '')),
            operation.get('currency_to_label', operation.get('currency_to', '')),
        ]

    @api.model
    def send_to_partner(self, partner, conversation, body, payload_type, operation_context=None):
        partner.ensure_whatsapp_ready()
        payload, msgid = self._build_message_payload(
            partner,
            conversation,
            body,
            payload_type,
            operation_context or {},
        )
        result = self._request('', payload)
        if conversation and payload['payload'].get('conversation_id'):
            conversation.sudo().write({
                'kommo_conversation_id': payload['payload']['conversation_id'],
                'kommo_client_id': payload['payload']['receiver']['id'],
            })
        result['msgid'] = msgid
        return result
