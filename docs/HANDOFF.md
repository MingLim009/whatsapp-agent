# Entrega — Integración Odoo · Kommo · WhatsApp · Claude

**Proyecto:** Ragnar Capital  
**Módulo:** `ragnar_whatsapp_integration` v17.0.1.1.0  
**Estado:** Completo a nivel de código. Pendiente solo configuración del cliente.

## Qué se entrega

Un módulo Odoo 17 instalable que implementa los 3 flujos del PDF v3:

1. Apertura al crear operación (plantilla Meta)
2. Cierre al concluir (plantilla o Claude según ventana 24h)
3. Conversación entrante vía webhook Kommo + respuesta Claude

Incluye además:

- Modelo de operaciones `ragnar.money.operation` (listo para usar o sustituir)
- Historial, cola async con reintentos y alerta a operadores
- Tablero Kanban de conversaciones
- **Modo mock** activo por defecto (pruebas sin Kommo/Claude reales)
- Datos demo, secuencias, grupos de seguridad
- Tests unitarios standalone

## Instalación rápida

```bash
# 1. Copiar módulo a addons de Odoo 17
cp -r ragnar_whatsapp_integration /path/to/odoo/addons/

# 2. Dependencia Python
pip install -r requirements.txt

# 3. Actualizar apps e instalar "Ragnar WhatsApp Integration"
# 4. (Opcional) cargar datos demo al instalar
```

## Prueba local sin credenciales

1. Dejar **Modo mock = True** (Ajustes → WhatsApp Bot)
2. Crear operación en **WhatsApp Bot → Operaciones**
3. Ejecutar cron o procesar cola: `whatsapp.message.queue` → jobs en estado `done`
4. Revisar **Mensajes** / **Conversaciones**

Para simular mensaje entrante (mock):

```http
POST /whatsapp/kommo/webhook
Content-Type: application/json

{
  "time": 1720000000,
  "message": {
    "sender": {"id": "client-1", "phone": "+59170000001", "name": "Cliente"},
    "receiver": {"id": "bot"},
    "conversation": {"id": "conv-demo"},
    "timestamp": 1720000000,
    "message": {"id": "msg-1", "type": "text", "text": "¿Cómo va mi operación?"}
  }
}
```

## Lo que el cliente debe proveer (bloqueantes)

| Ítem | Para qué |
|------|----------|
| Credenciales Kommo | Envío real WhatsApp |
| Plantillas Meta aprobadas + IDs | Apertura / cierre fuera de ventana 24h |
| API key Claude | Respuestas dinámicas reales |
| URL HTTPS pública de Odoo | Webhook entrante |
| (Opcional) Modelo propio de operaciones | Si no usan `ragnar.money.operation` |

## Tests

```bash
python -m unittest tests.test_core_logic -v
```

## Estructura

```
ragnar_whatsapp_integration/   # módulo Odoo
docs/                          # checklists y referencias
tests/                         # tests unitarios
README.md
requirements.txt
```
