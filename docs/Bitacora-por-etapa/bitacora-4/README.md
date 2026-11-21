# Etapa 4: resiliencia

**Rama:** `04-resiliencia` · **Bitácora:** `bitacora-etapa-04.pdf` (12 figuras) · [Volver al índice de bitácoras](../README.md)

Hasta la etapa 3 el sistema ya tenía tiempos límite y mensajería con reintentos. Faltaba resolver qué pasa cuando una pieza falla **seguido**: cada petición seguía llamando al servicio caído y esperando su tiempo límite, así que una falla de repartidores se volvía una espera lenta y generalizada en el núcleo. La etapa 4 agrega las defensas que faltaban, sin cambiar la regla de fondo: el sistema prefiere rechazar una operación a adivinar.

Cada llamada del núcleo a repartidores pasa por tres capas, de afuera hacia adentro:

| Capa | Qué hace |
|---|---|
| Circuit breaker | Si el circuito está abierto, responde 503 al instante, sin llamar |
| Reintento | Máximo uno, y solo si es seguro |
| Tiempo límite | 1 s para resolver el nombre y conectar, 3 s para leer la respuesta |

* **Circuit breaker** (`app/resiliencia.py`). Tras 3 fallos seguidos el núcleo deja de llamar a repartidores y responde 503 al instante; a los 10 segundos deja pasar una sola llamada de prueba, y si sale bien se cierra. Un 404 cuenta como éxito: el servicio contestó bien. Los números se configuran con `BREAKER_FALLOS` y `BREAKER_PAUSA_SEG`.
* **Reintentos seguros.** Uno solo, y solo cuando la petición no llegó a enviarse o el servicio respondió 502, 503 o 504. No se reintenta tras un tiempo de lectura agotado ni cuando el nombre del servicio no se resuelve. Es seguro porque la consulta es de solo lectura, y los reintentos van dentro del breaker para que una llamada con reintento cuente como un solo fallo.
* **Deduplicación completa.** Cada pedido guarda una huella SHA-256 de lo que se pidió. Con la misma clave, la misma huella devuelve `200` con el pedido original y otra huella devuelve `422`, en lugar de devolver el pedido viejo sin avisar.
* **Recuperación automática.** Los pools de conexiones comprueban cada conexión antes de usarla, así que si PostgreSQL se reinicia los servicios se recuperan sin reiniciarse.
* **Estado operativo.** `GET /estado` muestra el circuito hacia repartidores y cuántos eventos del outbox faltan por publicar.
* **Dos interfaces de demostración.** El panel web (`/panel/`) y la aplicación de escritorio (`Proyecto/interfaz/interfaz.py`).

## Qué cambia respecto a la etapa 3

| Aspecto | Etapa 3 | Etapa 4 |
|---|---|---|
| Repartidores falla seguido | Cada aceptación espera su tiempo límite de 3 s | Tras 3 fallos seguidos, 503 al instante |
| Fallos pasajeros | Un fallo es un 503 inmediato | Un reintento seguro antes de rendirse |
| Clave de idempotencia con otro pedido | Se devolvía el pedido anterior sin avisar | `422` con un mensaje claro |
| Conexiones a PostgreSQL | Sin comprobación antes de usarlas | El pool descarta las muertas |
| Estado operativo | Solo los registros | `GET /estado` |

## Qué se probó

Todas las salidas son de una corrida real del sistema completo (siete contenedores, Docker Desktop en Windows 11), con scripts guardados en `pruebas/`.

| Prueba | Resultado observado | Figuras |
|---|---|---|
| 0. Arranque y `/estado` | 7 contenedores; circuito `CERRADO`; 0 eventos pendientes | 2 |
| 1. Clave reutilizada con otro pedido | `201`, `200` y `422`; un solo pedido en la base | 3 |
| 2. Repartidores lento y el breaker | Tres intentos de 3.02 s y luego de 7 ms; circuito `ABIERTO`; se recupera a `CERRADO` | 4 y 5 |
| 3. Una copia congelada | Un `200` y siete `503`; el circuito se abrió (hallazgo 2) | 6 |
| 4. Repartidores caído por completo | Antes del arreglo 8 s por intento; después 1 s y luego 7 ms; se recupera al volver | 7 a 9 |
| 5. El núcleo muere tras un pago | 1 evento pendiente pasa a 0 y el aviso de pago llega una sola vez | 10 |
| 6. PostgreSQL se reinicia | Los tres servicios responden sin haberse reiniciado | 11 |
| 7. El gateway se cae | `000` desde afuera; el núcleo sigue alcanzando a repartidores | 12 |

## Hallazgos de la corrida real

1. **El nombre que no se resuelve no tenía tiempo límite (corregido).** Con repartidores detenido, cada aceptación tardaba 8 s: el DNS de Docker Desktop en Windows tardaba unos 4 s en decir que el nombre no existe, el límite de conexión de `httpx` no cubre esa resolución y el reintento la duplicaba. Ahora el nombre se resuelve con el mismo límite de 1 s y, si no se resuelve, no se reintenta. Resultado: de 8 s a 1 s por intento, y 7 ms con el circuito abierto.
2. **Con una copia congelada el circuito sí puede abrirse.** El DNS de Docker no alterna estrictamente entre copias, y tres llamadas seguidas pueden caer en la congelada. Es el comportamiento correcto del breaker, pero una sola copia congelada puede cortar por 10 s las llamadas internas aunque la otra esté sana. La causa de fondo es una limitación ya declarada: las llamadas internas por DNS no usan los healthchecks del gateway.

## La matriz de caídas

La bitácora cierra con una tabla de lo que le pasa al sistema cuando falla cada pieza, qué mecanismo lo resuelve y dónde está la evidencia (etapa y prueba). Remite a las bitácoras 1, 2 y 3, así que sirve para ver las cuatro juntas.

## Cómo repetir las pruebas

Las pruebas son scripts y se corrieron en Git Bash. Desde `Proyecto/`, con el sistema levantado:

```bash
docker compose down -v
docker compose up --build -d
source ../docs/Bitacora-por-etapa/bitacora-4/pruebas/comun.sh     # variables y funciones auxiliares
source ../docs/Bitacora-por-etapa/bitacora-4/pruebas/prueba-2.sh  # cualquiera de prueba-0.sh a prueba-7.sh
```

La salida real de cada script está en `pruebas/evidencia/`. El PDF muestra estas rutas como `../documentacion/bitacora-4/...`, porque se escribió antes de unificar la documentación en `docs/`.

## Limitaciones

* Las llamadas internas por DNS no usan los healthchecks del gateway (hallazgo 2).
* El breaker es por proceso: cada copia del núcleo tendría su propio circuito.
* PostgreSQL y el gateway siguen siendo puntos únicos de falla, ya declarados desde el PRD.

## Quién hizo qué

| Integrante | Aportes |
|---|---|
| Yukioayax Canek Gabriel Hernández ([@YukiGab](https://github.com/YukiGab)) | Circuit breaker, reintentos seguros, huella de la petición, `/estado`, pools que se recuperan solos, integración de la etapa 4 sobre la 3, corrida real de las ocho pruebas y de la regresión, arreglo del tiempo límite de la resolución de nombres y la aplicación de escritorio. |
| Erick Isaac Echeverria Goicochea ([@ErickI07](https://github.com/ErickI07)) | Panel web de demostración (`/panel/`) integrado con el núcleo y revisión de la etapa. |
| Los dos | Plan de la etapa, matriz de caídas, revisión cruzada de los pull requests, evidencias y bitácora. |
