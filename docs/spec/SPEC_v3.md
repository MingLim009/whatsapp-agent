# Integración Odoo – Bot IA – Kommo – WhatsApp Business
### Borrador funcional y técnico para el equipo de desarrollo — Ragnar Capital
_Versión 3 — arquitectura y plantillas confirmadas_

## 1. Contexto del proyecto

Los clientes de Ragnar Capital generan órdenes de cambio/envío de dinero (entre distintos pares de moneda) a través de una plataforma web construida sobre Odoo. Odoo es la fuente única de verdad: ahí vive toda la información de clientes, operaciones, montos, estados y comprobantes (vouchers).

El problema que resuelve este proyecto es la ansiedad del cliente mientras espera que su dinero llegue a la cuenta destino, y la falta de un canal donde pueda resolver dudas sobre su operación. La solución es un bot conversacional que notifica proactivamente al cliente por WhatsApp en los momentos clave del ciclo de vida de su operación, y que además puede sostener una conversación si el cliente responde o tiene consultas.

## 2. Arquitectura: todo dentro de Odoo

Decisión confirmada: **no hay ningún servicio externo que orqueste el bot ni que guarde datos del negocio.** Todo — datos, lógica de negocio, disparadores, historial de conversación — vive dentro de Odoo.

El único componente externo que Odoo debe llamar es la **API de Claude (Anthropic)**, usada exclusivamente para redactar el texto de los mensajes dinámicos (la conversación con el cliente una vez abierta la ventana de 24h). Esta llamada es puntual: Odoo le manda el contexto necesario (datos de la operación, historial reciente de esa conversación) y recibe de vuelta el texto a enviar. Claude no almacena ni orquesta nada por su cuenta; es solo el motor de redacción, invocado desde Odoo.

En resumen, las únicas dos integraciones salientes desde Odoo son:
- **Kommo** → para entregar y recibir mensajes de WhatsApp.
- **API de Claude** → para generar el texto de los mensajes conversacionales dinámicos.

No se expone ninguna API de Odoo hacia afuera para que un tercero lea sus datos; es Odoo quien llama hacia afuera cuando lo necesita.

## 3. Reglas de mensajería de WhatsApp Business y plantillas

Meta exige que cualquier mensaje **iniciado por el negocio** (no como respuesta a algo que escribió el cliente) use una **plantilla pre-aprobada**, con variables predefinidas. Un mensaje de texto libre solo se puede enviar dentro de una ventana de conversación de 24 horas, que se abre únicamente cuando el cliente escribe primero.

Esto se traduce en **dos plantillas aprobadas**, confirmadas para este proyecto:

1. **Plantilla de apertura** (fija, igual para todos los clientes), disparada al crear la operación:
   > "Generaste una operación en nuestra web. Ya estamos trabajando en ella."

2. **Plantilla de cierre** (fija/simple, con variables), disparada al concluir la operación, para el caso en que el cliente **no haya respondido** al primer mensaje (por lo tanto la ventana de 24h sigue cerrada):
   > "Tu orden ya fue concluida. Revisa tu correo para obtener el voucher."

Si el cliente sí respondió al primer mensaje (ventana abierta), el mensaje de cierre y cualquier otra respuesta pueden redactarse de forma dinámica vía Claude, sin necesidad de plantilla.

Ambas plantillas deben enviarse a aprobación de Meta a través de Kommo antes de iniciar desarrollo, ya que el proceso de aprobación puede tomar varios días y no debe bloquear el cronograma.

## 4. Flujo 1 — Nueva operación creada

1. El cliente genera una orden en la plataforma web (Odoo).
2. Odoo crea el registro de la operación, le asigna un número de operación y queda en el estado inicial correspondiente.
3. Ese evento dispara la automatización dentro de Odoo.
4. Odoo arma el mensaje de apertura (plantilla 1, sección 3) y lo envía a Kommo para su entrega por WhatsApp.

## 5. Flujo 2 — Operación concluida (voucher cargado)

1. Un operador interno carga en Odoo el voucher que confirma el depósito en la cuenta destino, y la operación pasa al estado "concluida" (usando el flujo de estados que ya existe en Odoo).
2. Ese cambio de estado dispara nuevamente la automatización.
3. Odoo revisa si la conversación con ese cliente ya está "abierta" (el cliente respondió al mensaje de apertura o escribió antes):
   - Si **no** está abierta → se envía la plantilla de cierre (plantilla 2, sección 3).
   - Si **sí** está abierta → Odoo llama a Claude para redactar un mensaje de cierre dinámico y lo envía como texto libre.
4. Se envía por Kommo al WhatsApp del cliente.

## 6. Flujo 3 — Conversación con el cliente

El bot no es solo notificador: si el cliente responde o escribe cualquier consulta, debe poder sostener la conversación.

