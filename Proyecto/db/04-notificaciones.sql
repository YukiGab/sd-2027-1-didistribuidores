-- Base propia del servicio de notificaciones (etapa 2).
-- Es una base lógica distinta dentro de la misma instancia de Postgres: el núcleo no la lee
-- y notificaciones no lee la del núcleo. Se ejecuta solo con el volumen vacío (down -v).

CREATE DATABASE notificaciones_db;

\connect notificaciones_db

CREATE TABLE avisos (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- UNIQUE en evento_id: un evento produce un solo aviso, aunque RabbitMQ lo entregue dos veces
    evento_id      uuid NOT NULL UNIQUE,
    pedido_id      uuid NOT NULL,
    usuario_id     uuid NOT NULL,
    tipo           text NOT NULL,
    version_pedido integer NOT NULL CHECK (version_pedido >= 1),
    mensaje        text NOT NULL,
    fecha_evento   timestamptz NOT NULL,                   -- cuándo ocurrió (viene en el evento)
    recibido_en    timestamptz NOT NULL DEFAULT now()      -- cuándo llegó a notificaciones
);

CREATE INDEX avisos_usuario_idx ON avisos (usuario_id, fecha_evento DESC);
CREATE INDEX avisos_pedido_idx  ON avisos (pedido_id, version_pedido);
