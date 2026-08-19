# -*- coding: utf-8 -*-
"""Standalone unit tests (no Odoo runtime required).

Run: python -m unittest tests.test_core_logic -v
"""
import hashlib
import hmac
import re
import unittest
from datetime import datetime, timedelta, timezone


def normalize_phone(phone):
    if not phone:
        return False
    digits = re.sub(r'[^\d+]', '', phone.strip())
    if not digits.startswith('+'):
        digits = f'+{digits.lstrip("0")}'
    return digits


def format_template(template_body, operation):
    replacements = {
        '{{operation_number}}': operation.get('operation_number', ''),
        '{{amount_from}}': str(operation.get('amount_from', '')),
        '{{amount_to}}': str(operation.get('amount_to', '')),
        '{{currency_from}}': operation.get('currency_from', ''),
        '{{currency_to}}': operation.get('currency_to', ''),
        '{{partner_name}}': operation.get('partner_name', ''),
    }
    result = template_body
    for key, value in replacements.items():
        result = result.replace(key, value or '')
    return result


def window_open(last_inbound_date, now=None):
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    if not last_inbound_date:
        return False
    return last_inbound_date >= now - timedelta(hours=24)


def verify_signature(raw_body, signature_header, secret):
    if not secret or not signature_header:
        return False
    expected = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha1).hexdigest().lower()
    return hmac.compare_digest(expected, signature_header.lower())


SUPPORTED_PAIRS = {('BOB', 'PEN'), ('PEN', 'BOB'), ('BOB', 'USD'), ('BOB', 'USDINT')}


class TestPhoneNormalize(unittest.TestCase):
    def test_e164(self):
        self.assertEqual(normalize_phone('+591 7000-0001'), '+59170000001')

    def test_add_plus(self):
        self.assertEqual(normalize_phone('59170000001'), '+59170000001')


class TestTemplateFormat(unittest.TestCase):
    def test_variables(self):
        text = format_template(
            'Hola {{partner_name}}, op {{operation_number}}: {{amount_from}} {{currency_from}}',
            {
                'partner_name': 'Ana',
                'operation_number': 'OP/2026/00001',
                'amount_from': 1000,
                'currency_from': 'BOB',
            },
        )
        self.assertEqual(text, 'Hola Ana, op OP/2026/00001: 1000 BOB')


class TestWindow24h(unittest.TestCase):
    def test_open(self):
        now = datetime(2026, 8, 19, 15, 0, 0)
        self.assertTrue(window_open(now - timedelta(hours=2), now=now))

    def test_closed(self):
        now = datetime(2026, 8, 19, 15, 0, 0)
        self.assertFalse(window_open(now - timedelta(hours=25), now=now))

    def test_no_inbound(self):
        self.assertFalse(window_open(None))


class TestKommoSignature(unittest.TestCase):
    def test_valid(self):
        body = b'{"message":"hola"}'
        secret = 'test-secret'
        sig = hmac.new(secret.encode(), body, hashlib.sha1).hexdigest()
        self.assertTrue(verify_signature(body, sig, secret))

    def test_invalid(self):
        self.assertFalse(verify_signature(b'x', 'bad', 'secret'))


class TestCurrencyPairs(unittest.TestCase):
    def test_confirmed_pairs(self):
        self.assertIn(('BOB', 'PEN'), SUPPORTED_PAIRS)
        self.assertIn(('BOB', 'USDINT'), SUPPORTED_PAIRS)
        self.assertNotIn(('USD', 'BOB'), SUPPORTED_PAIRS)


if __name__ == '__main__':
    unittest.main()
