# PRD · DiDistribuidores — Sistema de Gestión y Entrega de Pedidos

Equipo: DiDistribuidores
Integrantes: @YukiGab (Yukioayax Canek Gabriel Hernández), @ErickI07 (Erick Isaac Echeverria Goicochea), @BaliYandrei28 (Yandrei Guillermo Bali Martínez)
Fecha: 10 de octubre de 2026
Alcance: primera versión funcional para demostración local durante un mes.

## 1. Problema y usuarios

La persona que pide comida a domicilio suele enfrentarse a problemas de lentitud, pedidos que se pierden o cobros duplicados. El método actual depende de plataformas que priorizan la disponibilidad sobre la consistencia, lo que genera desconfianza.

El usuario principal es el cliente que pide comida: necesita realizar un pedido y recibirlo sin que se le cobre dos veces ni se pierda su pedido. Los usuarios secundarios son los restaurantes, que preparan la comida, y los repartidores, que la entregan. El valor del sistema es garantizar la consistencia en la transacción y la logística, incluso si eso significa sacrificar velocidad o disponibilidad en hora pico.

## 2. Por qué es un sistema distribuido

El sistema comienza como un monolito. Después se separan `notificaciones` y `repartidores` para estudiar responsabilidades, comunicación y fallas entre procesos. La frontera importante es entre `pedidos` y `repartidores`: la asignación de un pedido no debe depender de que `repartidores` esté disponible para que `pedidos` siga funcionando. La prioridad es la consistencia sobre la disponibilidad: se prefiere retrasar o rechazar un pedido a perderlo o confundirlo.

El alcance por internet, por sí solo, no exige microservicios. Esta partición permite cumplir la prioridad del producto y demostrar los temas del curso con tres servicios pequeños. Si el número de usuarios crece, se pueden añadir copias de `repartidores` y medir la cola de eventos; la única instancia PostgreSQL será un límite reconocido antes de prometer más capacidad.

## 3. Objetivos y lo que no vamos a hacer

La primera versión tendrá cuatro funciones:

1. **Registrar usuarios y menús:** permitir a los usuarios registrarse, ver menús y realizar pedidos.
2. **Procesar pagos simulados:** procesar pagos de forma segura (simulada).
3. **Asignar repartidores y dar seguimiento:** asignación básica de repartidores con seguimiento en tiempo real.
4. **Enviar notificaciones:** notificaciones de cambios de estado.

Los reportes públicos se podrán filtrar por municipio. La zona se expresará con municipio, colonia y una referencia textual visible, por ejemplo un cruce de calles o un lugar público. El formulario pedirá no escribir un domicilio particular. Quien publica podrá añadir voluntariamente un teléfono de contacto público; si lo omite, la otra persona aún podrá publicar un hallazgo que el dueño verá en la bandeja si sigue ese municipio.

El registro e inicio de sesión con correo y contraseña son funciones de apoyo para publicar y subscribirse; se mantienen deliberadamente básicos. Antes de publicar un teléfono, el formulario pide consentimiento explícito para mostrarlo.

La versión se demostrará localmente con Docker Compose. Quedan fuera: pasarela de pagos real, app móvil nativa, GPS real (coordenadas simuladas), mapa interactivo, coordenadas, localizadores o chips, reconocimiento por foto, carga de imágenes, chat, vinculación automática de hallazgos, correo, notificaciones push, recuperación de contraseña y despliegue público. Una interfaz web sencilla, adaptable a teléfono, basta para demostrar los flujos.

## 4. El requisito que perseguimos y lo que dejamos atrás

**Prioridad:** la consistencia en los pedidos y los pagos. Que ningún pedido se pierda ni se quede a medias, y que nunca se cobre un pedido que no se confirmó.

**Lo que sacrificamos a cambio:**
- La asignación de repartidor puede tardar más.
- El seguimiento en tiempo real puede mostrar datos con unos segundos de retraso.
- El sistema a veces retrasa o rechaza pedidos en hora pico (disponibilidad).

**Lo intocable:** nunca se cobra un pedido que no se confirmó y nunca se pierde un pedido ya confirmado.

## 5. Historias de usuario

### 5.1 Realizar un pedido
**Como** cliente con hambre que ya pagó, **quiero** que mi pedido llegue y que el sistema no me cobre dos veces ni lo pierda, **para** poder comer tranquilo sin estar revisando la app a cada rato.

*   **Criterio de aceptación 1 (Idempotencia - Obligatorio):** Dado que ya pagué y confirmé un pedido, cuando mi app reintenta la petición (porque se cayó la red), el sistema debe responderme con el mismo pedido y no generar un cobro ni un pedido nuevo.
*   **Criterio de aceptación 2 (Consistencia en fallos - Obligatorio):** Dado que ya pagué, cuando el servicio de repartidores se cae o no hay nadie disponible, el sistema debe avisarme al llegar a los 20 minutos para que yo decida qué hacer, y nunca puede dejar mi pedido en el limbo sin avisarme.
*   **Criterio de aceptación 3 (Entrega única - Obligatorio):** Dado que el repartidor llegó a mi puerta, cuando ingresa el código de confirmación, el pedido debe pasar a "entregado" una sola vez, aunque el repartidor presione el botón dos veces.

