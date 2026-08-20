#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local end-to-end demo of Ragnar WhatsApp bot logic (no Odoo required).

Simulates the three flows from borrador v3 using the same rules as the Odoo module
and standalone unit tests. Kommo and Claude run in mock mode.

Run: python scripts/run_mock_demo.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_core_logic import (  # noqa: E402
    SUPPORTED_PAIRS,
    format_template,
    normalize_phone,
    window_open,
)

TEMPLATE_OPENING = (
    'Generaste una operación en nuestra web. Ya estamos trabajando en ella.'
)
TEMPLATE_CLOSING = (
    'Tu orden ya fue concluida. Revisa tu correo para obtener el voucher.'
)

MOCK_CLAUDE_REPLY = (
    'Gracias por tu mensaje. Tu operación {operation_number} ({amount_from} '
    '{currency_from} -> {amount_to} {currency_to}) esta en proceso.'
)
MOCK_CLAUDE_CLOSING = (
    'Hola {partner_name}, tu operación {operation_number} fue concluida. '
    'Revisa tu correo para el voucher.'
)


@dataclass
class Message:
    direction: str
    body: str
    source: str
    at: datetime = field(default_factory=datetime.now)


@dataclass
class Operation:
    number: str
    partner_name: str
    phone: str
    currency_from: str
    currency_to: str
    amount_from: float
    amount_to: float
    state: str = 'confirmed'


@dataclass
class Conversation:
    partner_name: str
    phone: str
    messages: list[Message] = field(default_factory=list)
    last_inbound_date: datetime | None = None

    def log(self, direction: str, body: str, source: str) -> None:
        now = datetime.now()
        self.messages.append(Message(direction, body, source, now))
        if direction == 'inbound':
            self.last_inbound_date = now

    def is_window_open(self) -> bool:
        return window_open(self.last_inbound_date)

    def history(self, limit: int = 20) -> str:
        recent = self.messages[-limit:]
        lines = []
        for msg in recent:
            role = 'Cliente' if msg.direction == 'inbound' else 'Asistente'
            lines.append(f'{role}: {msg.body}')
        return '\n'.join(lines)


@dataclass
class QueueJob:
    payload_type: str
    body: str | None = None
    state: str = 'pending'


class MockKommo:
    def send(self, phone: str, body: str, payload_type: str) -> dict:
        print(f'  [MOCK Kommo -> {phone}] ({payload_type})')
        print(f'    {body}')
        return {'msgid': f'mock-{len(body)}', 'mock': True}


class MockClaude:
    def reply(self, operation: Operation, inbound: str) -> str:
        print(f'  [MOCK Claude] inbound: {inbound!r}')
        ctx = operation_context(operation)
        return MOCK_CLAUDE_REPLY.format(**ctx)

    def closing(self, operation: Operation) -> str:
        print('  [MOCK Claude] generating closing message')
        ctx = operation_context(operation)
        return MOCK_CLAUDE_CLOSING.format(**ctx)


def operation_context(op: Operation) -> dict:
    return {
        'operation_number': op.number,
        'partner_name': op.partner_name,
        'amount_from': op.amount_from,
        'amount_to': op.amount_to,
        'currency_from': op.currency_from,
        'currency_to': op.currency_to,
        'state': op.state,
    }


def validate_pair(op: Operation) -> bool:
    pair = (op.currency_from, op.currency_to)
    if pair not in SUPPORTED_PAIRS:
        print(f'  [SKIP] Par no soportado: {pair[0]} -> {pair[1]}')
        return False
    return True


def process_job(job: QueueJob, op: Operation, conv: Conversation, kommo: MockKommo, claude: MockClaude) -> None:
    phone = normalize_phone(op.phone)
    if job.payload_type == 'template_opening':
        body = TEMPLATE_OPENING
        source = 'template_opening'
    elif job.payload_type == 'template_closing':
        body = format_template(TEMPLATE_CLOSING, operation_context(op))
        source = 'template_closing'
    elif job.payload_type == 'claude_closing':
        body = claude.closing(op)
        source = 'claude'
    elif job.payload_type == 'claude_reply':
        inbound = job.body or ''
        body = claude.reply(op, inbound)
        source = 'claude'
    else:
        raise ValueError(job.payload_type)

    kommo.send(phone, body, job.payload_type)
    conv.log('outbound', body, source)
    job.state = 'done'


def section(title: str) -> None:
    print()
    print('=' * 60)
    print(title)
    print('=' * 60)


def main() -> int:
    kommo = MockKommo()
    claude = MockClaude()
    conv = Conversation(partner_name='Ana Castro', phone='+59170000001')
    op = Operation(
        number='OP/2026/00122',
        partner_name='Ana Castro',
        phone='+59170000001',
        currency_from='BOB',
        currency_to='PEN',
        amount_from=1000,
        amount_to=550,
    )

    section('FLUJO 1 - Operacion creada -> plantilla apertura')
    print(f'Operacion: {op.number} | {op.currency_from} -> {op.currency_to}')
    if not validate_pair(op):
        return 1
    job1 = QueueJob('template_opening')
    process_job(job1, op, conv, kommo, claude)
    print(f'  Job state: {job1.state}')

    section('FLUJO 3 - Cliente responde -> webhook -> Claude')
    inbound = 'Cuando llega el deposito a la cuenta destino?'
    print(f'  [Webhook POST] Cliente: {inbound}')
    conv.log('inbound', inbound, 'system')
    print(f'  Ventana 24h abierta: {conv.is_window_open()}')
    job3 = QueueJob('claude_reply', body=inbound)
    process_job(job3, op, conv, kommo, claude)

    section('FLUJO 2 - Operacion concluida (ventana ABIERTA -> Claude)')
    op.state = 'done'
    print(f'Estado: {op.state} | ventana: {conv.is_window_open()}')
    job2a = QueueJob('claude_closing')
    process_job(job2a, op, conv, kommo, claude)

    section('FLUJO 2 - Operacion concluida (ventana CERRADA -> plantilla)')
    conv2 = Conversation(partner_name='María López', phone='+59170000002')
    op2 = Operation(
        number='OP/2026/00124',
        partner_name='María López',
        phone='+59170000002',
        currency_from='BOB',
        currency_to='USD',
        amount_from=5000,
        amount_to=725,
        state='done',
    )
    print(f'Operación: {op2.number} | sin mensajes entrantes del cliente')
    print(f'  Ventana 24h abierta: {conv2.is_window_open()}')
    job2b = QueueJob('template_closing')
    process_job(job2b, op2, conv2, kommo, claude)

    section('HISTORIAL — Ana Castro')
    for msg in conv.messages:
        arrow = '->' if msg.direction == 'outbound' else '<-'
        print(f'  {arrow} [{msg.source}] {msg.body[:70]}...' if len(msg.body) > 70 else f'  {arrow} [{msg.source}] {msg.body}')

    section('RESUMEN')
    print('  Modo: MOCK (sin Odoo, Kommo ni Claude reales)')
    print('  Flujos 1, 2 y 3 ejecutados correctamente.')
    print('  Para UI completa: instalar módulo en Odoo 17 o abrir docs/mockup/')
    print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
