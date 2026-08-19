# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    whatsapp_phone = fields.Char(
        string='WhatsApp',
        help='Número con código de país, p. ej. +59170000000',
    )
    whatsapp_conversation_id = fields.Many2one(
        'whatsapp.conversation',
        string='Conversación WhatsApp',
        compute='_compute_whatsapp_conversation',
    )
    whatsapp_message_count = fields.Integer(compute='_compute_whatsapp_conversation')

    @api.depends('whatsapp_phone')
    def _compute_whatsapp_conversation(self):
        Conversation = self.env['whatsapp.conversation']
        for partner in self:
            conversation = Conversation.search([('partner_id', '=', partner.id)], limit=1)
            partner.whatsapp_conversation_id = conversation
            partner.whatsapp_message_count = conversation.message_count if conversation else 0

    @api.model
    def _normalize_phone(self, phone):
        if not phone:
            return False
        digits = re.sub(r'[^\d+]', '', phone.strip())
        if not digits.startswith('+'):
            digits = f'+{digits.lstrip("0")}'
        return digits

    def get_whatsapp_e164(self):
        self.ensure_one()
        phone = self.whatsapp_phone or self.mobile or self.phone
        normalized = self._normalize_phone(phone)
        if not normalized or len(re.sub(r'\D', '', normalized)) < 8:
            raise ValueError(
                f'El cliente {self.name} no tiene un número WhatsApp válido.'
            )
        return normalized

    def ensure_whatsapp_ready(self):
        self.ensure_one()
        self.get_whatsapp_e164()
        return True

    @api.model
    def find_by_whatsapp_phone(self, phone):
        normalized = self._normalize_phone(phone)
        if not normalized:
            return self.browse()
        candidates = self.search([
            '|', '|',
            ('whatsapp_phone', 'ilike', normalized.lstrip('+')),
            ('mobile', 'ilike', normalized.lstrip('+')),
            ('phone', 'ilike', normalized.lstrip('+')),
        ])
        for partner in candidates:
            try:
                if partner.get_whatsapp_e164() == normalized:
                    return partner
            except ValueError:
                continue
        return self.browse()
