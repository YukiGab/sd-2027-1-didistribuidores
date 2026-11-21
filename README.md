# DiDistribuidores: sistema de gestión y entrega de pedidos

## ¿Qué es el sistema?

Es un sistema distribuido para pedidos de comida a domicilio. Un cliente consulta el menú de un
restaurante, hace un pedido, lo paga y un repartidor lo recoge y lo entrega.

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

## Arquitectura en una vista

```
        clientes: interfaz.py, panel web (/panel/), Swagger (/docs), curl
                              │  HTTP, puerto 8080
                              ▼
                     Traefik (gateway)
        ┌─────────────────────┼──────────────────────┐
        ▼                     ▼                      ▼
     Núcleo            Repartidores            Notificaciones
 (usuarios, restau-   (2 copias, sin estado)   (consumidor + API)
  rantes, pedidos,           ▲                        ▲
  pagos, outbox,             │ HTTP directo, tiempo   │ eventos
  circuit breaker)           │ límite y breaker       │
        └────────────────────┘                  RabbitMQ (cola persistente)
        │  outbox → publicador ───────────────────────┘
        ▼
   PostgreSQL: didistribuidores · repartidores_db · notificaciones_db
```

- **Núcleo:** usuarios, restaurantes, pedidos y pagos. Es el dueño del estado del pedido.
- **Repartidores:** quién es cada repartidor, su zona y su disponibilidad. Corre en dos copias.
- **Notificaciones:** consume los eventos de los pedidos y guarda los avisos del cliente.
- **Traefik:** única entrada al sistema, enruta cada petición y reparte la carga entre copias.
- **RabbitMQ:** cola persistente entre el núcleo y notificaciones.

## ¿Cómo se levanta?

Requisitos: Docker y Docker Compose (y Python 3.9).

```bash
cd Proyecto
docker compose up --build
```

Todo el sistema entra por un solo puerto, el del gateway: <http://localhost:8080>. 
El panel de Traefik queda en <http://localhost:8081> y la consola de RabbitMQ en <http://localhost:15672> (usuario `sd`, contraseña `sd`).
Al arrancar con las bases vacías se cargan datos de prueba: 3 restaurantes con menú y 5 repartidores.

```bash
docker compose ps          # siete contenedores
docker compose down        # apaga conservando los datos
docker compose down -v     # apaga y borra los datos (se vuelven a cargar los de prueba)
```

> Hay que usar `docker compose down -v` al cambiar de etapa o de rama: los scripts de la carpeta
> `db/` solo se ejecutan cuando el volumen está vacío.

## Interfaces

| Interfaz | Cómo se abre | Para qué |
|---|---|---|
| Aplicación de escritorio | `python interfaz/interfaz.py` (desde `Proyecto/`) | Pedir y pagar como cliente, aceptar y entregar como repartidor, y ver el estado del sistema. Solo usa la biblioteca estándar de Python |
| Panel web | <http://localhost:8080/panel/> | La demostración para la presentación: cliente y repartidor, pruebas y arquitectura |
| Swagger | <http://localhost:8080/docs> | Probar cada endpoint a mano |

Las dos interfaces solo llaman a la API por el gateway: muestran, nunca deciden. El uso paso a paso,
con capturas, está en el [manual de usuario](docs/manual-de-usuario.pdf).

## Endpoints principales

Todos los endpoints se consumen por el gateway (`http://localhost:8080`); él decide qué servicio contesta.

| Método y ruta | Qué hace | Servicio |
|---|---|---|
| `GET /salud` | Comprueba que la app y la base responden | Núcleo |
| `GET /estado` | Estado del circuito hacia repartidores y eventos pendientes de publicar | Núcleo |
| `POST /api/usuarios`, `GET /api/usuarios/{id}` | Crear y consultar un usuario | Núcleo |
| `GET /api/restaurantes`, `GET /api/restaurantes/{id}/platillos` | Restaurantes y su menú | Núcleo |
| `POST /api/pedidos` (header `Idempotency-Key`) | Crear un pedido de forma idempotente | Núcleo |
| `GET /api/pedidos/{id}` | Consultar un pedido | Núcleo |
| `POST /api/pedidos/{id}/pago` | Pagar el pedido | Núcleo |
| `GET /api/pagos/{pedido_id}` | Consultar el pago de un pedido | Núcleo |
| `GET /api/pedidos/disponibles?repartidor_id=` | Pedidos pagados de la zona del repartidor | Núcleo |
| `POST /api/pedidos/{id}/aceptar` | Un repartidor toma el pedido (gana el primero) | Núcleo |
| `POST /api/pedidos/{id}/entrega` | Confirmar la entrega con el código | Núcleo |
| `POST /api/repartidores`, `GET /api/repartidores/{id}` | Crear y consultar repartidores | Repartidores |
| `GET /api/repartidores?zona=` | Lista los repartidores, con filtros por zona y disponibilidad | Repartidores |
| `PATCH /api/repartidores/{id}` | Cambia la disponibilidad de un repartidor | Repartidores |
| `GET /api/notificaciones?usuario_id=` | Avisos de un usuario | Notificaciones |
| `GET /api/notificaciones/pedido/{id}` | Avisos de un pedido, ordenados por versión | Notificaciones |
| `GET /api/notificaciones/pedido/{id}/ultimo` | El aviso más reciente de un pedido | Notificaciones |