### 5.2 Recibir notificaciones
**Como** cliente, **quiero** recibir alertas sobre el cambio de estado de mi pedido, **para** saber si va en camino o si ya llegó.

*   **Criterio de aceptación 1 (Obligatorio):** Dado que el pedido cambió de estado, cuando el sistema procesa el evento, debo recibir una notificación con un retraso máximo de unos segundos.
*   **Criterio de aceptación 2 (Obligatorio):** Dado que el servicio de notificaciones está caído, cuando se recupere, debo recibir las notificaciones pendientes sin que se pierdan ni se dupliquen.

## 6. Del monolito a los servicios

En el sistema final, los módulos del monolito son: `usuarios`, `restaurantes`, `pedidos`, `pagos`, `repartidores` y `notificaciones`.

**Dueño de la verdad:** `pedidos` es el dueño único del estado del pedido. La clave única para evitar pedidos duplicados y la regla de "gana la primera aceptación del repartidor" viven en el módulo de `pedidos`. `repartidores` solo muestra pedidos disponibles y recibe la aceptación, pero `pedidos` valida y guarda la decisión final.

**Plan de ramas:**

| Rama | Resultado comprobable |
| :--- | :--- |
| `01-monolito` | Una aplicación y una base. Publicación completa de pedidos y cuenta de demostración. Módulos internos: usuarios, restaurantes, pedidos, pagos, repartidores, notificaciones. |
| `02-separacion` | Se separa `notificaciones` a otro proceso y otra base lógica. Los pedidos siguen funcionando con ese proceso apagado. Los avisos pendientes se guardan en una cola persistente. |
| `03-separacion` | Se separa `repartidores` como servicio propio. Se implementa la asignación básica (mostrar a repartidores de la zona, gana el primero que acepta). |
| `04-resiliencia` | Se verifican reintentos, deduplicación, timeouts y caídas de procesos con pruebas reproducibles. |

**Manejo de fallas entre servicios:**
Al confirmar un reporte, `pedidos` guarda en una transacción local el reporte y un evento pendiente con ID único. Un proceso publicador lee la tabla de avisos pendientes y publica el evento en la cola persistente. Si `notificaciones` se cae, el evento queda pendiente y se reintenta al recuperarse.
Si `repartidores` se cae, `pedidos` envía una alerta preventiva y verifica con múltiples servidores redundantes si hay salud en la red. Si falla, el pedido se queda en estado "pendiente" hasta que ocurre un timeout (20 minutos), momento en el cual pasa a "cancelado" y se gatilla el reembolso a través de la cola persistente (Opción A).

## 7. Dónde vive cada pieza

| Pieza | Dónde vive | Por qué | Qué pasa si falla |
| :--- | :--- | :--- | :--- |
| **API gateway** | Traefik es la única puerta pública. Dirige `/` a la interfaz servida por `pedidos`, `/api/usuarios/` a `identidad`, `/api/mascotas/` y `/api/reportes/` a `pedidos`, y `/api/alertas/` a `alertas`. | Da una entrada y rutas claras. Es la Opción C elegida para evitar que `pedidos` sea un cuello de botella. | No entran nuevas solicitudes mientras está caído. Los datos ya guardados permanecen; es un punto único de falla aceptado para la demo. |
| **Directorio / DNS** | DNS interno de Docker Compose para llamadas entre servicios; Traefik descubre contenedores mediante su proveedor Docker. | Evita direcciones IP fijas. | Si Docker o su DNS falla, los procesos no se encuentran; se restablece el entorno y se comprueban rutas antes de continuar. |
| **Balanceo** | Traefik reparte peticiones entre dos copias sin estado de `repartidores`; ambas usan la misma base de `pedidos`. | Permite observar una réplica caída y continuar con la otra. | Durante la detección pueden fallar peticiones. El cliente reintenta publicaciones solo con clave de idempotencia; si caen ambas, no se confirma el reporte. |
| **Datos** | Una instancia PostgreSQL para `pedidos` (consistencia transaccional). Bases NoSQL para el resto. Una base lógica por servicio. Sin réplicas ni particiones en esta versión. | Permite propiedad de datos y transacciones locales sin operar un clúster de base de datos. | Si PostgreSQL cae, no se confirman nuevas escrituras. La base es un punto único de falla declarado. |
| **Operaciones entre servicios** | Eventos pendientes en la base de `pedidos`; `notificaciones` los consulta por HTTP interno y confirma solo después de guardar sus alertas. | La publicación no depende de una transacción distribuida ni de que `notificaciones` esté disponible. | Si `notificaciones` falla, el evento queda pendiente. No se revierte el reporte y no hace falta una saga compensatoria para este flujo. |
| **Manejo de fallas** | Consultas internas con timeout de 20 minutos para cancelación y reembolso; reintentos con espera; clave de idempotencia para publicar; alerta única por evento y destinatario. Circuit Breaker para proteger `pedidos` de saturarse si `repartidores` falla (Opción C). | Evita esperas indefinidas y duplicados en reintentos. | La siguiente consulta retoma el trabajo. Una publicación sin confirmación solo se reintenta con la misma clave. Se usa Circuit Breaker para evitar el efecto cascada. |

