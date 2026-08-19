# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class WhatsappConversation(models.Model):
    _name = 'whatsapp.conversation'
    _description = 'Conversación WhatsApp (ventana 24h)'
    _order = 'last_inbound_date desc, id desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        ondelete='cascade',
        index=True,
    )
    kommo_conversation_id = fields.Char(
        string='ID conversación Kommo',
        index=True,
        help='Identificador de conversación en Kommo/amojo.',
    )
    kommo_client_id = fields.Char(
        string='Client ID Kommo',
        help='ID del cliente en el canal de chat de Kommo.',
    )
    last_inbound_date = fields.Datetime(
        string='Último mensaje entrante',
        help='Usado para calcular la ventana de 24 horas de WhatsApp.',
    )
    window_open = fields.Boolean(
        string='Ventana abierta',
        compute='_compute_window_open',
        store=True,
    )
    message_ids = fields.One2many(
        'whatsapp.message',
        'conversation_id',
        string='Mensajes',
    )
    message_count = fields.Integer(compute='_compute_message_count')
    last_message_preview = fields.Char(compute='_compute_last_message', store=True)
    last_message_date = fields.Datetime(compute='_compute_last_message', store=True)
    stage = fields.Selection(
        [
            ('new', 'Nuevos contactos'),
            ('active', 'Chats en progreso'),
            ('awaiting', 'Pendiente respuesta'),
            ('done', 'Finalizados'),
        ],
        string='Etapa',
        compute='_compute_stage',
        store=True,
        index=True,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'partner_unique',
            'unique(partner_id)',
            'Ya existe una conversación WhatsApp para este cliente.',
        ),
    ]

    @api.depends('message_ids')
    def _compute_message_count(self):
        grouped = self.env['whatsapp.message'].read_group(
            [('conversation_id', 'in', self.ids)],
            ['conversation_id'],
            ['conversation_id'],
        )
        counts = {g['conversation_id'][0]: g['conversation_id_count'] for g in grouped}
        for record in self:
            record.message_count = counts.get(record.id, 0)

    @api.depends('message_ids', 'message_ids.body', 'message_ids.message_date', 'message_ids.direction')
    def _compute_last_message(self):
        for record in self:
            last = record.message_ids.sorted('message_date', reverse=True)[:1]
            if last:
                prefix = 'Cliente: ' if last.direction == 'inbound' else 'Bot: '
                preview = (prefix + (last.body or '')).strip()
                record.last_message_preview = preview[:120]
                record.last_message_date = last.message_date
            else:
                record.last_message_preview = False
                record.last_message_date = False

    @api.depends('last_inbound_date', 'window_open', 'message_ids', 'message_ids.direction')
    def _compute_stage(self):
        for record in self:
            inbound_messages = record.message_ids.filtered(lambda m: m.direction == 'inbound')
            if not inbound_messages:
                record.stage = 'new'
                continue
            if record.window_open:
                record.stage = 'active'
                continue
            last = record.message_ids.sorted('message_date', reverse=True)[:1]
            if last and last.direction == 'inbound':
                record.stage = 'awaiting'
            else:
                record.stage = 'done'

    @api.depends('last_inbound_date')
    def _compute_window_open(self):
        now = fields.Datetime.now()
        for record in self:
            if not record.last_inbound_date:
                record.window_open = False
            else:
                record.window_open = record.last_inbound_date >= now - timedelta(hours=24)

    def is_window_open(self):
        self.ensure_one()
        self._compute_window_open()
        return self.window_open

    def register_inbound(self, message_date=None):
        """Mark conversation window as open after client message."""
        self.ensure_one()
        self.write({'last_inbound_date': message_date or fields.Datetime.now()})

    @api.model
    def get_or_create_for_partner(self, partner):
        conversation = self.search([('partner_id', '=', partner.id)], limit=1)
        if not conversation:
            conversation = self.create({'partner_id': partner.id})
        return conversation

    @api.model
    def find_by_phone(self, phone):
        partner = self.env['res.partner'].find_by_whatsapp_phone(phone)
        if not partner:
            return self.browse()
        return self.search([('partner_id', '=', partner.id)], limit=1)

    @api.model
    def find_by_kommo_conversation(self, kommo_conversation_id):
        if not kommo_conversation_id:
            return self.browse()
        return self.search([('kommo_conversation_id', '=', kommo_conversation_id)], limit=1)

    def get_recent_history_for_claude(self, limit=20):
        """Return formatted conversation history for Claude prompts."""
        self.ensure_one()
        messages = self.message_ids.sorted('message_date', reverse=True)[:limit]
        lines = []
        for msg in reversed(messages):
            role = 'Cliente' if msg.direction == 'inbound' else 'Asistente'
            lines.append(f'{role}: {msg.body}')
        return '\n'.join(lines)
