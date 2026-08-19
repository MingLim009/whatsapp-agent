# Ragnar Capital — Integración Odoo · Kommo · WhatsApp · Claude

Módulo Odoo 17 listo para instalar. Implementa el borrador funcional/técnico v3.

## Estado

| Área | Estado |
|------|--------|
| Flujos 1, 2 y 3 (apertura, cierre, conversación) | Completo |
| Modelo `ragnar.money.operation` | Completo (usable en producción o como puente) |
| Historial + ventana 24h + Kanban | Completo |
| Cola async + reintentos + alerta operador | Completo |
| Modo mock (sin Kommo/Claude) | Completo (activo por defecto) |
| Credenciales / plantillas Meta / webhook HTTPS | **Pendiente del cliente** |

## Instalación

1. Copiar `ragnar_whatsapp_integration` a `addons/`
2. `pip install -r requirements.txt`
3. Actualizar lista de apps → instalar **Ragnar WhatsApp Integration**
4. Ajustes → WhatsApp Bot (credenciales cuando estén listas)
5. **Desactivar modo mock** solo cuando Kommo y Claude estén configurados

## Uso inmediato (mock)

1. Ir a **WhatsApp Bot → Operaciones**
2. Crear una operación con un contacto que tenga WhatsApp (`+591...`)
3. Procesar la cola (cron cada 1 min, o menú Cola de envío → Reintentar)
4. Ver mensajes en **Mensajes** / **Conversaciones**

## Webhook

- Health: `GET {base_url}/whatsapp/kommo/webhook` → `ragnar_whatsapp_webhook_ok`
- Inbound: `POST {base_url}/whatsapp/kommo/webhook`

## Documentación

- [Entrega / handoff](docs/HANDOFF.md)
- [Checklist go-live](docs/INTEGRATION_CHECKLIST.md)
- [Referencias de diseño](docs/DESIGN_REFERENCES.md)

## Mockup visual (cliente)

Demo multipágina profesional para presentar el proyecto:

```
docs/mockup/index.html
```

Abrir en cualquier navegador. Incluye 7 vistas navegables:

- **Resumen** — arquitectura y avance 70%
- **Flujos del bot** — apertura, cierre, conversación
- **Operaciones** — tabla y detalle de operaciones de cambio
- **Conversaciones** — Kanban + preview WhatsApp
- **Historial** — auditoría de mensajes
- **Cola de envío** — jobs async y reintentos
- **Configuración** — Kommo, Claude, Odoo


## Arquitectura (resumen)

Todo vive en Odoo. Salidas: Kommo (WhatsApp) y Claude (texto dinámico).  
Plantillas Meta solo para mensajes iniciados por el negocio sin ventana 24h abierta.
