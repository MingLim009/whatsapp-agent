# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    kommo_scope_id = fields.Char(
        string='Kommo Scope ID',
        config_parameter='ragnar_whatsapp.kommo_scope_id',
    )
    kommo_channel_secret = fields.Char(
        string='Kommo Channel Secret',
        config_parameter='ragnar_whatsapp.kommo_channel_secret',
    )
    kommo_account_id = fields.Char(
        string='Kommo Account ID (amojo_id)',
        config_parameter='ragnar_whatsapp.kommo_account_id',
    )
    kommo_template_opening_id = fields.Char(
        string='ID plantilla apertura (Kommo/Meta)',
        config_parameter='ragnar_whatsapp.kommo_template_opening_id',
    )
    kommo_template_closing_id = fields.Char(
        string='ID plantilla cierre (Kommo/Meta)',
        config_parameter='ragnar_whatsapp.kommo_template_closing_id',
    )
    kommo_bot_sender_id = fields.Char(
        string='ID remitente bot',
        config_parameter='ragnar_whatsapp.kommo_bot_sender_id',
        default='ragnar-bot',
    )
    kommo_bot_sender_name = fields.Char(
        string='Nombre remitente bot',
        config_parameter='ragnar_whatsapp.kommo_bot_sender_name',
        default='Ragnar Capital',
    )
    claude_api_key = fields.Char(
        string='Claude API Key',
        config_parameter='ragnar_whatsapp.claude_api_key',
    )
    claude_model = fields.Char(
        string='Modelo Claude',
        config_parameter='ragnar_whatsapp.claude_model',
        default='claude-3-5-haiku-20241022',
    )
    claude_max_tokens = fields.Integer(
        string='Máx. tokens Claude',
        config_parameter='ragnar_whatsapp.claude_max_tokens',
        default=512,
    )
    operation_created_states = fields.Char(
        string='Estados: operación creada',
        config_parameter='ragnar_whatsapp.operation_created_states',
        default='draft,confirmed,new,pending',
        help='Estados del modelo de operación que disparan la plantilla de apertura.',
    )
    operation_concluded_states = fields.Char(
        string='Estados: operación concluida',
        config_parameter='ragnar_whatsapp.operation_concluded_states',
        default='done,concluded,completed',
        help='Estados que disparan el mensaje de cierre.',
    )
    operation_model = fields.Char(
        string='Modelo técnico de operación',
        config_parameter='ragnar_whatsapp.operation_model',
        default='ragnar.money.operation',
        help='Nombre técnico del modelo Odoo de operaciones. Por defecto: ragnar.money.operation',
    )
    mock_mode = fields.Boolean(
        string='Modo mock (sin llamar a Kommo/Claude)',
        config_parameter='ragnar_whatsapp.mock_mode',
        default=True,
        help='Activo por defecto. Desactivar solo cuando las credenciales reales estén listas.',
    )
    template_opening_body = fields.Text(
        string='Texto plantilla apertura',
        config_parameter='ragnar_whatsapp.template_opening_body',
        default='Generaste una operación en nuestra web. Ya estamos trabajando en ella.',
    )
    template_closing_body = fields.Text(
        string='Texto plantilla cierre',
        config_parameter='ragnar_whatsapp.template_closing_body',
        default='Tu orden ya fue concluida. Revisa tu correo para obtener el voucher.',
    )
    webhook_base_url = fields.Char(
        string='URL base webhook Odoo',
        compute='_compute_webhook_base_url',
    )

    @api.depends('kommo_scope_id')
    def _compute_webhook_base_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for record in self:
            record.webhook_base_url = f'{base_url.rstrip("/")}/whatsapp/kommo/webhook'
