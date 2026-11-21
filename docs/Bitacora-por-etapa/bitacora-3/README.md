# Etapa 3: repartidores como servicio y gateway

**Rama:** `03-separacion` · **Bitácora:** `bitacora-etapa-03.pdf` (16 figuras) · [Volver al índice de bitácoras](../README.md)

En la tercera etapa, `repartidores` sale del núcleo y pasa a ser un servicio con su propio proceso, su propia base de datos (`repartidores_db`) y dos copias que se reparten la carga. Delante de todo hay un gateway (Traefik) que es la única entrada al sistema.

* **Una sola entrada.** Los clientes hablan con el gateway, en `http://localhost:8080`; él decide si la petición va al núcleo, a repartidores o a notificaciones. Los puertos 8000 y 8001 de las etapas anteriores ya no existen. Traefik no tiene una lista de servicios escrita: lee las etiquetas de los contenedores de Docker.
* **Dos copias de repartidores.** El gateway reparte las peticiones entre ellas y deja de mandar tráfico a la que deje de responder (`/salud`). Cada respuesta lleva el encabezado `X-Instancia` con la copia que contestó. Para que cualquier copia pueda atender cualquier petición, el servicio no guarda estado en memoria.
* **El núcleo no se cae con repartidores.** Se pueden crear y pagar pedidos aunque repartidores esté caído. La consulta del núcleo es directa (por el DNS de Docker, sin pasar por el gateway) y tiene un tiempo límite de 3 segundos (1 para conectar); si no responde, el núcleo contesta 503 y no cambia nada. Es la decisión que atraviesa toda la etapa: el sistema prefiere rechazar una operación a adivinar.
* **Quién decide.** Repartidores informa (quién es, su zona y si está disponible); pedidos decide quién gana el pedido con un `UPDATE` condicional en su propia base. Esa regla no cruza la red.
* **El cliente se entera del retraso.** Si un pedido pagado tarda demasiado en tener repartidor, recibe el aviso `pedido.retrasado` (una sola vez, gracias a la marca `retraso_avisado`); si vence el tiempo, el pedido se cancela y se reembolsa. El retraso no cambia la versión del pedido, porque no es un cambio de estado.
* **Una base por servicio.** Siguen siendo bases lógicas dentro de una sola instancia de PostgreSQL. `pedidos.repartidor_id` queda sin llave foránea, así que la existencia del repartidor se verifica al aceptar, preguntándole al servicio.

Con Docker 29 o superior, Traefik debe ser la versión 3.6.1 o más nueva; el compose fija `traefik:v3.6`.

## Qué cambia respecto a la etapa 2

| Aspecto | Etapa 2 | Etapa 3 |
|---|---|---|
| Repartidores | Módulo dentro del núcleo | Servicio aparte con su base `repartidores_db` y dos copias |
| Entrada al sistema | Un puerto por servicio (8000 y 8001) | Un solo puerto: el gateway, en 8080 |
| Núcleo a repartidores | Llamada a una función | Llamada HTTP con tiempo límite; 503 si no responde |
| Aviso de retraso | No existía | `pedido.retrasado`, una vez por pedido |
| Contenedores | 4 | 7 (Traefik, núcleo, notificaciones, 2 de repartidores, RabbitMQ y PostgreSQL) |

## Qué se probó

| Prueba | Resultado observado | Figuras |
|---|---|---|
| Despliegue: siete contenedores y gateway | 3 routers en Traefik; repartidores con 2 servers | 1 a 3 |
| 1. Tres peticiones por una sola dirección | Núcleo, repartidores y notificaciones contestan por `localhost:8080` | 5 |
| 2. Balanceo | 5 peticiones para cada copia | 6 |
| 3. Pedido completo por el gateway | `ASIGNADO`, `ENTREGADO` y avisos 2, 3 y 4; la llamada interna no pasa por Traefik (0 en su registro) | 7 |
| 4. Dos repartidores aceptan a la vez | Un `200` y un `409` | 8 |
| 5. Cae una copia | Diez `200` atendidos por la otra copia; al volver, otra vez 5 y 5 | 9 y 10 |
| 6. Caen las dos copias | Gateway `504`; el núcleo crea y paga; aceptar da `503` en 0.089 s y el pedido sigue `PAGADO`; llegan los avisos de pago, retraso y cancelación y el pago queda `REEMBOLSADO` | 11 y 12 |
| 7. Repartidores lento (5 s de latencia) | `503` a los 3.039 s, no a los 5; `ReadTimeout` en el registro | 13 |
| 8. Una base por servicio | Tres bases; el núcleo ya no tiene el esquema `repartidores` | 14 |
| 9. Repartidor no disponible | "El repartidor no está disponible" al aceptar | 15 |
| 10. La única entrada es el gateway | Solo `traefik` publica puertos de la aplicación (8080 y 8081) | 16 |

La prueba 6 es la principal: cumple el segundo criterio de la historia 5.1 del PRD. Con repartidores caído, el cliente se entera del retraso y el pedido nunca queda en el limbo.

## Cómo repetir las pruebas

Las pruebas se corrieron a mano en una terminal de Linux, todas contra el gateway (`http://localhost:8080`). La bitácora describe las variables y funciones auxiliares que se cargan antes (`B`, `U`, `R`, `P`, `REP`, `nuevo_pedido`, `pagar`, `aceptar`, `avisos`, `instancias`).

```bash
cd Proyecto
docker compose down -v
docker compose up --build -d
docker compose ps            # siete contenedores
curl http://localhost:8080/salud
```

Para la prueba del servicio lento: `LATENCIA_MS=5000 docker compose up -d repartidores`.

## Lo que quedó pendiente para la siguiente etapa

El núcleo ya tenía tiempo límite, pero cada petición seguía esperándolo cuando repartidores estaba caído. La etapa 4 agrega el reintento seguro y el circuit breaker, y la medición real en Windows mostrará que la resolución del nombre también necesitaba su propio tiempo límite.

## Quién hizo qué

| Integrante | Aportes |
|---|---|
| Erick Isaac Echeverria Goicochea ([@ErickI07](https://github.com/ErickI07)) | La etapa completa: separación de repartidores con base propia, cliente HTTP con tiempo límite, gateway Traefik con dos copias, aviso de retraso, las diez pruebas y el reporte. |
| Yukioayax Canek Gabriel Hernández ([@YukiGab](https://github.com/YukiGab)) | Revisión de la etapa. El servicio de notificaciones y la infraestructura de la etapa 2 son la base sobre la que se construyó. |
| Los dos | Decisiones de alcance y diseño del PRD, contrato de eventos, revisión cruzada, evidencias y bitácora. |
