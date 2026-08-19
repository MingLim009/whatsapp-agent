# Guía de mapeo — Modelo real de operaciones

Cuando Ragnar Capital tenga su modelo de operaciones identificado en Odoo, siga estos pasos para conectar el bot WhatsApp sin reescribir la lógica.

---

## Opción A — Usar el modelo demo incluido

Si no existe aún un modelo dedicado, use `ragnar.money.operation` (menú **WhatsApp Bot → Operaciones**). Ya incluye:

- Pares BOB/PEN/USD/USDINT
- Disparo automático de apertura y cierre
- Vistas y secuencia `OP/AÑO/#####`

En Ajustes, confirme: **Modelo técnico de operación** = `ragnar.money.operation` (valor por defecto).

---

## Opción B — Conectar modelo existente

### 1. Heredar el mixin

En su módulo (o extensión de `ragnar_whatsapp_integration`):

```python
class SuModeloOperacion(models.Model):
    _name = 'su.modulo.operacion'  # nombre real
    _inherit = ['su.modulo.operacion', 'whatsapp.operation.mixin']
```

### 2. Implementar hooks (si los nombres de campo difieren)

Override solo lo necesario en el mixin:

| Método | Propósito | Campos por defecto |
|--------|-----------|-------------------|
| `_whatsapp_get_partner()` | Cliente | `partner_id` o `customer_id` |
| `_whatsapp_get_operation_number()` | Número op. | `operation_number`, `name`, `reference` |
| `_whatsapp_get_currency_pair()` | Par moneda | `currency_from_id` / `currency_to_id` |
| `_whatsapp_get_amounts()` | Montos | `amount_from`, `amount_to` |
| `_whatsapp_is_created_state()` | Estado apertura | configurable vía Ajustes |
| `_whatsapp_is_concluded_state()` | Estado cierre | configurable vía Ajustes |

### 3. Server actions (incluidas en el módulo)

Tras instalar/actualizar, en **Ajustes → Técnico → Acciones del servidor**:

- **WhatsApp: notificar apertura de operación** → ejecutar al crear / confirmar operación
- **WhatsApp: notificar cierre de operación** → ejecutar al pasar a estado concluida

Enlácelas con **Acciones automatizadas** sobre su modelo:

| Automatización | Trigger | Acción |
|----------------|---------|--------|
| Apertura | Al crear registro (o al confirmar) | Server action apertura |
| Cierre | Al actualizar campo `state` → valor concluido | Server action cierre |

### 4. Actualizar Ajustes

- **Modelo técnico de operación** → `su.modulo.operacion`
- **Estados creada** → valores reales (ej. `confirmed,processing`)
- **Estados concluida** → valores reales (ej. `done`)

### 5. Contactos

Cada cliente debe tener **WhatsApp** en formato E.164 (`+591...`) en el campo `whatsapp_phone`, `mobile` o `phone`.

---

## Checklist de verificación

1. Crear operación de prueba → job `template_opening` en cola
2. Simular webhook entrante → job `claude_reply` en cola
3. Concluir operación sin respuesta previa → `template_closing`
4. Concluir con ventana 24 h abierta → `claude_closing`
5. Revisar historial en **WhatsApp Bot → Mensajes**

Ver también: [INTEGRATION_CHECKLIST.md](INTEGRATION_CHECKLIST.md)