## 8. Stack y cómo se levanta

Python y FastAPI se usan en el monolito y los servicios para mantener un solo lenguaje en la API y el proceso que genera alertas. PostgreSQL permite guardar reporte y evento en una transacción local y aplicar restricciones de unicidad. Traefik aporta gateway, descubrimiento de contenedores y balanceo. Docker Compose levanta los servicios, la base y la red interna. La interfaz usa HTML, CSS y JavaScript sencillos; no necesita una aplicación móvil independiente.

`docker compose up --build` debe levantar el sistema y mostrar una página inicial desde Traefik. La demostración mínima debe permitir: publicar un pedido; ver su enlace público; recibir la alerta en menos de 3 minutos; detener `notificaciones` y publicar otro sin perderlo; reiniciar `notificaciones` y recibir una sola alerta; detener una copia de `repartidores` y continuar con la otra; detener PostgreSQL y comprobar que no aparece como publicado un reporte que no se guardó.

## 9. Decisiones de arquitectura

| Decisión | Alternativa descartada para esta versión | Por qué |
| :--- | :--- | :--- |
| Empezar con un monolito y separar por ramas. | Crear todos los servicios desde el primer día. | Primero se comprueba el flujo y después se hace visible el efecto de cruzar la red. |
| Conservar reportes y eventos pendientes en la misma transacción local. | Enviar alertas dentro de la solicitud de publicación. | Una falla de alertas no impide guardar el reporte. |
| Separar `notificaciones` y `repartidores` como servicios. | Dividir también `pagos` y `restaurantes` desde el inicio. | Hay tres fronteras defendibles sin multiplicar llamadas y bases. `pagos` sigue presente pero acoplado para garantizar consistencia. |
| Usar tokens firmados que `pedidos` y `repartidores` validan localmente. | Consultar identidad en cada solicitud. | Publicar con un token vigente sigue funcionando si identidad se detiene. Se acepta que un token siga válido hasta su vencimiento. |
| Usar cola persistente para notificaciones y reembolsos. | Enviar notificaciones dentro de la solicitud de publicación. | Una falla de notificaciones no impide guardar el reporte. |
| Representar ubicación con municipio, colonia y referencia pública. | Mapa y coordenadas. | Permite describir el avistamiento sin implementar cartografía; se evita pedir domicilios privados. |
| Usar una instancia PostgreSQL con bases separadas. | Réplicas y particiones sin carga media. | La prioridad es demostrar propiedad de datos y fallas entre servicios. Se reconoce la falla de la base única. |
| Usar consulta periódica de eventos por HTTP interno. | Añadir un broker desde el inicio. | Da entrega diferida recuperable con menos componentes para operar en un mes. |

## 10. Preguntas abiertas y desacuerdos

No hubo registros ni desacuerdos.

**Preguntas abiertas (para el arquitecto y la defensa):**
1. **Claves no concluidas:** ¿Cuál es el número exacto de duración de las claves de pedidos no concluidos? (Se habló de 10-20 min, falta fijar uno).
2. **Vida de los pedidos:** ¿Qué pasa exactamente con los pedidos pasados los 6 meses (se borran, se archivan en frío)?
3. **Criterio de "zona":** ¿Cómo definen "cercanos en la zona" sin GPS real (por colonia, por número de zona)?
4. **Cliente sin repartidor:** Si pasan los 20 minutos y el cliente "decide qué hacer", ¿qué opciones exactas tiene y qué pasa con su cobro?
5. **Disputas:** Quedó fuera el caso de "el repartidor dice que entregó pero el cliente dice que no llegó". ¿Lo dejan explícitamente fuera de alcance o lo manejan con el módulo de Atención?
6. **Dueño de piezas nuevas:** ¿Quién es el dueño de la cola persistente, la tabla de avisos pendientes y el proceso publicador? ¿Dónde viven exactamente?
7. **Costo de fallos:** Si el restaurante ya cocinó y el servicio de `repartidores` falla justo después del pre-check, ¿quién asume el costo de la comida preparada (el restaurante, la plataforma o el cliente)?
8. **Aclaración de timeout:** Se definió un timeout de 20 minutos para la cancelación y reembolso. ¿Existe un timeout más corto (3-5 minutos) para reintentos de red internos entre servicios, o el timeout de 20 minutos aplica para ambos casos?
9. **Módulo de Atención:** Se mencionó un servicio paralelo de `Atención` para gestionar inconsistencias (como un pedido forzado a "entregado" que el cliente no recibió). ¿Es un servicio completamente nuevo en la arquitectura o es una funcionalidad dentro de `pedidos`?