1. El cliente escribe algo en WhatsApp.
2. Kommo recibe el mensaje y lo notifica a Odoo vía webhook (a configurar en Kommo).
3. Odoo guarda el mensaje entrante en el historial de conversación del cliente (ver sección 8).
4. Odoo arma el contexto (datos de la operación + historial reciente) y llama a Claude para generar la respuesta.
5. Odoo envía la respuesta por Kommo y la guarda también en el historial.

## 7. Multi-moneda

Los mensajes deben construirse dinámicamente según el par de moneda de cada operación. Pares confirmados:

- BOB → PEN
- PEN → BOB
- BOB → USD
- BOB → USDINT (bolivianos a dólares internacionales, enviados vía SWIFT — distinto de USD "normal", no es USDT/stablecoin)

El bot debe tomar el par de la operación desde Odoo y usarlo para completar las variables de monto/moneda origen y destino en cada plantilla o mensaje generado. A confirmar si existen más pares además de los cuatro listados.

## 8. Historial de conversación

Se guarda **dentro de Odoo**, para mantener toda la información centralizada junto con el resto de los datos del cliente y sus operaciones. Esto implica crear un modelo (por ejemplo, algo así como "mensajes de WhatsApp por cliente/operación") con al menos: fecha/hora, dirección (entrante/saliente), texto, operación asociada (si aplica), y si fue generado por plantilla o por Claude. Este historial es el que se le pasa como contexto a Claude en cada respuesta conversacional.

## 9. Volumen esperado

Aproximadamente **500 operaciones por día**. Cada operación genera al menos 2 mensajes salientes (apertura + cierre), más los mensajes de conversación que el cliente inicie. Con esto el desarrollador debe:
- Confirmar con Kommo los límites de envío (rate limits) de su plan/API y de la cuenta de WhatsApp Business asociada.
- Diseñar el envío de mensajes de forma asíncrona/en cola dentro de Odoo (jobs o colas), para no bloquear el flujo de negocio si Kommo o Claude tardan en responder.

## 10. Requisitos técnicos a nivel Odoo

- Identificar el modelo y los valores exactos de estado que representan "operación creada" y "operación concluida" dentro del flujo de estados que ya existe en Odoo.
- El registro del cliente debe tener el número de WhatsApp en formato válido para Kommo (con código de país).
- Automatizaciones en Odoo (Automated Actions, Server Actions o módulo custom) que disparen cada flujo según el cambio de estado correspondiente.
- Módulo/lógica dentro de Odoo que decida cuándo usar plantilla fija vs. respuesta dinámica de Claude, según si la ventana de 24h está abierta (registrar esto por cliente/conversación).
- Integración con la API de Claude: manejo seguro de la API key (almacenada como parámetro de sistema en Odoo, no hardcodeada), y construcción del prompt con el contexto de la operación y el historial.
- Webhook entrante desde Kommo hacia Odoo, para recibir mensajes del cliente y confirmaciones de entrega.
- Manejo de errores: reintentos si Kommo o Claude no responden, con log y alerta a un operador.
- Registro/auditoría en Odoo de todos los mensajes enviados y recibidos, con su estado de entrega.

## 11. Puntos abiertos a definir con el desarrollador antes de empezar

- Enviar ambas plantillas (apertura y cierre) a aprobación de Meta vía Kommo, y estimar el tiempo de aprobación para no bloquear el cronograma.
- Mapear técnicamente los estados de Odoo que disparan cada flujo (creación y conclusión).
- Confirmar la lista completa de pares de moneda soportados (por ahora: BOB/PEN, PEN/BOB, BOB/USD, BOB/USDINT).
- Definir el criterio exacto para considerar una conversación "abierta" (¿cualquier mensaje entrante del cliente, dentro de las últimas 24h?) y cómo se calcula ese estado dentro de Odoo.
- Definir el modelo de datos del historial de conversación (sección 8) con el equipo de desarrollo.
- Confirmar el plan/modelo de Claude a usar (por costo y latencia) y quién administra la API key.

## 12. Resumen para el desarrollador

Todo vive dentro de Odoo: los datos, la lógica de negocio, los disparadores y el historial de conversación. Odoo hace solo dos tipos de llamada saliente: a Kommo (para enviar/recibir WhatsApp) y a la API de Claude (para redactar mensajes dinámicos cuando la conversación está abierta). Hay dos plantillas aprobadas por Meta para los mensajes iniciados por el negocio (apertura de operación y cierre sin respuesta previa del cliente); cualquier otro mensaje, una vez que el cliente escribió, puede ser dinámico. El volumen esperado es de ~500 operaciones/día, con los pares de moneda BOB/PEN, PEN/BOB, BOB/USD y BOB/USDINT, por lo que los mensajes deben construirse de forma dinámica según cada operación.
