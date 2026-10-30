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
| Cola de mensajes fallidos | `notificaciones.pedidos.dlq` |
| Mensajes | persistentes |

`notificaciones` hace el ack después de guardar el aviso en su base. Si el mensaje es inválido, va a la cola de mensajes fallidos.

## Tabla `outbox` (en `pedidos_db`)

| Columna | Tipo | Nota |
|---|---|---|
| `id` | uuid, llave primaria | es el `eventoId` |
| `tipo` | text | |
| `payload` | jsonb | el evento completo |
| `creado_en` | timestamptz | |
| `publicado_en` | timestamptz, puede ser nulo | nulo significa pendiente |

La fila se inserta en la misma transacción que cambia el estado del pedido. El publicador busca las filas con `publicado_en` nulo, las manda y las marca. Si falla antes de marcarlas, se vuelven a mandar, y por eso `notificaciones` tiene que tolerar duplicados.