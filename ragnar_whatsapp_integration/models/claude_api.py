# -*- coding: utf-8 -*-
import logging

import requests

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages'


class ClaudeApiClient(models.AbstractModel):
    _name = 'claude.api.client'
    _description = 'Cliente API Claude (Anthropic)'

    @api.model
    def _is_mock_mode(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'ragnar_whatsapp.mock_mode', 'True'
        ) in ('True', 'true', '1')

    @api.model
    def _get_config(self):
        icp = self.env['ir.config_parameter'].sudo()
        return {
            'api_key': icp.get_param('ragnar_whatsapp.claude_api_key'),
            'model': icp.get_param(
                'ragnar_whatsapp.claude_model',
                'claude-3-5-haiku-20241022',
            ),
            'max_tokens': int(icp.get_param('ragnar_whatsapp.claude_max_tokens', '512')),
            'mock_mode': self._is_mock_mode(),
        }

    @api.model
    def _system_prompt(self):
        icp = self.env['ir.config_parameter'].sudo()
        return icp.get_param(
            'ragnar_whatsapp.claude_system_prompt',
            (
                'Eres el asistente de WhatsApp de Ragnar Capital, una plataforma de '
                'cambio y envío de dinero. Responde en español, con tono profesional '
                'y empático. Ayuda al cliente con el estado de su operación usando '
                'solo la información del contexto. No inventes montos ni fechas. '
                'Si no tienes un dato, indícalo con claridad y sugiere contactar al '
                'equipo de soporte. Mensajes breves, adecuados para WhatsApp.'
            ),
        )

    @api.model
    def _mock_reply(self, user_prompt):
        _logger.info('[MOCK Claude] prompt length=%s', len(user_prompt or ''))
        if 'cierre' in (user_prompt or '').lower() or 'concluida' in (user_prompt or '').lower():
            return (
                'Tu operación ya fue concluida. Revisa tu correo para obtener el voucher. '
                'Si tienes alguna duda, escríbenos por este mismo chat.'
            )
        return (
            'Gracias por tu mensaje. Estamos revisando el estado de tu operación y '
            'te confirmaremos en breve. ¿Hay algo específico que necesites saber?'
        )

    @api.model
    def _call_api(self, user_prompt):
        config = self._get_config()
        if config.get('mock_mode') or not config['api_key']:
            if not config['api_key'] and not config.get('mock_mode'):
                raise UserError(
                    'La API key de Claude no está configurada. Revise Ajustes > WhatsApp Bot.'
                )
            return self._mock_reply(user_prompt)

        headers = {
            'x-api-key': config['api_key'],
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }
        payload = {
            'model': config['model'],
            'max_tokens': config['max_tokens'],
            'system': self._system_prompt(),
            'messages': [{'role': 'user', 'content': user_prompt}],
        }
        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=60)
        if response.status_code >= 400:
            _logger.error('Claude API error %s: %s', response.status_code, response.text)
            raise UserError(f'Error Claude ({response.status_code}): {response.text[:500]}')

        data = response.json()
        content_blocks = data.get('content') or []
        texts = [block.get('text', '') for block in content_blocks if block.get('type') == 'text']
        text = '\n'.join(texts).strip()
        if not text:
            raise UserError('Claude devolvió una respuesta vacía.')
        return text

    @api.model
    def _format_operation_block(self, operation_context):
        if not operation_context:
            return 'Sin operación asociada en el contexto.'
        return (
            f"Número de operación: {operation_context.get('operation_number', 'N/D')}\n"
            f"Estado: {operation_context.get('state', 'N/D')}\n"
            f"Origen: {operation_context.get('amount_from', '')} "
            f"{operation_context.get('currency_from_label', operation_context.get('currency_from', ''))}\n"
            f"Destino: {operation_context.get('amount_to', '')} "
            f"{operation_context.get('currency_to_label', operation_context.get('currency_to', ''))}"
        )

    @api.model
    def generate_reply(self, operation_context, history, inbound_text):
        prompt = (
            'Redacta la respuesta al cliente por WhatsApp.\n\n'
            f'Contexto de operación:\n{self._format_operation_block(operation_context)}\n\n'
            f'Historial reciente:\n{history or "(sin historial)"}\n\n'
            f'Último mensaje del cliente:\n{inbound_text}\n\n'
            'Responde únicamente con el texto del mensaje, sin comillas ni explicaciones.'
        )
        return self._call_api(prompt)

    @api.model
    def generate_closing_message(self, operation_context, history):
        prompt = (
            'Redacta un mensaje de cierre por WhatsApp informando que la operación '
            'fue concluida y que el voucher fue enviado por correo.\n\n'
            f'Contexto de operación:\n{self._format_operation_block(operation_context)}\n\n'
            f'Historial reciente:\n{history or "(sin historial)"}\n\n'
            'Responde únicamente con el texto del mensaje, sin comillas ni explicaciones.'
        )
        return self._call_api(prompt)
