-- Etapa 4: huella (SHA-256) de la petición que creó el pedido.
-- Sirve para detectar que una Idempotency-Key se reutilizó con un pedido distinto.
-- Puede ser nula: los pedidos anteriores a esta columna no tienen huella y se aceptan sin comparar.
ALTER TABLE pedidos.pedidos ADD COLUMN huella_peticion text;
