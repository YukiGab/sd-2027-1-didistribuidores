-- Etapa 3: marca para avisar UNA sola vez que un pedido pagado se está retrasando.
-- Va en un archivo aparte (y no dentro de 01-esquema.sql) para no pisar el trabajo de otras ramas.
ALTER TABLE pedidos.pedidos ADD COLUMN retraso_avisado boolean NOT NULL DEFAULT false;
