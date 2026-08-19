# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WhatsappMessage(models.Model):
    _name = 'whatsapp.message'
    _description = 'Mensaje WhatsApp'
    _order = 'message_date desc, id desc'

    conversation_id = fields.Many2one(
        'whatsapp.conversation',
        string='Conversación',
        required=True,
        ondelete='cascade',
        index=True,
    )
    partner_id = fields.Many2one(
        related='conversation_id.partner_id',
        store=True,
        index=True,
    )
    direction = fields.Selection(
        [
            ('inbound', 'Entrante'),
            ('outbound', 'Saliente'),
        ],
        required=True,
        index=True,
    )
    body = fields.Text(string='Texto', required=True)
    message_date = fields.Datetime(
        string='Fecha',
        default=fields.Datetime.now,
        required=True,
        index=True,
    )
    source = fields.Selection(
        [
            ('template_opening', 'Plantilla apertura'),
            ('template_closing', 'Plantilla cierre'),
            ('claude', 'Claude (dinámico)'),
            ('manual', 'Manual'),
            ('system', 'Sistema'),
        ],
        string='Origen',
        default='system',
    )
    operation_model = fields.Char(string='Modelo operación', index=True)
    operation_id = fields.Integer(string='ID operación', index=True)
    operation_ref = fields.Char(
        string='Referencia operación',
        compute='_compute_operation_ref',
        store=True,
    )
    kommo_message_id = fields.Char(string='ID mensaje Kommo', index=True)
    delivery_state = fields.Selection(
        [
            ('pending', 'Pendiente'),
            ('sent', 'Enviado'),
            ('delivered', 'Entregado'),
            ('read', 'Leído'),
            ('failed', 'Fallido'),
        ],
        default='pending',
        index=True,
    )
    delivery_error = fields.Text(string='Error de entrega')
    queue_id = fields.Many2one(
        'whatsapp.message.queue',
        string='Job de cola',
        ondelete='set null',
    )

    @api.depends('operation_model', 'operation_id')
    def _compute_operation_ref(self):
        for record in self:
            if record.operation_model and record.operation_id:
                record.operation_ref = f'{record.operation_model},{record.operation_id}'
            else:
                record.operation_ref = False

    @api.model
    def log_inbound(self, conversation, body, kommo_message_id=None, message_date=None):
        message = self.create({
            'conversation_id': conversation.id,
            'direction': 'inbound',
            'body': body,
            'source': 'system',
            'kommo_message_id': kommo_message_id,
            'message_date': message_date or fields.Datetime.now(),
            'delivery_state': 'delivered',
        })
        conversation.register_inbound(message.message_date)
        return message

    @api.model
    def log_outbound(
        self,
        conversation,
        body,
        source,
        operation_model=None,
        operation_id=None,
        kommo_message_id=None,
        queue_id=None,
    ):
        return self.create({
            'conversation_id': conversation.id,
            'direction': 'outbound',
            'body': body,
            'source': source,
            'operation_model': operation_model,
            'operation_id': operation_id,
            'kommo_message_id': kommo_message_id,
            'queue_id': queue_id,
            'delivery_state': 'pending',
        })

    def update_delivery_state(self, state, error=None):
        vals = {'delivery_state': state}
        if error:
            vals['delivery_error'] = error
        self.write(vals)
