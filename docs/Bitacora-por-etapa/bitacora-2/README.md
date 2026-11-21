# Etapa 2: notificaciones como servicio aparte

**Rama:** `02-separacion` · **Bitácora:** `bitacora-etapa-02.pdf` (11 figuras) · [Volver al índice de bitácoras](../README.md)

`notificaciones` sale del núcleo y pasa a ser un servicio con su propio proceso, su propia base (`notificaciones_db`) y su propia API. El núcleo ya no lo llama: cada cambio de estado deja un evento en `pedidos.outbox`, un publicador lo manda a una cola persistente de RabbitMQ y el servicio de notificaciones lo consume y guarda el aviso.

El camino de un aviso:

1. El pedido cambia de estado y, en la misma transacción, se guarda un evento en el outbox. Desde ese momento el pedido ya está confirmado: nadie espera a que se envíe ningún aviso.
2. Un publicador (un hilo dentro del núcleo) lee los eventos pendientes y los publica en RabbitMQ. Solo los marca como publicados cuando RabbitMQ confirma que los recibió.
3. Los mensajes esperan en una cola durable, marcados como persistentes.
4. El consumidor del servicio de notificaciones valida cada mensaje, guarda el aviso y hasta después de guardarlo confirma el mensaje (`ack`).

* **Los pedidos no esperan a los avisos.** El evento se guarda en la misma transacción que el cambio de estado; si notificaciones o RabbitMQ están caídos, el evento queda pendiente y se publica al volver.
* **Sin pérdidas ni duplicados.** La cola es durable, el consumidor confirma el mensaje solo después de guardarlo y `evento_id` es único, así que un evento repetido se ignora.
* **Mensajes inválidos** van a una cola de mensajes fallidos (`notificaciones.pedidos.dlq`) y no bloquean a los demás.
* **Eventos desordenados.** Cada evento lleva la versión del pedido, que permite saber cuál es el estado más reciente sin depender de la fecha.
* **RabbitMQ con nombre fijo.** RabbitMQ guarda sus datos según el nombre del nodo; sin un `hostname` fijo las colas persistentes parecerían desaparecer al recrear el contenedor.

## Qué cambia respecto a la etapa 1

| Aspecto | Etapa 1 | Etapa 2 |
|---|---|---|
| Notificaciones | Evento guardado en el outbox, sin publicar | Servicio aparte que consume los eventos por RabbitMQ |
| Contenedores | 2 (aplicación y base) | 4 (más RabbitMQ y notificaciones) |
| Direcciones | `:8000` | `:8000` (núcleo) y `:8001` (notificaciones); consola de RabbitMQ en `:15672` |

## Qué se probó

| Prueba | Resultado observado | Figuras |
|---|---|---|
| Levantar los cuatro servicios y consola de RabbitMQ | Base y RabbitMQ `healthy`; consumidor conectado; las dos colas son durables | 1 y 2 |
| 1. Flujo normal | Tres avisos (versiones 2, 3 y 4) y tres eventos publicados | 3 |
| 2. Notificaciones apagado | El pedido llega a `ENTREGADO`; 3 mensajes esperan en la cola; al volver llegan los 3, una vez cada uno | 4 y 5 |
| 3. Evento duplicado | El mismo evento publicado tres veces deja un aviso y dos duplicados ignorados | 6 |
| 4. Mensaje inválido | Un mensaje en la cola de fallidos; el evento válido posterior se guarda | 7 |
| 5. Eventos desordenados | Los avisos salen ordenados por versión y `/ultimo` devuelve la versión 4 | 8 |
| 6. RabbitMQ caído | El pedido avanza; 3 eventos pendientes en el outbox; al volver, 0 pendientes | 9 y 10 |
| 7. La cola sobrevive a un reinicio de RabbitMQ | Los 3 mensajes siguen antes y después; los avisos llegan completos | 11 |

Las pruebas 2 y 6 cubren los criterios de la historia 5.2 del PRD: con notificaciones apagado un pedido se crea, se paga y avanza con normalidad, y los avisos pendientes llegan una sola vez al volver.

## Cómo repetir las pruebas

Las pruebas se corrieron a mano en PowerShell. Cada una trae su comando en la bitácora, y se apoyan en cuatro funciones auxiliares que ella describe (`Ciclo-Completo`, `Avisos`, `Cola` y `Psql`).

```bash
cd Proyecto
docker compose down -v        # el script que crea notificaciones_db solo corre con el volumen vacío
docker compose up --build -d
curl http://localhost:8000/salud
curl http://localhost:8001/salud
```

## Quién hizo qué

| Integrante | Aportes |
|---|---|
| Yukioayax Canek Gabriel Hernández ([@YukiGab](https://github.com/YukiGab)) | Servicio de notificaciones (base propia, consumidor, API y cola de mensajes fallidos), publicador del outbox hacia RabbitMQ, RabbitMQ en el Compose y las siete pruebas. |
| Erick Isaac Echeverria Goicochea ([@ErickI07](https://github.com/ErickI07)) | Revisión del trabajo de notificaciones. |
| Los dos | Decisiones de alcance y diseño del PRD, contrato de eventos, revisión cruzada, evidencias y bitácora. |
