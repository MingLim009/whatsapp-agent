# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

SUPPORTED_CURRENCY_PAIRS = {
    ('BOB', 'PEN'),
    ('PEN', 'BOB'),
    ('BOB', 'USD'),
    ('BOB', 'USDINT'),
}

CURRENCY_LABELS = {
    'BOB': 'Bolivianos (BOB)',
    'PEN': 'Soles peruanos (PEN)',
    'USD': 'Dólares (USD)',
    'USDINT': 'Dólares internacionales (SWIFT)',
}


class WhatsappOperationMixin(models.AbstractModel):
    """Mixin para el modelo de operaciones de cambio existente en Odoo.

    Herede este mixin en el modelo real de operaciones (p. ej. ``sale.order``,
    ``money.transfer``, etc.) y configure las acciones automatizadas según
    README.md.
    """

    _name = 'whatsapp.operation.mixin'
    _description = 'Mixin de operación para WhatsApp Bot'

    whatsapp_notified_open = fields.Boolean(
        string='Notificación de apertura enviada',
        copy=False,
        readonly=True,
    )
    whatsapp_notified_close = fields.Boolean(
        string='Notificación de cierre enviada',
        copy=False,
        readonly=True,
    )
    whatsapp_conversation_id = fields.Many2one(
        'whatsapp.conversation',
        string='Conversación WhatsApp',
        copy=False,
        readonly=True,
    )
    whatsapp_message_count = fields.Integer(compute='_compute_whatsapp_message_count')

    def _compute_whatsapp_message_count(self):
        Message = self.env['whatsapp.message']
        for record in self:
            record.whatsapp_message_count = Message.search_count([
                ('operation_model', '=', record._name),
                ('operation_id', '=', record.id),
            ])

    def _whatsapp_get_partner(self):
        """Override if the partner field uses another name."""
        self.ensure_one()
        partner = getattr(self, 'partner_id', False) or getattr(self, 'customer_id', False)
        if not partner:
            raise ValueError(
                f'La operación {self.display_name} no tiene cliente asociado para WhatsApp.'
            )
        return partner

    def _whatsapp_get_operation_number(self):
        """Override to return the business operation number."""
        self.ensure_one()
        for attr in ('operation_number', 'name', 'reference'):
            value = getattr(self, attr, None)
            if value:
                return str(value)
        return str(self.id)

    def _whatsapp_get_currency_pair(self):
        """Return (currency_from_code, currency_to_code).

        Override according to the real field names on the operation model.
        """
        self.ensure_one()
        currency_from = getattr(self, 'currency_from_id', False) or getattr(
            self, 'source_currency_id', False
        )
        currency_to = getattr(self, 'currency_to_id', False) or getattr(
            self, 'destination_currency_id', False
        )
        code_from = self._whatsapp_normalize_currency_code(currency_from)
        code_to = self._whatsapp_normalize_currency_code(currency_to)
        return code_from, code_to

    def _whatsapp_get_amounts(self):
        """Return (amount_from, amount_to) as floats."""
        self.ensure_one()
        amount_from = getattr(self, 'amount_from', None) or getattr(self, 'amount_source', 0.0)
        amount_to = getattr(self, 'amount_to', None) or getattr(self, 'amount_destination', 0.0)
        return float(amount_from or 0.0), float(amount_to or 0.0)

    def _whatsapp_is_created_state(self):
        """Return True when the operation was just created / is active."""
        self.ensure_one()
        state = getattr(self, 'state', None)
        created_states = self.env['ir.config_parameter'].sudo().get_param(
            'ragnar_whatsapp.operation_created_states', 'draft,confirmed,new,pending'
        )
        return state in [s.strip() for s in created_states.split(',') if s.strip()]

    def _whatsapp_is_concluded_state(self):
        """Return True when the operation is concluded (voucher loaded)."""
        self.ensure_one()
        state = getattr(self, 'state', None)
        concluded_states = self.env['ir.config_parameter'].sudo().get_param(
            'ragnar_whatsapp.operation_concluded_states', 'done,concluded,completed'
        )
        return state in [s.strip() for s in concluded_states.split(',') if s.strip()]

    @api.model
    def _whatsapp_normalize_currency_code(self, currency):
        if not currency:
            return False
        if hasattr(currency, 'name'):
            code = currency.name.upper()
        else:
            code = str(currency).upper()
        if code == 'USDT':
            return 'USDINT'
        return code

    def _whatsapp_operation_ref(self):
        self.ensure_one()
        return f'{self._name},{self.id}'

    def _whatsapp_get_or_create_conversation(self):
        self.ensure_one()
        partner = self._whatsapp_get_partner()
        conversation = self.whatsapp_conversation_id
        if not conversation:
            conversation = self.env['whatsapp.conversation'].get_or_create_for_partner(partner)
            self.sudo().write({'whatsapp_conversation_id': conversation.id})
        return conversation

    def _whatsapp_build_operation_context(self):
        self.ensure_one()
        code_from, code_to = self._whatsapp_get_currency_pair()
        amount_from, amount_to = self._whatsapp_get_amounts()
        label_from = CURRENCY_LABELS.get(code_from, code_from or 'N/D')
        label_to = CURRENCY_LABELS.get(code_to, code_to or 'N/D')
        return {
            'operation_number': self._whatsapp_get_operation_number(),
            'currency_from': code_from,
            'currency_to': code_to,
            'currency_from_label': label_from,
            'currency_to_label': label_to,
            'amount_from': amount_from,
            'amount_to': amount_to,
            'state': getattr(self, 'state', ''),
            'partner_name': self._whatsapp_get_partner().name,
        }

    def action_whatsapp_notify_operation_created(self):
        """Called by automated action when an operation is created."""
        queue = self.env['whatsapp.message.queue']
        for record in self:
            if record.whatsapp_notified_open:
                continue
            if not record._whatsapp_is_created_state():
                continue
            try:
                partner = record._whatsapp_get_partner()
                conversation = record._whatsapp_get_or_create_conversation()
                queue.enqueue_opening_template(
                    partner=partner,
                    conversation=conversation,
                    operation_model=record._name,
                    operation_id=record.id,
                    operation_context=record._whatsapp_build_operation_context(),
                )
                record.sudo().write({'whatsapp_notified_open': True})
            except Exception:
                _logger.exception(
                    'Error encolando notificación de apertura para operación %s',
                    record.id,
                )
        return True

    def action_whatsapp_notify_operation_concluded(self):
        """Called by automated action when operation reaches concluded state."""
        queue = self.env['whatsapp.message.queue']
        for record in self:
            if record.whatsapp_notified_close:
                continue
            if not record._whatsapp_is_concluded_state():
                continue
            try:
                partner = record._whatsapp_get_partner()
                conversation = record._whatsapp_get_or_create_conversation()
                operation_context = record._whatsapp_build_operation_context()
                if conversation.is_window_open():
                    queue.enqueue_claude_message(
                        partner=partner,
                        conversation=conversation,
                        message_type='closing_dynamic',
                        operation_model=record._name,
                        operation_id=record.id,
                        operation_context=operation_context,
                    )
                else:
                    queue.enqueue_closing_template(
                        partner=partner,
                        conversation=conversation,
                        operation_model=record._name,
                        operation_id=record.id,
                        operation_context=operation_context,
                    )
                record.sudo().write({'whatsapp_notified_close': True})
            except Exception:
                _logger.exception(
                    'Error encolando notificación de cierre para operación %s',
                    record.id,
                )
        return True
