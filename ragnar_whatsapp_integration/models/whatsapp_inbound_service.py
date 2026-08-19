# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, timezone

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WhatsappInboundService(models.AbstractModel):
    _name = 'whatsapp.inbound.service'
    _description = 'Procesamiento de mensajes entrantes WhatsApp'

    @api.model
    def process_webhook(self, payload):
        """Route Kommo webhook payloads: delivery status or inbound message."""
        if self._handle_delivery_status(payload):
            return 'delivery'
        if self.enqueue_from_kommo(payload):
            return 'inbound'
        return False

    @api.model
    def _handle_delivery_status(self, payload):
        """Update outbound message delivery state when Kommo reports status."""
        status_code = payload.get('status_code')
        msgid = payload.get('msgid') or payload.get('message_id')
        message_wrapper = payload.get('message') or {}
        inner = message_wrapper.get('message') or message_wrapper
        if not status_code and inner:
            status_code = inner.get('status_code') or inner.get('delivery_status')
            msgid = msgid or inner.get('id')

        if status_code is None or not msgid:
            return False

        state_map = {
            1: 'delivered',
            2: 'read',
            -1: 'failed',
        }
        delivery_state = state_map.get(int(status_code))
        if not delivery_state:
            return False

        Message = self.env['whatsapp.message']
        message = Message.search([('kommo_message_id', '=', msgid)], limit=1)
        if not message:
            _logger.info('Webhook entrega Kommo para msgid %s sin mensaje en Odoo', msgid)
            return True

        error = payload.get('error') or payload.get('error_text')
        message.update_delivery_state(delivery_state, error=error)
        return True

    @api.model
    def enqueue_from_kommo(self, payload):
        """Parse Kommo webhook v2 and queue conversational reply."""
        parsed = self._parse_kommo_payload(payload)
        if not parsed:
            _logger.info('Webhook Kommo ignorado (sin mensaje entrante de cliente)')
            return False

        partner = self.env['res.partner'].find_by_whatsapp_phone(parsed['phone'])
        if not partner:
            _logger.warning(
                'Mensaje WhatsApp de %s sin cliente asociado en Odoo',
                parsed['phone'],
            )
            return False

        conversation = self.env['whatsapp.conversation'].get_or_create_for_partner(partner)
        if parsed.get('kommo_conversation_id'):
            conversation.sudo().write({
                'kommo_conversation_id': parsed['kommo_conversation_id'],
                'kommo_client_id': parsed.get('kommo_client_id'),
            })

        self.env['whatsapp.message'].log_inbound(
            conversation=conversation,
            body=parsed['text'],
            kommo_message_id=parsed.get('kommo_message_id'),
            message_date=parsed.get('message_date'),
        )

        operation = self._find_latest_operation_for_partner(partner)
        if operation:
            operation_context = operation._whatsapp_build_operation_context()
            operation_model = operation._name
            operation_id = operation.id
        else:
            operation_context = {}
            operation_model = False
            operation_id = False

        self.env['whatsapp.message.queue'].enqueue_claude_message(
            partner=partner,
            conversation=conversation,
            message_type='reply',
            operation_model=operation_model,
            operation_id=operation_id,
            operation_context=operation_context,
            inbound_text=parsed['text'],
        )
        return True

    @api.model
    def _parse_kommo_payload(self, payload):
        """Extract inbound client message from Kommo webhook v2."""
        message_wrapper = payload.get('message') or {}
        inner = message_wrapper.get('message') or message_wrapper
        text = (inner.get('text') or '').strip()
        msg_type = inner.get('type', 'text')

        if msg_type != 'text' or not text:
            return False

        sender = message_wrapper.get('sender') or {}
        receiver = message_wrapper.get('receiver') or {}
        conversation = message_wrapper.get('conversation') or {}

        # Inbound: client is sender (has phone), business/manager is receiver.
        phone = sender.get('phone') or receiver.get('phone')
        if not phone:
            return False

        # Ignore outbound webhooks relayed from Kommo UI (manager -> client).
        if sender.get('name') in ('Manager', 'Ragnar Capital') or sender.get('id', '').startswith('ragnar-'):
            bot_sender_id = self.env['ir.config_parameter'].sudo().get_param(
                'ragnar_whatsapp.kommo_bot_sender_id', 'ragnar-bot'
            )
            if sender.get('id') == bot_sender_id:
                return False

        timestamp = message_wrapper.get('timestamp') or payload.get('time')
        message_date = False
        if timestamp:
            message_date = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).replace(tzinfo=None)

        return {
            'text': text,
            'phone': phone,
            'kommo_message_id': inner.get('id'),
            'kommo_conversation_id': conversation.get('id'),
            'kommo_client_id': sender.get('id') or conversation.get('client_id'),
            'message_date': message_date,
        }

    @api.model
    def _find_latest_operation_for_partner(self, partner):
        model_name = self.env['ir.config_parameter'].sudo().get_param(
            'ragnar_whatsapp.operation_model',
        )
        if not model_name or model_name not in self.env:
            return self.env['whatsapp.operation.mixin'].browse()

        Model = self.env[model_name]
        if 'partner_id' in Model._fields:
            domain = [('partner_id', '=', partner.id)]
        elif 'customer_id' in Model._fields:
            domain = [('customer_id', '=', partner.id)]
        else:
            return self.env['whatsapp.operation.mixin'].browse()

        return Model.search(domain, limit=1, order='create_date desc')
