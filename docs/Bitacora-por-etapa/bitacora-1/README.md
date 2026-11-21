# Etapa 1: monolito modular

**Rama:** `01-monolito` · **Bitácora:** `bitacora-etapa-01.pdf` (27 figuras) · [Volver al índice de bitácoras](../README.md)

La primera etapa construye todo el sistema como una sola aplicación con una sola base de datos, pero organizada en módulos (`usuarios`, `restaurantes`, `pedidos`, `pagos` y `repartidores`). La idea es resolver primero la lógica de negocio y las fronteras entre módulos, para que después separar un módulo en un servicio sea cambiar una llamada a función por una llamada de red.

Cada módulo tiene tres capas: `router.py` (recibe la petición HTTP), `servicio.py` (reglas del negocio) y `repositorio.py` (ejecuta el SQL). Un módulo solo habla con otro a través de su `servicio.py`.

**Consistencia.** Como la prioridad del sistema es no duplicar ni perder pedidos, las garantías no dependen del código de Python sino de la base de datos:

* La **idempotencia** se resuelve con una restricción `UNIQUE` sobre el usuario y la clave de cada pedido (`Idempotency-Key`). Si llegan varias peticiones iguales a la vez, la base deja pasar una y las demás reciben el mismo pedido.
* El **estado del pedido** avanza con `UPDATE` condicionales que incluyen el estado de origen. Así solo una petición consigue cada cambio, aunque lleguen varias al mismo tiempo (pagar, aceptar un repartidor, confirmar la entrega).
* Cobrar o reembolsar y cambiar el estado ocurren en **una sola transacción**, por eso `pagos` vive dentro del núcleo y no como servicio aparte.
* Los pedidos que no avanzan se **cancelan por tiempo**, con dos relojes configurables (pago y asignación de repartidor), y si ya había cobro se reembolsa en la misma transacción.
* Cada cambio de estado deja un **evento** en la tabla `outbox`, listo para publicarse a la cola de mensajes (lo que se hace en la etapa 2).

El pedido recorre los estados `PENDIENTE_PAGO → PAGADO → ASIGNADO → ENTREGADO`, o termina en `CANCELADO` si no avanza a tiempo. El total lo calcula el servidor con los precios del menú, nunca el cliente.

## Qué se probó

| Prueba | Resultado observado | Figuras |
|---|---|---|
| Arranque y `/salud` | La aplicación y la base están conectadas | 1 |
| Usuarios y restaurantes | Se crean y consultan; un identificador mal formado se rechaza antes de llegar a la base | 2 |
| Pedido y su reintento (misma clave) | `201` la primera vez, `200` después con el mismo pedido | 3 y 4 |
| Cinco peticiones simultáneas con la misma clave | Un `201`, cuatro `200` y un solo pedido en la base | 5 |
| Peticiones inválidas | `400` sin clave, `422` con platillo inexistente, `404` con usuario inexistente | 6 a 8 |
| Pago repetido y simultáneo | Un solo cobro y versión 2 | 9 a 11 |
| Dos repartidores aceptan a la vez | Uno recibe `200`, otro `409`; el pedido queda `ASIGNADO` con versión 3 | 12 a 15 |
| Entrega repetida y simultánea | Una sola entrega, versión 4 | 16 a 19 |
| Cancelación por tiempo | `sin_pago` sin reembolso; `sin_repartidor` con reembolso; un pedido asignado no se cancela | 20 a 23 |
| Infraestructura y outbox | Base `healthy`, 3 restaurantes, 9 platillos y 5 repartidores, y tres eventos en el outbox (versiones 2, 3 y 4) | 24 a 27 |

**Un número que prueba la idea.** Un pedido completo termina en la versión 4 (creado, pagado, asignado, entregado). Si la entrega hubiera ocurrido más de una vez, la versión sería mayor.

## Cómo repetir las pruebas

Las pruebas se corrieron a mano; cada una trae su comando en la bitácora. En esta etapa el sistema responde en `http://localhost:8000`.

```bash
cd Proyecto
docker compose down -v        # los scripts de db/ solo corren con el volumen vacío
docker compose up --build -d
curl http://localhost:8000/salud
```

Las figuras 1 a 23 se hicieron en una terminal de Linux y las 24 a 27 en PowerShell.

## Lo que quedó pendiente para la siguiente etapa

Los eventos del outbox quedan con `publicado_en` nulo: el publicador hacia RabbitMQ llega en la etapa 2.

## Quién hizo qué

| Integrante | Aportes |
|---|---|
| Erick Isaac Echeverria Goicochea ([@ErickI07](https://github.com/ErickI07)) | Estructura de módulos y esquema SQL; arranque, pool de conexiones y manejo de errores; usuarios y restaurantes; pedidos con idempotencia; pagos; repartidores y aceptación; entrega; cancelación por tiempo con reembolso; pruebas de los pasos 1 a 7 y pull request de la etapa. |
| Yukioayax Canek Gabriel Hernández ([@YukiGab](https://github.com/YukiGab)) | Docker Compose final (PostgreSQL 17, volúmenes y healthchecks), datos semilla y tabla `outbox`; pruebas de la infraestructura; revisión del pull request. |
| Los dos | Decisiones de alcance y diseño del PRD, contrato de eventos, revisión cruzada, evidencias y bitácora. |
