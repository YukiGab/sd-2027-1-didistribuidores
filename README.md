# DiDistribuidores: sistema de gestión y entrega de pedidos

## ¿Qué es el sistema?

Es un sistema distribuido para pedidos de comida a domicilio. Un cliente consulta el menú de un
restaurante, hace un pedido, lo paga (pago simulado) y un repartidor lo recoge y lo entrega.

Su prioridad es la **consistencia sobre la disponibilidad**: preferimos retrasar o rechazar un
pedido antes que perderlo, duplicarlo o cobrarlo dos veces.

Garantías que nunca se rompen:

- Nunca se cobra un pedido que no se confirmó.
- Nunca se pierde un pedido ya confirmado.
- Un reintento con la misma `Idempotency-Key` devuelve el mismo pedido, sin segundo cobro.
- La entrega se registra una sola vez, aunque el repartidor confirme dos veces.

## ¿Quiénes somos?

- Yukioayax Canek Gabriel Hernández ([@YukiGab](https://github.com/YukiGab))
- Erick Isaac Echeverria Goicochea ([@ErickI07](https://github.com/ErickI07))

Materia: Sistemas Distribuidos 2027-1, Grupo 2, FI-UNAM.

## ¿Cómo se levanta?

Requisitos: Docker y Docker Compose.

```bash
cd Proyecto
docker compose up --build
```

La aplicación queda en <http://localhost:8000> (documentación interactiva en `/docs`).
Al arrancar con la base vacía se cargan datos de prueba: 3 restaurantes con menú y 5 repartidores.

```bash
docker compose down        # apaga conservando los datos
docker compose down -v     # apaga y borra los datos (se vuelven a cargar los de prueba)
```

## Endpoints principales

| Método y ruta | Qué hace |
|---|---|
| `GET /salud` | Comprueba que la app y la base responden |
| `POST /api/usuarios`, `GET /api/usuarios/{id}` | Crear y consultar un usuario |
| `GET /api/restaurantes`, `GET /api/restaurantes/{id}/platillos` | Restaurantes y su menú |
| `POST /api/pedidos` (header `Idempotency-Key`) | Crear un pedido de forma idempotente |
| `GET /api/pedidos/{id}` | Consultar un pedido |
| `POST /api/pedidos/{id}/pago` | Pagar el pedido |
| `GET /api/pagos/{pedido_id}` | Consultar el pago de un pedido |
| `POST /api/repartidores`, `GET /api/repartidores/{id}` | Crear y consultar repartidores |
| `GET /api/pedidos/disponibles?repartidor_id=` | Pedidos pagados de la zona del repartidor |
| `POST /api/pedidos/{id}/aceptar` | Un repartidor toma el pedido (gana el primero) |
| `POST /api/pedidos/{id}/entrega` | Confirmar la entrega con el código |

Los pedidos pasan por los estados `PENDIENTE_PAGO → PAGADO → ASIGNADO → ENTREGADO`. Si nadie paga a
tiempo, o nadie toma un pedido pagado, el pedido se cancela y, si había cobro, se reembolsa.

## Estructura del repositorio

```
.
├── README.md
├── docs/
│   ├── PRD.md              requisitos, alcance y decisiones de arquitectura
│   ├── eventos.md          contrato de los eventos entre servicios
│   └── reporte_etapa1.md   reporte técnico detallado de la etapa 1
└── Proyecto/
    ├── docker-compose.yml
    ├── Dockerfile
    ├── requirements.txt
    ├── db/                 esquema, datos de prueba y tabla outbox
    └── app/
        ├── main.py, config.py, db.py, errores.py
        └── modulos/        usuarios, restaurantes, pedidos, pagos, repartidores, notificaciones
```

Cada módulo tiene tres capas: `router.py` (HTTP), `servicio.py` (reglas de negocio) y `repositorio.py`
(SQL). Un módulo solo habla con otro a través de su `servicio.py`.

## Configuración

Variables de entorno de la aplicación (se definen en `docker-compose.yml`):

| Variable | Valor en el compose | Descripción |
|---|---|---|
| `TIMEOUT_PAGO_SEG` | 30 | Segundos antes de cancelar un pedido sin pagar (valor normal: 600) |
| `TIMEOUT_ASIGNACION_SEG` | 60 | Segundos antes de cancelar y reembolsar un pedido pagado sin repartidor (valor normal: 1200) |
| `REVISION_TIMEOUTS_SEG` | 5 | Cada cuántos segundos se revisan los pedidos vencidos |
| `OUTBOX_ACTIVO` | 1 | Guarda los eventos de pedidos en `pedidos.outbox` |

## Etapa 1: monolito modular

La primera etapa construye todo el sistema como una sola aplicación con una sola base de datos,
pero organizada en módulos (`usuarios`, `restaurantes`, `pedidos`, `pagos` y `repartidores`). La idea
es resolver primero la lógica de negocio y las fronteras entre módulos, para que después separar un
módulo en un servicio sea cambiar una llamada a función por una llamada de red.

**Consistencia.** Como la prioridad del sistema es no duplicar ni perder pedidos, las garantías no
dependen del código de Python sino de la base de datos:

- La **idempotencia** se resuelve con una restricción `UNIQUE` sobre la clave de cada pedido. Si
  llegan varias peticiones iguales a la vez, la base deja pasar una y las demás reciben el mismo pedido.
- El **estado del pedido** avanza con `UPDATE` condicionales que incluyen el estado de origen. Así
  solo una petición consigue cada cambio, aunque lleguen varias al mismo tiempo (pagar, aceptar un
  repartidor, confirmar la entrega).
- Cobrar o reembolsar y cambiar el estado ocurren en **una sola transacción**, por eso `pagos` vive
  dentro del núcleo y no como servicio aparte.
- Los pedidos que no avanzan se **cancelan por tiempo**, con dos relojes configurables (pago y
  asignación de repartidor), y si ya había cobro se reembolsa en la misma transacción.
- Cada cambio de estado deja un **evento** en la tabla `outbox`, listo para que en la etapa 2 se
  publique a la cola de mensajes.

## Plan de ramas

El sistema empieza como un monolito y se parte por etapas, cada una en su rama.

| Rama | Qué se comprueba | Estado |
|---|---|---|
| `main` | README y PRD | Listo |
| `01-monolito` | Una aplicación y una base. Flujo completo de pedidos con idempotencia | Listo |
| `02-separacion` | `notificaciones` como proceso aparte, con cola persistente. Los pedidos siguen funcionando con ese proceso apagado | Pendiente |
| `03-separacion` | `repartidores` como servicio propio; gana el primer repartidor que acepta | Pendiente |
| `04-resiliencia` | Reintentos, deduplicación, timeout con reembolso, circuit breaker y pruebas de caídas | Pendiente |

## Estado actual

- **Etapa 0:** terminada. El alcance del PRD se redujo y se acordó con el profesor: un núcleo con
  `pedidos` y `pagos`, y dos servicios que se separarán, `notificaciones` y `repartidores`.
- **Etapa 1 (`01-monolito`):** terminada. El monolito modular cubre el flujo completo: crear un
  pedido de forma idempotente, pagarlo, asignarlo a un repartidor, confirmar la entrega y cancelar
  con reembolso los pedidos vencidos. Los eventos de cada cambio de estado se guardan en
  `pedidos.outbox`, pero todavía no se publican a ninguna cola.
- **Siguiente:** etapa 2, separar `notificaciones` como proceso aparte con una cola persistente.

## Documentación

- [PRD](docs/PRD.md): problema, alcance, "dónde vive cada pieza" y decisiones de arquitectura.
- [Contrato de eventos](docs/eventos.md): formato de los eventos entre `pedidos` y `notificaciones`.
- [Reporte de la etapa 1](docs/reporte_etapa1.md): explicación paso a paso de lo construido.
