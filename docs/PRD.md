# PRD: DiDistribuidores, sistema de pedidos y entrega de comida

Equipo: DiDistribuidores (@YukiGab y @ErickI07). Versión 2, 30 de octubre de 2026.

Somos dos en el equipo, así que de acuerdo con el profesor reducimos el alcance: un núcleo (usuarios, restaurantes, pedidos y pagos simulados) y dos servicios que se separan de él, `notificaciones` y `repartidores`. Todo corre en local con `docker compose up --build`.

## 1. Problema y usuarios

Cuando alguien pide comida a domicilio en hora pico, el sistema se pone lento, se pierden pedidos o se cobra dos veces. Muchas veces pasa porque la app reintenta una petición y el servidor la procesa de nuevo.

El usuario principal es el cliente: quiere pedir, pagar una sola vez y recibir su comida. Los secundarios son el restaurante, que la prepara, y el repartidor, que la entrega. Para nosotros importa más que el pedido y el cobro sean correctos que la velocidad.

## 2. Por qué es distribuido

- Un aviso al cliente o la búsqueda de un repartidor no deben impedir que un pedido se confirme. Por eso `notificaciones` y `repartidores` corren en procesos aparte.
- `repartidores` no guarda estado en memoria, así que se pueden levantar varias copias detrás del gateway para aguantar la hora pico.
- Cada servicio tiene su propia base lógica. Al comunicarse por la red hay que resolver timeouts, reintentos y duplicados.

La frontera que más importa es la de `pedidos` con `repartidores`: `pedidos` tiene que seguir funcionando aunque `repartidores` esté caído.

## 3. Alcance

Las cuatro funciones del sistema:

1. Usuarios y menús: registrar un usuario sencillo, ver restaurantes y menús (datos semilla) y crear pedidos.
2. Pagos simulados: cobrar un pedido sin cobrarlo dos veces.
3. Repartidores: asignar uno de la misma zona (gana el primero que acepta) y confirmar la entrega con un código.
4. Notificaciones: avisar al cliente de los cambios de estado de su pedido.

Lo que no hacemos:

- Pasarela de pagos real. El pago se simula.
- App móvil o interfaz. Solo API detrás de un gateway.
- GPS ni seguimiento en tiempo real. El cliente consulta el estado del pedido. La zona es un número entero.
- Disputas de entrega. Solo el repartidor confirma con el código.
- Módulo de Atención, historial de 6 meses, bases NoSQL y verificación previa con servidores redundantes.
- Autenticación real. El usuario se identifica con un id, sin contraseña ni token.
- Aceptación o rechazo del pedido por parte del restaurante. Se asume que prepara todo pedido pagado.
- Definir quién paga la comida ya preparada si el pedido se cancela.

## 4. Qué priorizamos y qué sacrificamos

Priorizamos la consistencia en pedidos y pagos. Nunca se cobra un pedido que no se confirmó y nunca se pierde uno ya confirmado.

A cambio aceptamos que:

- la asignación de repartidor sea básica, que tarde o que no se logre;
- el estado del pedido se vea con unos segundos de retraso;
- en hora pico el sistema retrase o rechace pedidos;
- los avisos lleguen tarde si `notificaciones` está caído. Preferimos que lleguen tarde a que no lleguen.

## 5. Historias de usuario

### 5.1 Realizar un pedido

Como cliente con hambre que ya pagó, quiero que mi pedido llegue sin que me cobren dos veces ni lo pierdan, para comer tranquilo.

- CA1 (idempotencia): si mi app repite la petición con la misma `Idempotency-Key`, el sistema devuelve el mismo pedido y no crea otro ni cobra de nuevo. La clave es `UNIQUE` en la base de `pedidos`, así que dos peticiones simultáneas con la misma clave producen un solo pedido.
- CA2 (repartidores caído): si `repartidores` está caído o nadie acepta, el sistema me avisa que el pedido sigue en búsqueda. No se queda en el limbo: al vencer el timeout se cancela y se reembolsa.
- CA3 (entrega única): cuando el repartidor ingresa el código de entrega, el pedido pasa a `ENTREGADO` una sola vez aunque lo envíe dos veces.

### 5.2 Recibir avisos aunque `notificaciones` esté caído

Como cliente, quiero recibir los avisos de mi pedido aunque el servicio de avisos haya estado apagado, para no perder información.

- CA1: con `notificaciones` apagado, un pedido se crea, se paga y cambia de estado normalmente.
- CA2: al volver a encender `notificaciones`, llegan los avisos pendientes, cada uno una sola vez.
- CA3: un mensaje inválido va a una cola de mensajes fallidos y no bloquea a los demás.

