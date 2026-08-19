# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RagnarMoneyOperation(models.Model):
    """Modelo demo/producción adaptable de operaciones de cambio.

    Si Ragnar Capital ya tiene otro modelo, mapéelo en Ajustes y herede
    ``whatsapp.operation.mixin`` allí. Este modelo permite probar el flujo
    completo sin esperar ese mapeo.
    """

    _name = 'ragnar.money.operation'
    _description = 'Operación de cambio / envío de dinero'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'whatsapp.operation.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Número de operación',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('ragnar.money.operation')
        or 'New',
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True,
        index=True,
    )
    currency_from = fields.Selection(
        [
            ('BOB', 'BOB'),
            ('PEN', 'PEN'),
            ('USD', 'USD'),
            ('USDINT', 'USDINT'),
        ],
        string='Moneda origen',
        required=True,
        default='BOB',
    )
    currency_to = fields.Selection(
        [
            ('BOB', 'BOB'),
            ('PEN', 'PEN'),
            ('USD', 'USD'),
            ('USDINT', 'USDINT'),
        ],
        string='Moneda destino',
        required=True,
        default='PEN',
    )
    amount_from = fields.Float(string='Monto origen', required=True, digits=(16, 2))
    amount_to = fields.Float(string='Monto destino', required=True, digits=(16, 2))
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmada'),
            ('processing', 'En proceso'),
            ('done', 'Concluida'),
            ('cancelled', 'Cancelada'),
        ],
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )
    voucher_attached = fields.Boolean(string='Voucher cargado', tracking=True)
    notes = fields.Text(string='Notas internas')

    def _whatsapp_get_currency_pair(self):
        self.ensure_one()
        return self.currency_from, self.currency_to

    def _whatsapp_get_amounts(self):
        self.ensure_one()
        return float(self.amount_from or 0.0), float(self.amount_to or 0.0)

    def _whatsapp_get_operation_number(self):
        self.ensure_one()
        return self.name

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        to_notify = records.filtered(lambda r: r.state in ('confirmed', 'processing', 'draft'))
        if to_notify:
            to_notify.action_whatsapp_notify_operation_created()
        return records

    def write(self, vals):
        previous_states = {rec.id: rec.state for rec in self}
        result = super().write(vals)
        if 'state' in vals or 'voucher_attached' in vals:
            for rec in self:
                old_state = previous_states.get(rec.id)
                if rec.state == 'done' and old_state != 'done':
                    rec.action_whatsapp_notify_operation_concluded()
                elif vals.get('voucher_attached') and rec.state == 'done':
                    rec.action_whatsapp_notify_operation_concluded()
                elif old_state in (False, 'cancelled') and rec.state in ('draft', 'confirmed', 'processing'):
                    rec.action_whatsapp_notify_operation_created()
        return result

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        return True

    def action_process(self):
        self.write({'state': 'processing'})
        return True

    def action_done(self):
        self.write({'state': 'done', 'voucher_attached': True})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    def action_whatsapp_force_opening(self):
        self.write({'whatsapp_notified_open': False})
        return self.action_whatsapp_notify_operation_created()

    def action_whatsapp_force_closing(self):
        self.write({'whatsapp_notified_close': False})
        return self.action_whatsapp_notify_operation_concluded()
