-- Datos de prueba para la Etapa 1.
-- Se ejecuta solo la primera vez que arranca Postgres con la base vacía
-- (para repetirlo: docker compose down -v).

INSERT INTO restaurantes.restaurantes (nombre, zona) VALUES
    ('Tacos El Güero',     1),
    ('Pizzería Don Luigi', 2),
    ('Fonda La Abuela',    3);

INSERT INTO restaurantes.platillos (restaurante_id, nombre, precio)
SELECT r.id, p.nombre, p.precio
FROM (VALUES
    ('Tacos El Güero',     'Taco al pastor',    25.00),
    ('Tacos El Güero',     'Gringa',            60.00),
    ('Tacos El Güero',     'Agua de horchata',  30.00),
    ('Pizzería Don Luigi', 'Pizza margarita',  140.00),
    ('Pizzería Don Luigi', 'Pizza pepperoni',  160.00),
    ('Pizzería Don Luigi', 'Refresco',          25.00),
    ('Fonda La Abuela',    'Comida corrida',    90.00),
    ('Fonda La Abuela',    'Caldo de pollo',    75.00),
    ('Fonda La Abuela',    'Agua fresca',       25.00)
) AS p(restaurante, nombre, precio)
JOIN restaurantes.restaurantes r ON r.nombre = p.restaurante;

-- Los repartidores de prueba ahora se cargan en db/06-repartidores.sql (base repartidores_db).
