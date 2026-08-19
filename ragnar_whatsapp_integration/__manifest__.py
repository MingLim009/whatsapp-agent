{
    'name': 'Ragnar WhatsApp Integration (Odoo – Kommo – Claude)',
    'version': '17.0.1.2.0',
    'category': 'Sales/CRM',
    'summary': 'WhatsApp bot for money-exchange operations via Kommo and Claude AI',
    'description': """
        Integración Odoo – Bot IA – Kommo – WhatsApp Business (Ragnar Capital).

        Notificaciones proactivas y conversación con clientes sobre operaciones de cambio/envío
        de dinero. Toda la lógica vive en Odoo; las únicas integraciones externas son Kommo
        (WhatsApp) y la API de Claude (redacción dinámica).

        Incluye modelo de operaciones listo para usar (ragnar.money.operation), modo mock
        para pruebas sin credenciales, cola asíncrona, historial y tablero Kanban.
    """,
    'author': 'Ragnar Capital',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        'security/whatsapp_security.xml',
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'data/cron_data.xml',
        'data/server_actions.xml',
        'views/whatsapp_message_views.xml',
        'views/whatsapp_conversation_views.xml',
        'views/whatsapp_queue_views.xml',
        'views/ragnar_money_operation_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'external_dependencies': {
        'python': ['requests'],
    },
}
