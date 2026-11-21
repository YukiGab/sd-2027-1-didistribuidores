# Bitácoras por etapa

Esta carpeta reúne las **bitácoras de pruebas** de DiDistribuidores, una por cada etapa del proyecto. Cada bitácora documenta el trabajo realizado durante una etapa: qué se probó, cómo y qué se observó, con la captura de la ejecución real.

> **Esto no es el reporte final.** El reporte final del proyecto (problema, diagramas, decisiones, manejo de fallas, cómo levantarlo, qué falta y quién hizo qué) es un documento aparte: [`reporte-final.pdf`](../reporte-final.pdf). Las bitácoras sirven como evidencia y como apoyo para ese reporte.

## Contenido

Cada carpeta tiene el PDF de su bitácora (`bitacora-etapa-0N.pdf`) y, junto a él, sus capturas y salidas. Dentro de cada una hay un `README.md` que explica esa etapa en detalle.

| Carpeta | Etapa | Rama | Qué documenta |
|---|---|---|---|
| [`bitacora-1/`](bitacora-1/) | 1. Monolito modular | `01-monolito` | Un solo sistema y una sola base, ordenados en módulos. Idempotencia, pago, aceptación del pedido por un repartidor, entrega con código, cancelación por tiempo con reembolso, infraestructura con Docker Compose y tabla `outbox`. |
| [`bitacora-2/`](bitacora-2/) | 2. Notificaciones como servicio aparte | `02-separacion` | Notificaciones con su propia base, publicador del outbox hacia RabbitMQ y consumidor. Flujo normal, servicio apagado, evento duplicado, mensaje inválido, eventos desordenados, RabbitMQ caído y reinicio de la cola. |
| [`bitacora-3/`](bitacora-3/) | 3. Repartidores como servicio, gateway y réplicas | `03-separacion` | Repartidores con base propia y dos copias, Traefik como única entrada, llamada del núcleo con tiempo límite (503 si no responde) y aviso de retraso. Enrutamiento, balanceo, caída de una y de las dos copias, servicio lento, bases separadas y puertos publicados. |
| [`bitacora-4/`](bitacora-4/) | 4. Resiliencia | `04-resiliencia` | Circuit breaker, reintentos seguros, deduplicación con huella de la petición, `GET /estado`, recuperación automática de conexiones y las dos interfaces de demostración. Ocho pruebas de caídas, dos hallazgos de la corrida real y la matriz de caídas. |

## El hilo de las cuatro etapas

Cada etapa responde una pregunta distinta, y cada bitácora parte de la anterior:

| Etapa | La pregunta que responde |
|---|---|
| 1 | ¿Cómo evitamos cobros dobles y pedidos duplicados cuando llegan peticiones al mismo tiempo? La base de datos decide (`UNIQUE` y `UPDATE` condicional). |
| 2 | ¿Qué pasa con los avisos si un servicio o la cola se cae? Outbox, RabbitMQ y un consumidor idempotente. |
| 3 | ¿Qué pasa con una llamada que necesita respuesta ya? Tiempo límite, 503 y dos copias detrás de un gateway. |
| 4 | ¿Qué pasa cuando una pieza falla seguido? Circuit breaker, reintentos seguros y pruebas sistemáticas de caídas. |

La **matriz de caídas** de la bitácora 4 reúne todo lo que le pasa al sistema cuando falla cada pieza y remite, para cada caso, a la etapa y la prueba donde está la evidencia. Desde esta matriz se pueden consultar las pruebas de las cuatro etapas.

## Cómo está escrita cada bitácora

Las cuatro siguen la misma estructura:

1. **Portada**.
2. **Introducción** de la etapa: qué se construyó y qué decisión de diseño atraviesa las pruebas.
3. **Una sección por cada prueba**, con *Qué queríamos comprobar*, *Cómo funciona* (cuando hace falta explicarlo), el comando que se ejecutó y *Qué se observó*, junto con la captura.
4. **Tabla de resumen** con lo que se comprobó, el resultado observado y la figura donde se ve.
5. **Quién hizo qué** en esa etapa.


## Detalles que conviene saber

- **Las direcciones cambian entre etapas.** En las etapas 1 y 2 el núcleo responde en `localhost:8000` y notificaciones en `localhost:8001`. A partir de la etapa 3 esos puertos ya no existen: todo entra por el gateway, en `localhost:8080`.
- **Las pruebas parten de un entorno limpio.** Para repetirlas hay que levantar el sistema desde cero (`docker compose down -v` y luego `docker compose up --build -d`).
- **Los comandos se ven distintos entre bitácoras.** Las etapas 1 a 3 se probaron a mano, algunas en una terminal de Linux (`curl`, `bash`) y otras en PowerShell (`curl.exe`, `Invoke-RestMethod`). La etapa 4 se probó con scripts en Git Bash, sobre Docker Desktop en Windows 11. Aunque cambian los comandos, las pruebas verifican el mismo comportamiento.
- **Cada bitácora describe el código de su propia rama.** Si algo cambia en una etapa posterior, la bitácora anterior no se actualiza. Por ejemplo, la etapa 3 documenta el tiempo límite de 3 s del núcleo hacia repartidores; la etapa 4 le agrega el reintento, el breaker y el tiempo límite de 1 s para resolver el nombre del servicio.

## Cómo repetir las pruebas

**Etapas 1 a 3.** Cada prueba trae su comando en la bitácora. Se corren desde cero, con las direcciones de su etapa.

**Etapa 4.** Las pruebas son scripts. Desde `Proyecto/`, en bash o Git Bash, con el sistema levantado:

```bash
source ../docs/Bitacora-por-etapa/bitacora-4/pruebas/comun.sh   # variables y funciones auxiliares
source ../docs/Bitacora-por-etapa/bitacora-4/pruebas/prueba-2.sh # cualquiera de prueba-0.sh a prueba-7.sh
```


## Relación con el resto de la documentación

| Documento | Para qué sirve |
|---|---|
| [`../PRD.md`](../PRD.md) | Requisitos, alcance y decisiones de arquitectura del proyecto. |
| [`../eventos.md`](../eventos.md) | Contrato de los eventos entre `pedidos` y `notificaciones`. |
| [`../reporte-final.pdf`](../reporte-final.pdf) | Reporte final del equipo. |
| [`../manual-de-usuario.pdf`](../manual-de-usuario.pdf) | Cómo levantar el sistema y usar la aplicación de escritorio, el panel web y la API. |
| [`../pruebas/pruebas-del-proyecto.pdf`](../pruebas/pruebas-del-proyecto.pdf) | Plan y resultados de todas las pruebas del proyecto. |
| Esta carpeta | Evidencia de pruebas, etapa por etapa. |

## Equipo

- Erick Isaac Echeverria Goicochea ([@ErickI07](https://github.com/ErickI07))
- Yukioayax Canek Gabriel Hernández ([@YukiGab](https://github.com/YukiGab))