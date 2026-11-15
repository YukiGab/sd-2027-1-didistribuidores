# Bitácoras por etapa

Esta carpeta reúne las **bitácoras de pruebas** que se fueron escribiendo durante el desarrollo de DiDistribuidores, una por cada etapa del proyecto.

> **Esto no es el reporte final.** El reporte final del proyecto (problema, diagramas, decisiones, manejo de fallas, cómo levantarlo, qué falta y quién hizo qué) es un documento aparte, en [`docs/reporte-final.pdf`]. Las bitácoras son el registro de trabajo: qué se probó en cada etapa, cómo y qué se observó. Sirven como evidencia y como material de apoyo para el reporte final.

## Contenido

| Archivo | Etapa | Rama | Qué documenta |
|---|---|---|---|
| `bitacora-etapa-01.docx` | 1. Monolito modular | `01-monolito` | Un solo sistema y una sola base, ordenados en módulos (usuarios, restaurantes, pedidos, pagos y repartidores). Pruebas de idempotencia, pago, aceptación del pedido por un repartidor, entrega con código, cancelación por tiempo con reembolso, infraestructura con Docker Compose y tabla `outbox`. |
| `bitacora-etapa-02.docx` | 2. Notificaciones como servicio aparte | `02-separacion` | El servicio de notificaciones con su propia base, el publicador del outbox hacia RabbitMQ y el consumidor. Pruebas de flujo normal, servicio apagado, evento duplicado, mensaje inválido, eventos desordenados, RabbitMQ caído y reinicio de la cola. |
| `bitacora-etapa-03.docx` | 3. Repartidores como servicio, gateway y réplicas | `03-separacion` | Repartidores como servicio con base propia y dos copias, Traefik como única entrada, llamada del núcleo con tiempo límite (503 si no responde) y aviso de retraso. Pruebas de enrutamiento, balanceo, caída de una y de las dos copias, servicio lento, bases separadas y puertos publicados. |

## Cómo está escrita cada bitácora

Las tres siguen la misma estructura:

1. **Portada**.
2. **Introducción** de la etapa: qué se construyó y qué decisión de diseño atraviesa las pruebas.
3. **Una sección por cada prueba**, con tres partes: *Qué queríamos comprobar*, *Cómo funciona* (cuando hace falta explicarlo), el comando que se ejecutó y *Qué se observó*, junto con la captura de pantalla.
4. **Tabla de resumen** con lo que se comprobó y el resultado observado.
5. **Quién hizo qué** en esa etapa.

Cada captura es una evidencia real de la ejecución del sistema.

## Detalles que conviene saber

- **Las direcciones cambian entre etapas.** En las etapas 1 y 2 el núcleo responde en `localhost:8000` y notificaciones en `localhost:8001`. A partir de la etapa 3 esos puertos ya no existen: todo entra por el gateway, en `localhost:8080`.
- **Las pruebas parten de un entorno limpio.** Para repetirlas hay que levantar el sistema desde cero (`docker compose down -v` y luego `docker compose up --build -d`), porque los scripts de la carpeta `db/` solo se ejecutan cuando el volumen está vacío.
- **Los comandos pueden verse distintos entre capturas.** Algunas se hicieron en una terminal de Linux (`curl`, `bash`) y otras en PowerShell (`curl.exe`, `Invoke-RestMethod`). El comportamiento observado es el mismo.
- **Cada bitácora corresponde al estado del código en la rama de su etapa.** Si el código cambia en una etapa posterior, la bitácora anterior no se actualiza: describe lo que se probó en ese momento.

## Relación con el resto de la documentación

| Documento | Para qué sirve |
|---|---|
| [`docs/PRD.md`](../PRD.md) | Requisitos, alcance y decisiones de arquitectura del proyecto. |
| [`docs/eventos.md`](../eventos.md) | Contrato de los eventos entre `pedidos` y `notificaciones`. |
| [`docs/reporte-final.pdf`] | Reporte final del equipo (Pendiente). |
| Esta carpeta | Evidencia de pruebas, etapa por etapa. |

## Equipo

- Erick Isaac Echeverria Goicochea ([@ErickI07](https://github.com/ErickI07))
- Yukioayax Canek Gabriel Hernández ([@YukiGab](https://github.com/YukiGab))
