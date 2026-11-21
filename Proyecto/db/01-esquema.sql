-- Esquema del núcleo (etapa 01-monolito).
-- Un esquema de Postgres por módulo del núcleo. Ninguna tabla apunta con llave foránea a una tabla
-- de otro esquema: las referencias entre módulos son solo ids que se validan en el código.
-- Así, cuando se separe un servicio, su esquema se mueve a otra base sin romper nada.

CREATE SCHEMA IF NOT EXISTS usuarios;
CREATE SCHEMA IF NOT EXISTS restaurantes;
CREATE SCHEMA IF NOT EXISTS pedidos;
CREATE SCHEMA IF NOT EXISTS pagos;

-- Usuarios (sin contraseña: se identifican por id)
CREATE TABLE usuarios.usuarios (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre     text NOT NULL,
    zona       smallint NOT NULL CHECK (zona BETWEEN 1 AND 5),
    creado_en  timestamptz NOT NULL DEFAULT now()
);

-- Restaurantes y menús
CREATE TABLE restaurantes.restaurantes (
    id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre  text NOT NULL,
    zona    smallint NOT NULL CHECK (zona BETWEEN 1 AND 5)
);

CREATE TABLE restaurantes.platillos (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurante_id  uuid NOT NULL REFERENCES restaurantes.restaurantes (id),
    nombre          text NOT NULL,
    precio          numeric(10,2) NOT NULL CHECK (precio > 0),
    disponible      boolean NOT NULL DEFAULT true
);

-- Pedidos: este módulo es el único dueño del estado del pedido
CREATE TABLE pedidos.pedidos (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id          uuid NOT NULL,
    restaurante_id      uuid NOT NULL,
    zona                smallint NOT NULL CHECK (zona BETWEEN 1 AND 5),
    estado              text NOT NULL DEFAULT 'PENDIENTE_PAGO'
                        CHECK (estado IN ('PENDIENTE_PAGO', 'PAGADO', 'ASIGNADO',
                                          'ENTREGADO', 'CANCELADO')),
    motivo_cancelacion  text CHECK (motivo_cancelacion IN ('sin_pago', 'sin_repartidor')),
    total               numeric(10,2) NOT NULL CHECK (total > 0),
    clave_idempotencia  text NOT NULL,
    repartidor_id       uuid,
    codigo_entrega      text NOT NULL,
    version             integer NOT NULL DEFAULT 1,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_en      timestamptz NOT NULL DEFAULT now(),
    -- Lo que evita el pedido doble
    UNIQUE (usuario_id, clave_idempotencia)
);

-- Para el job de timeouts y para listar los pedidos PAGADO de una zona
CREATE INDEX pedidos_estado_creado_idx ON pedidos.pedidos (estado, actualizado_en);
CREATE INDEX pedidos_pagados_zona_idx  ON pedidos.pedidos (zona) WHERE estado = 'PAGADO';

-- Se guarda el precio del momento: si el menú cambia después, el pedido no cambia
CREATE TABLE pedidos.pedido_platillos (
    pedido_id        uuid NOT NULL REFERENCES pedidos.pedidos (id),
    platillo_id      uuid NOT NULL,
    cantidad         integer NOT NULL CHECK (cantidad > 0),
    precio_unitario  numeric(10,2) NOT NULL CHECK (precio_unitario > 0),
    PRIMARY KEY (pedido_id, platillo_id)
);

-- Pagos simulados. UNIQUE en pedido_id: un pedido solo puede tener un cobro.
CREATE TABLE pagos.pagos (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id        uuid NOT NULL UNIQUE,
    monto            numeric(10,2) NOT NULL CHECK (monto > 0),
    estado           text NOT NULL DEFAULT 'COBRADO' CHECK (estado IN ('COBRADO', 'REEMBOLSADO')),
    creado_en        timestamptz NOT NULL DEFAULT now(),
    reembolsado_en   timestamptz
);

-- Los repartidores ya no viven aquí: desde la etapa 3 son un servicio con su propia base (db/06-repartidores.sql).
-- pedidos.repartidor_id sigue siendo solo un uuid, sin llave foránea, porque la tabla está en otra base.
-- La tabla pedidos.outbox está en db/03-outbox.sql y la base de notificaciones en db/04-notificaciones.sql.
