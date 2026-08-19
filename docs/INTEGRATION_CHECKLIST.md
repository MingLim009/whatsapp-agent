# Checklist de integración / go-live

## Completado en el código (desarrollo)

- [x] Flujos apertura / cierre / conversación
- [x] Modelo `ragnar.money.operation`
- [x] Historial y ventana 24h
- [x] Cola async + reintentos + alerta
- [x] Modo mock
- [x] Webhook GET/POST (+ estado de entrega)
- [x] Kanban de conversaciones
- [x] Validación pares de moneda
- [x] Server actions + guía de mapeo
- [x] Especificación v3 consolidada en `docs/spec/`
- [x] Tests unitarios

## Antes del go-live (cliente)

- [ ] Plantilla de apertura aprobada en Meta
- [ ] Plantilla de cierre aprobada en Meta
- [ ] Canal Kommo: `scope_id` + `channel_secret` + `account_id`
- [ ] Webhook Kommo → `{base_url}/whatsapp/kommo/webhook` responde 200
- [ ] API key Claude configurada
- [ ] **Modo mock desactivado** en producción
- [ ] Contactos con WhatsApp E.164 (`+591...`)
- [ ] Rate limits Kommo confirmados (~1000+ msgs/día)

## Pruebas staging

1. Crear operación BOB→PEN → plantilla apertura (o mock log)
2. POST webhook simulado → respuesta Claude/mock en cola
3. Concluir con ventana abierta → cierre dinámico
4. Concluir sin respuesta previa → plantilla cierre
5. Forzar fallo → reintentos + alerta
6. Revisar Kanban y historial
