# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class KommoWebhookController(http.Controller):

    @http.route(
        '/whatsapp/kommo/webhook',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
    )
    def kommo_webhook_health(self, **kwargs):
        """Health check for webhook URL registration."""
        return request.make_response('ragnar_whatsapp_webhook_ok', status=200)

    @http.route(
        '/whatsapp/kommo/webhook',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def kommo_webhook(self, **kwargs):
        """Receive inbound WhatsApp messages forwarded by Kommo.

        Responds within 5 seconds; processing is queued asynchronously.
        """
        raw_body = request.httprequest.get_data()
        signature = request.httprequest.headers.get('X-Signature', '')

        kommo = request.env['kommo.api.client'].sudo()
        if not kommo.verify_webhook_signature(raw_body, signature):
            _logger.warning('Webhook Kommo rechazado: firma inválida')
            return request.make_response('Invalid signature', status=403)

        try:
            payload = json.loads(raw_body.decode('utf-8') or '{}')
        except (UnicodeDecodeError, json.JSONDecodeError):
            _logger.exception('Webhook Kommo con JSON inválido')
            return request.make_response('Bad request', status=400)

        request.env['whatsapp.inbound.service'].sudo().process_webhook(payload)
        return request.make_response('OK', status=200)