Los pedidos pasan por los estados `PENDIENTE_PAGO → PAGADO → ASIGNADO → ENTREGADO`. Si nadie paga a
tiempo, o nadie toma un pedido pagado, el pedido se cancela y, si había cobro, se reembolsa.

## Estructura del repositorio

```
.
├── README.md
├── docs/
│   ├── PRD.md                 requisitos, alcance y decisiones de arquitectura
│   ├── eventos.md             contrato de los eventos entre servicios
│   ├── reporte-final.pdf      reporte final del proyecto
│   ├── manual-de-usuario.pdf  cómo levantar y usar el sistema y sus interfaces
│   ├── pruebas/               plan y resultados de todas las pruebas (PDF)
│   └── Bitacora-por-etapa/    bitácoras de pruebas de las etapas 1 a 4
└── Proyecto/
    ├── docker-compose.yml     Traefik, núcleo, repartidores (2 copias), notificaciones, RabbitMQ y PostgreSQL
    ├── Dockerfile
    ├── requirements.txt
    ├── db/                    esquema, datos de prueba, outbox, bases de notificaciones y repartidores, huella
    ├── app/                   el núcleo
    │   ├── main.py, config.py, db.py, errores.py
    │   ├── resiliencia.py     circuit breaker
    │   ├── clientes/          cliente HTTP de repartidores (tiempo límite, reintento y breaker)
    │   ├── modulos/           usuarios, restaurantes, pedidos y pagos
    │   └── panel/             panel web de demostración
    ├── interfaz/interfaz.py   aplicación de escritorio
    ├── repartidores/          servicio de repartidores (API y base propia, dos copias)
    └── notificaciones/        servicio de notificaciones (consumidor de RabbitMQ y API)
```

Cada módulo tiene tres capas: `router.py` (HTTP), `servicio.py` (reglas de negocio) y `repositorio.py`
(SQL). Un módulo solo habla con otro a través de su `servicio.py`.

## Configuración

Variables de entorno de la aplicación (se definen en `docker-compose.yml`):

| Variable | Valor en el compose | Descripción |
|---|---|---|
| `TIMEOUT_PAGO_SEG` | 30 | Segundos antes de cancelar un pedido sin pagar (valor normal: 600) |
| `TIMEOUT_ASIGNACION_SEG` | 60 | Segundos antes de cancelar y reembolsar un pedido pagado sin repartidor (valor normal: 1200) |
| `UMBRAL_RETRASO_SEG` | 30 | Segundos pagado y sin repartidor antes de avisar al cliente del retraso (valor normal: 600) |
| `REVISION_TIMEOUTS_SEG` | 5 | Cada cuántos segundos se revisan los pedidos vencidos y retrasados |
| `OUTBOX_ACTIVO` | 1 | Guarda los eventos de pedidos en `pedidos.outbox` |
| `PUBLICADOR_ACTIVO` | 1 | Activa el publicador que manda los eventos del outbox a RabbitMQ |
| `RABBITMQ_URL` | `amqp://sd:sd@rabbitmq:5672/` | Dirección de RabbitMQ |
| `REPARTIDORES_URL` | `http://repartidores:8000` | Dirección del servicio de repartidores para el núcleo |
| `REPARTIDORES_TIMEOUT_SEG` | 3 | Tiempo límite para recibir la respuesta de cada llamada del núcleo a repartidores |
| `REPARTIDORES_CONNECT_TIMEOUT_SEG` | 1 (valor por defecto) | Tiempo límite para resolver el nombre y conectar con repartidores |
| `BREAKER_FALLOS` | 3 | Fallos seguidos que abren el circuito hacia repartidores |
| `BREAKER_PAUSA_SEG` | 10 | Segundos que espera abierto antes de dejar pasar una llamada de prueba |
| `REPARTIDORES_REINTENTOS` | 1 | Reintentos por llamada a repartidores (solo cuando es seguro) |