### 5.3 Aceptar un pedido (repartidor)

Como repartidor, quiero ver los pedidos de mi zona y aceptar uno, para entregarlo.

- CA1: solo veo pedidos `PAGADO` de mi zona.
- CA2: si dos repartidores aceptan al mismo tiempo, solo uno se queda con el pedido y el otro recibe un rechazo claro.

### 5.4 Pedido sin repartidor

Como cliente, quiero que mi pedido se cancele y se reembolse si nadie lo entrega a tiempo, para no quedarme sin comida y sin dinero.

- CA1: un pedido `PAGADO` sin repartidor pasa a `CANCELADO` al cumplirse `TIMEOUT_ASIGNACION_SEG` y su pago queda `REEMBOLSADO`.
- CA2: el reembolso se hace una sola vez, aunque el proceso que cancela corra dos veces.

Deseables: menú en menos de 3 segundos en hora pico, avisos en menos de 10 segundos y un mensaje claro cuando el sistema esté saturado.

## 6. Del monolito a los servicios

Primero se construye un monolito modular con los módulos `usuarios`, `restaurantes` (con menús), `pedidos`, `pagos`, `repartidores` y `notificaciones`. Un módulo no consulta las tablas de otro; se hablan por funciones. Después se separan `notificaciones` y `repartidores`.

| Servicio | Contiene | Es dueño de |
|---|---|---|
| `pedidos` (núcleo) | usuarios, restaurantes, pedidos, pagos | estado del pedido, clave de idempotencia, pagos, tabla `outbox` |
| `notificaciones` | bandeja de avisos | los avisos y los eventos ya procesados |
| `repartidores` | repartidores y sus zonas | disponibilidad y zona de cada repartidor |

`pedidos` es el único dueño del estado del pedido. La regla de que gana el primer repartidor que acepta vive ahí, como una actualización condicional: `UPDATE ... WHERE estado = 'PAGADO' AND repartidor_id IS NULL`.

`pagos` se queda dentro del núcleo. Así el cobro, el cambio de estado y el reembolso se hacen en la misma transacción local, y no puede haber cobro sin pedido ni pedido sin cobro.

Estados del pedido: `PENDIENTE_PAGO → PAGADO → ASIGNADO → ENTREGADO`. Además hay dos cancelaciones por vencimiento, cada una con su reloj:

- `PENDIENTE_PAGO → CANCELADO` si no se paga en `TIMEOUT_PAGO_SEG`. No hubo cobro, así que no hay reembolso.
- `PAGADO → CANCELADO` si no hay repartidor en `TIMEOUT_ASIGNACION_SEG`. El pago queda `REEMBOLSADO`.

Ramas:

| Rama | Qué se comprueba |
|---|---|
| `01-monolito` | Una aplicación y una base. Flujo completo: menú, pedido idempotente, pago simulado, asignación y entrega con código |
| `02-separacion` | `notificaciones` como proceso aparte. Los pedidos funcionan con él apagado y los avisos pendientes llegan al volver |
| `03-separacion` | `repartidores` como servicio propio, asignación por zona y puerta única con gateway |
| `04-resiliencia` | Timeouts, circuit breaker, deduplicación y pruebas de caídas |

Manejo de fallas entre servicios:

- Notificaciones: `pedidos` guarda el cambio de estado y un evento en la tabla `outbox` en la misma transacción. Un publicador manda los eventos pendientes a RabbitMQ. Si `notificaciones` o RabbitMQ están caídos, el evento queda pendiente y se reintenta.
- Repartidores: si falla o nadie acepta, el pedido sigue `PAGADO` y se avisa al cliente. Al cumplirse el timeout se cancela y se reembolsa en una transacción local.

## 7. Dónde vive cada pieza

