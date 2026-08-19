# Referencias de diseño

Imágenes de referencia compartidas para el proyecto.

## 1. dunma — CRM WhatsApp (referencia principal)

**Archivo:** `dunma-whatsapp-crm.png`

Landing page de un CRM de WhatsApp con tablero Kanban:

| Columna | Equivalente en Odoo |
|---------|---------------------|
| Nuevos contactos | `stage = new` — apertura enviada, cliente sin respuesta |
| Chats en progreso | `stage = active` — ventana 24h abierta |
| Negociación en camino | `stage = awaiting` — cliente escribió, pendiente de respuesta |
| Mensajes finalizados | `stage = done` — conversación cerrada |

Implementado en el módulo Odoo como vista Kanban en **WhatsApp Bot → Conversaciones**.

## 2. SHARP-CODE — Página de contacto (referencia secundaria)

**Archivo:** `sharp-code-contact.png`

UI oscura con formulario de contacto + lista de equipo + datos de contacto.
No forma parte del bot WhatsApp; útil si Ragnar Capital necesita una landing o página de soporte web aparte.

## 3. NATURECOIN — Página de contacto (referencia secundaria)

**Archivo:** `naturecoin-contact.png`

Layout similar al anterior (formulario + sidebar). Mismo alcance: sitio web/marketing, no backend Odoo.

## Alcance actual vs. referencias

| Referencia | ¿Incluido en este repo? |
|------------|-------------------------|
| Tablero Kanban WhatsApp (dunma) | Sí — vista Kanban en Odoo |
| Landing marketing tipo dunma | No — requeriría frontend aparte |
| Páginas de contacto oscuras | No — fuera del alcance del PDF v3 |
