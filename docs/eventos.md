# Contrato de eventos

Los eventos los publica `pedidos` desde la tabla `outbox` y los consume `notificaciones`.

## Formato

Todos los eventos tienen los mismos campos:

```json
{
  "eventoId": "uuid, distinto en cada evento",
  "tipo": "pedido.pagado",
  "versionPedido": 3,
  "fecha": "2026-10-31T18:20:00Z",
  "pedidoId": "uuid",
  "usuarioId": "uuid",
  "datos": {}
}
```

- `eventoId`: `notificaciones` guarda los que ya procesó y descarta los repetidos.
- `versionPedido`: número que sube cada vez que cambia el estado del pedido. Los mensajes pueden llegar desordenados, y con este número `notificaciones` sabe cuál es el más reciente.
- `fecha`: momento en que ocurrió el evento, en UTC. Sirve para mostrar y depurar, no para ordenar.

## Tipos de evento

| `tipo` | Cuándo se emite | `datos` |
|---|---|---|
| `pedido.pagado` | El pago simulado salió bien | `{ "total": 180.50 }` |
| `pedido.retrasado` | Todavía no hay repartidor, o `repartidores` está caído | `{ "motivo": "buscando_repartidor" }` |
| `pedido.asignado` | Un repartidor aceptó el pedido | `{ "repartidorId": "uuid" }` |
| `pedido.entregado` | Se confirmó el código de entrega | `{}` |
| `pedido.cancelado` | Venció un reloj del pedido | `{ "motivo": "sin_pago" o "sin_repartidor", "reembolsado": true o false }` |

`pedido.retrasado` se emite solo una vez por pedido.

## RabbitMQ

| Elemento | Nombre |
|---|---|
| Exchange (topic, durable) | `pedidos.eventos` |
| Routing key | el valor de `tipo` |
| Cola principal (durable) | `notificaciones.pedidos`, enlazada con `pedido.*` |
| Exchange de mensajes fallidos (direct, durable) | `pedidos.eventos.dlx` |
| Cola de mensajes fallidos (durable) | `notificaciones.pedidos.dlq`, enlazada al exchange de fallidos con la clave `notificaciones.pedidos` |
| Mensajes | persistentes |

`notificaciones` hace el ack después de guardar el aviso en su base. Si el mensaje es inválido, lo rechaza sin reencolar y va a la cola de mensajes fallidos.

La cola principal se declara con `x-dead-letter-exchange` apuntando al exchange de fallidos, así
que un mensaje rechazado sin reencolar llega solo a la cola de fallidos.

El exchange y las colas los declaran tanto el publicador (núcleo) como el consumidor
(`notificaciones`), con exactamente los mismos argumentos. Así los mensajes esperan en la cola
aunque `notificaciones` no haya arrancado nunca. Los dos archivos son
`Proyecto/app/modulos/pedidos/topologia.py` y `Proyecto/notificaciones/app/topologia.py`, y deben
mantenerse idénticos.

El publicador entrega cada evento **al menos una vez** (solo lo marca como publicado cuando RabbitMQ
lo confirma); el consumidor ignora los duplicados por `eventoId`.

## Tabla `outbox` (en la base del núcleo, `didistribuidores`)

| Columna | Tipo | Nota |
|---|---|---|
| `id` | uuid, llave primaria | es el `eventoId` |
| `tipo` | text | |
| `payload` | jsonb | el evento completo |
| `creado_en` | timestamptz | |
| `publicado_en` | timestamptz, puede ser nulo | nulo significa pendiente |

La fila se inserta en la misma transacción que cambia el estado del pedido. El publicador busca las filas con `publicado_en` nulo, las manda y las marca. Si falla antes de marcarlas, se vuelven a mandar, y por eso `notificaciones` tiene que tolerar duplicados.