| Pieza | Dónde vive | Por qué | Si falla |
|---|---|---|---|
| API gateway | Traefik, el único servicio con puerto público. Manda `/api/pedidos`, `/api/restaurantes` y `/api/usuarios` al núcleo, `/api/repartidores` a `repartidores` y `/api/notificaciones` a `notificaciones` | Una sola entrada, sin exponer cada servicio | No entran peticiones nuevas, pero los datos guardados no se pierden. Es un punto único de falla que aceptamos para la demo |
| Directorio | DNS de Docker Compose: los servicios se llaman por nombre (`repartidores`, `rabbitmq`, `db`) | No hace falta montar un registro aparte como Eureka | Si falla el DNS de Docker, los servicios no se encuentran entre sí y hay que reiniciar el entorno |
| Balanceo | Traefik reparte entre copias de `repartidores` (`docker compose up --scale repartidores=2`). Las copias no guardan estado | Permite escalar y que una copia pueda morir | Si muere una copia, las demás atienden. Si mueren todas, entra el circuit breaker |
| Datos | Una instancia de PostgreSQL con una base lógica por servicio: `pedidos_db`, `notificaciones_db` y `repartidores_db`. Sin réplicas ni particiones | `pedidos` y `pagos` necesitan transacciones y restricciones `UNIQUE` | Si PostgreSQL cae, no se confirman escrituras. Es un punto único de falla que declaramos. Si el sistema creciera, se particionaría por zona |
| Operaciones entre servicios | `outbox` más RabbitMQ para los avisos, HTTP con timeout de `pedidos` a `repartidores`, e idempotencia con `Idempotency-Key` y con `eventoId` | Evita transacciones distribuidas y mantiene los servicios desacoplados | Un evento fallido queda pendiente y se reintenta. Uno duplicado se ignora |
| Manejo de fallas | Timeout HTTP de pocos segundos, circuit breaker de `pedidos` hacia `repartidores`, los dos relojes de pedido y una cola de mensajes fallidos en `notificaciones` | Cada límite evita esperas infinitas y reintentos sin control | Con el circuito abierto, `pedidos` responde rápido sin llamar a `repartidores`. El pedido queda `PAGADO` y se cancela al vencer su reloj |

## 8. Stack y demo

Python 3.11 con FastAPI, PostgreSQL 17, RabbitMQ 4, Traefik y Docker Compose. El acceso a la base es con `psycopg`.

La demo debe mostrar: hacer un pedido y repetir la petición para ver la idempotencia; apagar `notificaciones`, hacer pedidos y ver que los avisos llegan al volver; y apagar `repartidores` para ver que el pedido se cancela y se reembolsa. Para la demo se usa `TIMEOUT_ASIGNACION_SEG=60` (normal: 20 minutos) y `TIMEOUT_PAGO_SEG=30` (normal: 10 minutos).

## 9. Decisiones de arquitectura

| Decisión | Alternativa que descartamos | Por qué |
|---|---|---|
| Empezar con un monolito modular y separar por ramas | Crear todos los servicios desde el inicio | Primero se hace funcionar el negocio y después se ve qué cambia al cruzar la red |
| `pagos` dentro del núcleo | Un servicio `pagos` con su base | Separarlo obligaría a coordinar dos servicios para no cobrar sin pedido, y con dos personas no alcanza |
| Idempotencia con `UNIQUE` en la base | Un diccionario en memoria que revisa si ya existe | El diccionario deja un hueco entre revisar y guardar. La base lo resuelve de forma atómica |
| `outbox` y RabbitMQ para los avisos | Llamar a `notificaciones` por HTTP dentro de la petición | Que fallen los avisos no debe bloquear ni deshacer un pedido |
| Reembolso en la misma transacción que la cancelación | Reembolso por una cola aparte | Como `pagos` está en el núcleo, una transacción local es más simple y segura |
| Separar primero `notificaciones` y luego `repartidores` | Separar `pagos` primero | `notificaciones` es el caso más sencillo de mensajería y `repartidores` depende de que el pedido ya exista |
| Dos relojes de pedido configurables: pago (10 min) y asignación (20 min) | Un solo reloj, o esperar sin límite | Cada uno protege una regla distinta y se pueden acortar para la demo |
| Circuit breaker de `pedidos` hacia `repartidores` | Reintentar sin límite | Evita llenar `pedidos` de llamadas que van a fallar |
| Una instancia de PostgreSQL con una base lógica por servicio | Una instancia por servicio, o NoSQL | Cada servicio es dueño de sus datos sin multiplicar contenedores. El costo es un punto único de falla |
| Traefik como gateway y DNS de Compose como directorio | Spring Cloud Gateway y Eureka (lo del lab de Java) | Usamos Python, y Docker ya resuelve los nombres |

## 10. Decisiones tomadas y pendientes

1. `pagos` se queda dentro del núcleo.
2. Hay dos relojes de pedido configurables por variable de entorno, además del timeout HTTP entre servicios.
3. Los pedidos viejos no se archivan ni se borran.
4. La zona es un entero de 1 a 5.
5. Si vence `TIMEOUT_ASIGNACION_SEG` sin repartidor, el pedido se cancela y se reembolsa solo.
6. Aceptamos los recortes de alcance de la sección 3.
7. Acceso a la base con `psycopg` directo.
8. El profesor confirmó el alcance: núcleo más `notificaciones` y `repartidores`.
9. El restaurante no acepta pedidos y el módulo de Atención se elimina.