Variable solo para pruebas, en el servicio de repartidores: `LATENCIA_MS` (0 por defecto) retrasa sus
respuestas para comprobar el tiempo límite, por ejemplo `LATENCIA_MS=5000 docker compose up -d repartidores`.

## Etapa 1: monolito modular

La primera etapa construye todo el sistema como una sola aplicación con una sola base de datos,
pero organizada en módulos (`usuarios`, `restaurantes`, `pedidos`, `pagos` y `repartidores`). La idea
es resolver primero la lógica de negocio y las fronteras entre módulos, para que después separar un
módulo en un servicio sea cambiar una llamada a función por una llamada de red.

**Consistencia.** Como la prioridad del sistema es no duplicar ni perder pedidos, las garantías no
dependen del código sino de la base de datos:

- La **idempotencia** se resuelve con una restricción `UNIQUE` sobre la clave de cada pedido. Si
  llegan varias peticiones iguales a la vez, la base deja pasar una y las demás reciben el mismo pedido.
- El **estado del pedido** avanza con `UPDATE` condicionales que incluyen el estado de origen. Así
  solo una petición consigue cada cambio, aunque lleguen varias al mismo tiempo (pagar, aceptar un
  repartidor, confirmar la entrega).
- Cobrar o reembolsar y cambiar el estado ocurren en **una sola transacción**, por eso `pagos` vive
  dentro del núcleo y no como servicio aparte.
- Los pedidos que no avanzan se **cancelan por tiempo**, con dos relojes configurables (pago y
  asignación de repartidor), y si ya había cobro se reembolsa en la misma transacción.
- Cada cambio de estado deja un **evento** en la tabla `outbox`, listo para publicarse a la cola de
  mensajes (lo que se hace en la etapa 2).

## Etapa 2: notificaciones como servicio aparte

`notificaciones` sale del núcleo y pasa a ser un servicio con su propio proceso, su propia base
(`notificaciones_db`) y su propia API. El núcleo ya no lo llama: cada cambio de estado deja un evento
en `pedidos.outbox`, un publicador lo manda a una cola persistente de RabbitMQ y el servicio de
notificaciones lo consume y guarda el aviso.

- **Los pedidos no esperan a los avisos.** El evento se guarda en la misma transacción que el cambio
  de estado; si notificaciones o RabbitMQ están caídos, el evento queda pendiente y se publica al volver.
- **Sin pérdidas ni duplicados.** La cola es durable, el consumidor confirma el mensaje solo después
  de guardarlo y `evento_id` es único, así que un evento repetido se ignora.
- **Mensajes inválidos** van a una cola de mensajes fallidos y no bloquean a los demás.
- **Eventos desordenados.** Cada evento lleva la versión del pedido, que permite saber cuál es el
  estado más reciente sin depender de la fecha.

## Etapa 3: repartidores como servicio y gateway

En la tercera etapa, `repartidores` sale del núcleo y pasa a ser un servicio con su propio proceso,
su propia base de datos (`repartidores_db`) y dos copias que se reparten la carga. Delante de todo hay
un gateway (Traefik) que es la única entrada al sistema.

- **Una sola entrada.** Los clientes hablan con el gateway; él decide si la petición va al núcleo,
  a repartidores o a notificaciones. Los puertos 8000 y 8001 de las etapas anteriores ya no existen.
- **Dos copias de repartidores.** El gateway reparte las peticiones entre ellas y deja de mandar
  tráfico a la que deje de responder (`/salud`). Cada respuesta lleva el encabezado `X-Instancia`
  con la copia que contestó.
- **El núcleo no se cae con repartidores.** Se pueden crear y pagar pedidos aunque repartidores esté
  caído. La consulta del núcleo es directa (por el DNS de Docker, sin pasar por el gateway) y tiene un
  tiempo límite; si no responde, el núcleo contesta 503 y no cambia nada.
- **Quién decide.** Repartidores informa (quién es, su zona y si está disponible); pedidos decide
  quién gana el pedido con un `UPDATE` condicional en su propia base.
