# Decisiones técnicas — Borrador v3

Documento que cierra los **puntos abiertos** de la sección 11 del borrador funcional/técnico v3, con las decisiones adoptadas en el módulo `ragnar_whatsapp_integration`.

Referencia: [SPEC_v3.md](spec/SPEC_v3.md)

---

## 1. Plantillas Meta

| Plantilla | Texto acordado | Disparo |
|-----------|----------------|---------|
| Apertura | *"Generaste una operación en nuestra web. Ya estamos trabajando en ella."* | Creación de operación |
| Cierre (ventana cerrada) | *"Tu orden ya fue concluida. Revisa tu correo para obtener el voucher."* | Estado concluida |

**Implementación:** textos en parámetros de sistema (`ragnar_whatsapp.template_*_body`); IDs Kommo/Meta en Ajustes cuando estén aprobados.

**Pendiente del cliente:** envío a aprobación Meta vía Kommo y entrega de `kommo_template_opening_id` / `kommo_template_closing_id`.

---

## 2. Estados Odoo que disparan cada flujo

Configurable en **Ajustes → WhatsApp Bot**:

| Parámetro | Valor por defecto | Uso |
|-----------|-------------------|-----|
| `operation_created_states` | `draft,confirmed,processing,new,pending` | Flujo 1 — apertura |
| `operation_concluded_states` | `done,concluded,completed` | Flujo 2 — cierre |

**Modelo demo:** `ragnar.money.operation` dispara automáticamente en `create` (estados iniciales) y en `write` al pasar a `done`.

**Modelo real del cliente:** heredar `whatsapp.operation.mixin` y enlazar server actions (ver [MAPPING_GUIDE.md](MAPPING_GUIDE.md)).

---

## 3. Pares de moneda soportados

Confirmados en código (`SUPPORTED_CURRENCY_PAIRS`):

- BOB → PEN
- PEN → BOB
- BOB → USD
- BOB → USDINT (SWIFT; no USDT/stablecoin)

Operaciones con pares no soportados **no encolan WhatsApp** y registran warning en log. A confirmar con Ragnar si hay pares adicionales.

---

## 4. Criterio “ventana abierta” (24 h)

**Decisión:** una conversación está abierta si el cliente envió al menos un mensaje entrante y `last_inbound_date` es posterior a `now - 24 horas`.

- Campo: `whatsapp.conversation.last_inbound_date`
- Computed: `whatsapp.conversation.window_open`
- Se actualiza en cada mensaje entrante (webhook Kommo)

Esto cumple la regla Meta: texto libre solo dentro de 24 h desde el último mensaje del cliente.

---

## 5. Modelo de historial de conversación

| Modelo | Rol |
|--------|-----|
| `whatsapp.conversation` | Una conversación por cliente; ventana 24 h, IDs Kommo, Kanban |
| `whatsapp.message` | Cada mensaje: fecha, dirección, texto, operación, origen (plantilla/Claude), estado entrega |
| `whatsapp.message.queue` | Cola async; reintentos (máx. 5) y alerta a administradores |

El historial reciente (últimos 20 mensajes) se pasa a Claude en cada respuesta.

---

## 6. Claude — modelo y administración

| Parámetro | Valor por defecto |
|-----------|-------------------|
| Modelo | `claude-3-5-haiku-20241022` |
| Max tokens | 512 |
| API key | Parámetro `ragnar_whatsapp.claude_api_key` en Ajustes |

Haiku por balance costo/latencia (~500 ops/día). La API key la administra Ragnar Capital en su instancia Odoo.

---

## 7. Volumen y cola async

~500 operaciones/día → mínimo ~1000 mensajes salientes (apertura + cierre).

**Implementación:** cron cada 1 min procesa `whatsapp.message.queue` en lotes de 50; backoff exponencial en reintentos.

**Pendiente del cliente:** confirmar rate limits del plan Kommo / WhatsApp Business.

---

## 8. Webhook Kommo

- URL: `{web.base.url}/whatsapp/kommo/webhook`
- `GET` → health check (`ragnar_whatsapp_webhook_ok`)
- `POST` → mensajes entrantes del cliente (+ actualización opcional de estado de entrega si Kommo lo reporta)
- Firma HMAC-SHA1 con `channel_secret`
- Respuesta en &lt; 5 s; procesamiento en cola

---

## 9. Modo mock

Activo por defecto (`ragnar_whatsapp.mock_mode = True`) para desarrollo sin credenciales. Desactivar solo en staging/producción con Kommo y Claude configurados.
