-- Tabla outbox: los eventos se guardan aquí en la misma transacción que cambia el estado
-- del pedido, y un publicador los manda después a RabbitMQ (etapa 2).
-- Formato de los eventos: docs/eventos.md

CREATE TABLE pedidos.outbox (
    id            uuid PRIMARY KEY,                 -- es el eventoId
    tipo          text NOT NULL,                    -- por ejemplo 'pedido.pagado'
    payload       jsonb NOT NULL,                   -- el evento completo
    creado_en     timestamptz NOT NULL DEFAULT now(),
    publicado_en  timestamptz                       -- nulo = pendiente de publicar
);

-- El publicador solo lee los pendientes
CREATE INDEX outbox_pendientes_idx ON pedidos.outbox (creado_en) WHERE publicado_en IS NULL;
