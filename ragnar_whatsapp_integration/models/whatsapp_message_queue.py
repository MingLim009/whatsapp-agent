# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

MAX_RETRIES = 5


class WhatsappMessageQueue(models.Model):
    _name = 'whatsapp.message.queue'
    _description = 'Cola de envío WhatsApp'
    _order = 'priority desc, create_date asc, id asc'

    name = fields.Char(string='Referencia', compute='_compute_name', store=True)
    state = fields.Selection(
        [
            ('pending', 'Pendiente'),
            ('processing', 'Procesando'),
            ('done', 'Completado'),
            ('failed', 'Fallido'),
        ],
        default='pending',
        required=True,
        index=True,
    )
    priority = fields.Integer(default=10)
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    conversation_id = fields.Many2one('whatsapp.conversation', required=True, ondelete='cascade')
    payload_type = fields.Selection(
        [
            ('template_opening', 'Plantilla apertura'),
            ('template_closing', 'Plantilla cierre'),
            ('text', 'Texto libre'),
            ('claude_reply', 'Respuesta Claude'),
            ('claude_closing', 'Cierre dinámico Claude'),
        ],
        required=True,
    )
    body = fields.Text(string='Texto a enviar')
    claude_prompt_context = fields.Text(
        string='Contexto Claude (JSON)',
        help='Contexto serializado para generación dinámica.',
    )
    operation_model = fields.Char(index=True)
    operation_id = fields.Integer(index=True)
    retry_count = fields.Integer(default=0)
    next_retry_date = fields.Datetime(string='Próximo reintento', index=True)
    last_error = fields.Text(string='Último error')
    message_id = fields.Many2one('whatsapp.message', string='Mensaje registrado', readonly=True)
    processed_date = fields.Datetime(readonly=True)

    @api.depends('payload_type', 'partner_id', 'create_date')
    def _compute_name(self):
        for record in self:
            partner = record.partner_id.name or 'Cliente'
            record.name = f'{record.payload_type} – {partner}'

    @api.model
    def _base_vals(self, partner, conversation, operation_model=None, operation_id=None, **extra):
        vals = {
            'partner_id': partner.id,
            'conversation_id': conversation.id,
            'operation_model': operation_model,
            'operation_id': operation_id,
        }
        vals.update(extra)
        return vals

    @api.model
    def enqueue_opening_template(self, partner, conversation, operation_model, operation_id, operation_context):
        return self.create(self._base_vals(
            partner,
            conversation,
            operation_model=operation_model,
            operation_id=operation_id,
            payload_type='template_opening',
            claude_prompt_context=json.dumps(operation_context, ensure_ascii=False),
        ))

    @api.model
    def enqueue_closing_template(self, partner, conversation, operation_model, operation_id, operation_context):
        return self.create(self._base_vals(
            partner,
            conversation,
            operation_model=operation_model,
            operation_id=operation_id,
            payload_type='template_closing',
            claude_prompt_context=json.dumps(operation_context, ensure_ascii=False),
        ))

    @api.model
    def enqueue_claude_message(
        self,
        partner,
        conversation,
        message_type,
        operation_model=None,
        operation_id=None,
        operation_context=None,
        inbound_text=None,
    ):
        context = {
            'operation': operation_context or {},
            'inbound_text': inbound_text,
            'history': conversation.get_recent_history_for_claude(),
        }
        payload_type = 'claude_closing' if message_type == 'closing_dynamic' else 'claude_reply'
        return self.create(self._base_vals(
            partner,
            conversation,
            operation_model=operation_model,
            operation_id=operation_id,
            payload_type=payload_type,
            claude_prompt_context=json.dumps(context, ensure_ascii=False),
        ))

    @api.model
    def enqueue_text_message(self, partner, conversation, body, source='manual'):
        return self.create(self._base_vals(
            partner,
            conversation,
            payload_type='text',
            body=body,
            claude_prompt_context=json.dumps({'source': source}, ensure_ascii=False),
        ))

    @api.model
    def cron_process_queue(self, batch_size=50):
        now = fields.Datetime.now()
        domain = [
            ('state', 'in', ['pending', 'failed']),
            '|',
            ('next_retry_date', '=', False),
            ('next_retry_date', '<=', now),
        ]
        jobs = self.search(domain, limit=batch_size, order='priority desc, create_date asc')
        for job in jobs:
            job._process_job()
        return True

    def _process_job(self):
        self.ensure_one()
        if self.state == 'processing':
            return
        if self.retry_count >= MAX_RETRIES:
            self.write({'state': 'failed'})
            return

        self.write({'state': 'processing'})
        try:
            body, source = self._resolve_outbound_content()
            kommo = self.env['kommo.api.client']
            result = kommo.send_to_partner(
                partner=self.partner_id,
                conversation=self.conversation_id,
                body=body,
                payload_type=self.payload_type,
                operation_context=self._get_operation_context(),
            )
            message = self.env['whatsapp.message'].log_outbound(
                conversation=self.conversation_id,
                body=body,
                source=source,
                operation_model=self.operation_model,
                operation_id=self.operation_id,
                kommo_message_id=result.get('msgid'),
                queue_id=self.id,
            )
            message.update_delivery_state('sent')
            self.write({
                'state': 'done',
                'body': body,
                'message_id': message.id,
                'processed_date': fields.Datetime.now(),
                'last_error': False,
            })
        except Exception as exc:
            _logger.exception('Error procesando job WhatsApp %s', self.id)
            retry = self.retry_count + 1
            delay_minutes = min(60, 2 ** retry)
            failed = retry >= MAX_RETRIES
            self.write({
                'state': 'failed' if failed else 'pending',
                'retry_count': retry,
                'last_error': str(exc),
                'next_retry_date': fields.Datetime.add(
                    fields.Datetime.now(),
                    minutes=delay_minutes,
                ),
            })
            if failed:
                self._notify_operator_failure(str(exc))

    def _get_operation_context(self):
        if not self.claude_prompt_context:
            return {}
        try:
            return json.loads(self.claude_prompt_context)
        except json.JSONDecodeError:
            return {}

    def _resolve_outbound_content(self):
        if self.payload_type in ('text',):
            if not self.body:
                raise ValueError('El job de texto libre no tiene cuerpo.')
            return self.body, 'manual'

        if self.payload_type == 'template_opening':
            icp = self.env['ir.config_parameter'].sudo()
            template_body = icp.get_param(
                'ragnar_whatsapp.template_opening_body',
                'Generaste una operación en nuestra web. Ya estamos trabajando en ella.',
            )
            return template_body, 'template_opening'

        if self.payload_type == 'template_closing':
            icp = self.env['ir.config_parameter'].sudo()
            template_body = icp.get_param(
                'ragnar_whatsapp.template_closing_body',
                'Tu orden ya fue concluida. Revisa tu correo para obtener el voucher.',
            )
            ctx = self._get_operation_context()
            return self._format_template(template_body, ctx), 'template_closing'

        claude = self.env['claude.api.client']
        ctx = self._get_operation_context()
        if self.payload_type == 'claude_closing':
            body = claude.generate_closing_message(
                operation_context=ctx.get('operation', ctx),
                history=ctx.get('history', ''),
            )
            return body, 'claude'

        body = claude.generate_reply(
            operation_context=ctx.get('operation', {}),
            history=ctx.get('history', ''),
            inbound_text=ctx.get('inbound_text', ''),
        )
        return body, 'claude'

    @api.model
    def _format_template(self, template_body, context):
        """Simple variable substitution for template bodies."""
        operation = context if isinstance(context, dict) else {}
        replacements = {
            '{{operation_number}}': operation.get('operation_number', ''),
            '{{amount_from}}': str(operation.get('amount_from', '')),
            '{{amount_to}}': str(operation.get('amount_to', '')),
            '{{currency_from}}': operation.get('currency_from', ''),
            '{{currency_to}}': operation.get('currency_to', ''),
            '{{currency_from_label}}': operation.get('currency_from_label', ''),
            '{{currency_to_label}}': operation.get('currency_to_label', ''),
            '{{partner_name}}': operation.get('partner_name', ''),
        }
        result = template_body
        for key, value in replacements.items():
            result = result.replace(key, value or '')
        return result

    def _notify_operator_failure(self, error_message):
        """Alert system users when a job exhausts retries."""
        self.ensure_one()
        users = self.env.ref('base.group_system').users
        if not users:
            return
        partner_ids = users.mapped('partner_id').ids
        self.env['mail.message'].sudo().create({
            'model': self._name,
            'res_id': self.id,
            'message_type': 'notification',
            'subtype_id': self.env.ref('mail.mt_note').id,
            'body': (
                f'<p><strong>Fallo WhatsApp (job #{self.id})</strong></p>'
                f'<p>Cliente: {self.partner_id.display_name}</p>'
                f'<p>Tipo: {self.payload_type}</p>'
                f'<p>Error: {error_message}</p>'
            ),
            'partner_ids': [(6, 0, partner_ids)],
        })

    def action_retry(self):
        for record in self:
            record.write({
                'state': 'pending',
                'next_retry_date': False,
                'retry_count': 0,
            })
            record._process_job()
