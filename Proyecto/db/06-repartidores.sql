-- Base propia del servicio de repartidores (etapa 3).
-- Es una base lógica distinta dentro de la misma instancia de Postgres: el núcleo no la lee y
-- repartidores no lee la del núcleo. Se ejecuta solo con el volumen vacío (docker compose down -v).

CREATE DATABASE repartidores_db;

\connect repartidores_db

CREATE TABLE repartidores (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      text NOT NULL,
    zona        smallint NOT NULL CHECK (zona BETWEEN 1 AND 5),
    disponible  boolean NOT NULL DEFAULT true,
    creado_en   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX repartidores_zona_idx ON repartidores (zona) WHERE disponible;

-- Datos de prueba (antes estaban en db/02-semilla.sql)
INSERT INTO repartidores (nombre, zona) VALUES
    ('Ana Ruiz',    1),
    ('Luis Pérez',  1),
    ('Marta Soto',  2),
    ('Diego Vega',  2),
    ('Sofía Mena',  3);