- **El cliente se entera del retraso.** Si un pedido pagado tarda demasiado en tener repartidor,
  recibe el aviso `pedido.retrasado` (una sola vez); si vence el tiempo, el pedido se cancela y se reembolsa.

Con Docker 29 o superior, Traefik debe ser la versión 3.6.1 o más nueva; el compose fija `traefik:v3.6`.

## Etapa 4: resiliencia

La última etapa hace que el sistema aguante fallas sin perder información.

- **Circuit breaker.** Si el servicio de repartidores falla varias veces seguidas, el núcleo deja de
  llamarlo y responde 503 al instante en lugar de esperar su tiempo límite en cada intento. Pasado un
  rato deja pasar una llamada de prueba y, si sale bien, vuelve a la normalidad.
- **Reintentos seguros.** Un solo reintento, solo cuando la petición no llegó a enviarse o el
  servicio respondió 502, 503 o 504; nunca después de un tiempo de espera agotado ni cuando el nombre
  del servicio no se resuelve.
- **La resolución del nombre también tiene tiempo límite.** En Docker Desktop para Windows, resolver el
  nombre de un servicio detenido tardaba unos 4 s (8 s con el reintento); ahora tiene el mismo límite de
  1 s que la conexión.
- **Deduplicación completa.** Si una `Idempotency-Key` se reutiliza con un pedido distinto, se
  rechaza con 422 en lugar de devolver el pedido original sin avisar.
- **Estado operativo.** `GET /estado` muestra el estado del circuito y cuántos eventos esperan
  publicarse.
- **Recuperación automática.** Los servicios se reconectan solos si PostgreSQL se reinicia.

Todo se comprobó contra Docker real; las salidas están en la bitácora 4.

## Plan de ramas

El sistema empieza como un monolito y se parte por etapas, cada una en su rama.

| Rama | Qué se comprueba | Estado |
|---|---|---|
| `main` | README y PRD | Listo |
| `01-monolito` | Una aplicación y una base. Flujo completo de pedidos con idempotencia | Listo |
| `02-separacion` | `notificaciones` como proceso aparte, con cola persistente. Los pedidos siguen funcionando con ese proceso apagado | Listo |
| `03-separacion` | `repartidores` como servicio propio con gateway y dos copias; gana el primer repartidor que acepta | Listo |
| `04-resiliencia` | Reintentos, deduplicación, timeout con reembolso, circuit breaker y pruebas de caídas | Listo |

## Estado actual

- **Etapa 0:** terminada. El alcance del PRD se redujo y se acordó con el profesor: un núcleo con
  `pedidos` y `pagos`, y dos servicios que se separan, `notificaciones` y `repartidores`.
- **Etapa 1 (`01-monolito`):** terminada. El monolito modular cubre el flujo completo: crear un
  pedido de forma idempotente, pagarlo, asignarlo a un repartidor, confirmar la entrega y cancelar
  con reembolso los pedidos vencidos. Cada cambio de estado se guarda como evento en `pedidos.outbox`.
- **Etapa 2 (`02-separacion`):** terminada. `notificaciones` corre como servicio aparte con base
  propia y recibe los eventos por RabbitMQ.
- **Etapa 3 (`03-separacion`):** terminada. `repartidores` corre como servicio aparte con base
  propia y dos copias detrás de un gateway. El núcleo lo consulta por HTTP con tiempo límite.
- **Etapa 4 (`04-resiliencia`):** terminada. El núcleo tiene circuit breaker y reintentos seguros hacia
  repartidores, detecta claves de idempotencia reutilizadas y se recupera solo si PostgreSQL se reinicia.
- **El proyecto está completo:** las cuatro etapas están terminadas, con su interfaz y su documentación.

## Documentación

- [Reporte final](docs/reporte-final.pdf): problema, diagramas, decisiones, manejo de fallas, cómo
  levantarlo, qué falta y quién hizo qué.
- [PRD](docs/PRD.md): problema, alcance, "dónde vive cada pieza" y decisiones de arquitectura.
- [Contrato de eventos](docs/eventos.md): formato de los eventos entre `pedidos` y `notificaciones`.
- [Bitácoras por etapa](docs/Bitacora-por-etapa/): pruebas con evidencia de las etapas 1 a 4, con un README por etapa.
- [Pruebas del proyecto](docs/pruebas/pruebas-del-proyecto.pdf): plan y resultados de todas las pruebas.
- [Manual de usuario](docs/manual-de-usuario.pdf): cómo levantar el sistema y usar la aplicación de escritorio, el panel web y la API.