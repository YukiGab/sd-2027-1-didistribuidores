# PRD · DiDistribuidores — Sistema de Gestión y Entrega de Pedidos de Comida

Equipo: DiDistribuidores
Integrantes: @YukiGab (Yukioayax Canek Gabriel Hernández), @ErickI07 (Erick Isaac Echeverria Goicochea)
Fecha: 10 de octubre de 2026
Alcance: primera versión funcional para demostración local durante un mes.

## 1. Problema y usuarios

El cliente que pide comida a domicilio suele enfrentarse a problemas de lentitud, pedidos que se pierden o cobros duplicados en hora pico. Los métodos actuales dependen de sistemas que priorizan la disponibilidad, lo que genera desconfianza y pérdidas económicas.

El usuario principal es el cliente que pide comida: necesita realizar un pedido y recibirlo sin que se le cobre dos veces ni se pierda su pedido. Los usuarios secundarios son los restaurantes, que preparan la comida, y los repartidores, que la entregan. El valor del sistema es garantizar la consistencia en la transacción y la logística, incluso si eso significa sacrificar velocidad o disponibilidad.

## 2. Por qué es un sistema distribuido

El sistema comienza como un monolito. Después se separan `notificaciones` y `repartidores` para estudiar responsabilidades, comunicación y fallas entre procesos. La frontera importante es entre `pedidos` y `repartidores`: la asignación de un pedido no debe depender de que `repartidores` esté disponible para que `pedidos` siga funcionando. 

El sistema necesita ser distribuido por la alta carga de pedidos en hora pico, lo que convertiría las escrituras en la base de datos en un cuello de botella. La prioridad es la **consistencia sobre la disponibilidad**: se prefiere retrasar o rechazar un pedido a perderlo, confundirlo o cobrarlo dos veces.

## 3. Objetivos y lo que no vamos a hacer

La primera versión tendrá cuatro funciones:

1. **Registrar usuarios y menús:** permitir a los usuarios registrarse, ver menús y realizar pedidos.
2. **Procesar pagos simulados:** procesar pagos de forma segura (simulada).
3. **Asignar repartidores y dar seguimiento:** asignación básica de repartidores con seguimiento en tiempo real.
4. **Enviar notificaciones:** notificaciones de cambios de estado.

**Lo que NO vamos a hacer:**
*   No construiremos una pasarela de pagos real (se simulará con un servicio interno).
*   No haremos una app móvil nativa (solo backend y API Gateway).
*   No implementaremos geolocalización GPS real (se simularán coordenadas). El criterio de "zona" se definirá más adelante sin GPS.
*   Queda fuera el manejo de disputas ("el repartidor dice que entregó pero el cliente dice que no"). Solo el repartidor confirmará la llegada mediante un botón/código para evitar clics accidentales. 

## 4. El requisito que perseguimos y lo que dejamos atrás

**Prioridad:** La consistencia en los pedidos y los pagos. Que ningún pedido se pierda ni se quede a medias, y que nunca se cobre un pedido que no se confirmó.

**Lo que sacrificamos a cambio:**
- La asignación de repartidor puede tardar más (asignación básica, no inteligente).
- El seguimiento en tiempo real puede mostrar datos con unos segundos de retraso.
- El sistema a veces retrasa o rechaza pedidos en hora pico (disponibilidad).

**Lo intocable:** Nunca se cobra un pedido que no se confirmó y nunca se pierde un pedido ya confirmado.

## 5. Historias de usuario

### 5.1 Realizar un pedido
**Como** cliente con hambre que ya pagó, **quiero** que mi pedido llegue y que el sistema no me cobre dos veces ni lo pierda, **para** poder comer tranquilo sin estar revisando la app.

*   **Criterio de aceptación 1 (Idempotencia - Obligatorio):** Dado que ya pagué y confirmé un pedido, cuando mi app reintenta la petición (porque se cayó la red), el sistema debe responderme con el mismo pedido y no generar un cobro ni un pedido nuevo (la clave única vive en la base de datos de `pedidos`).
*   **Criterio de aceptación 2 (Consistencia en fallos - Obligatorio):** Dado que ya pagué, cuando el servicio de repartidores se cae o no hay nadie disponible, el sistema debe avisarme y nunca puede dejar mi pedido en el limbo sin avisarme.
*   **Criterio de aceptación 3 (Entrega única - Obligatorio):** Dado que el repartidor llegó a mi puerta, cuando ingresa el código de confirmación, el pedido debe pasar a "entregado" una sola vez, aunque el repartidor presione el botón dos veces.

**Criterios deseables:**
*   Que el menú del restaurante cargue en menos de 3 segundos en hora pico.
*   Que las notificaciones de cambio de estado me lleguen con menos de 10 segundos de retraso.
*   Que la app me muestre un mensaje claro si el sistema está saturado.

## 6. Del monolito a los servicios

En el sistema final, los módulos del monolito son: `usuarios`, `restaurantes` (incluye menús), `pedidos`, `pagos`, `repartidores` (incluye tracking) y `notificaciones`.

**Dueño de la verdad:** `pedidos` es el dueño único del estado del pedido. La clave única para evitar pedidos duplicados y la regla de "gana la primera aceptación del repartidor" viven en el módulo de `pedidos`. `pagos` es un servicio stateless (API pura) y el control de idempotencia y el registro de transacciones se centralizan en la base de datos de `pedidos`.

**Plan de ramas:**
| Rama | Resultado comprobable |
| :--- | :--- |
| `01-monolito` | Una aplicación y una base. Flujo completo de pedidos. Módulos internos: usuarios, restaurantes, pedidos, pagos, repartidores, notificaciones. |
| `02-separacion` | Se separa `notificaciones` a otro proceso y otra base lógica. Los pedidos siguen funcionando con ese proceso apagado. Los avisos pendientes se guardan en una cola persistente. |
| `03-separacion` | Se separa `repartidores` como servicio propio. Se implementa la asignación básica (mostrar a repartidores de la zona, gana el primero que acepta mediante actualización condicional en base de datos). |
| `04-resiliencia` | Se verifican reintentos, deduplicación, timeouts (20 minutos para cancelar/reembolsar) y caídas de procesos con pruebas reproducibles. |

**Manejo de fallas entre servicios:**
*   **Notificaciones:** `pedidos` guarda en una transacción local el cambio de estado y el aviso pendiente. Un proceso publicador los envía a la cola persistente. Si `notificaciones` se cae, el evento queda pendiente y se reintenta.
*   **Reembolsos:** Si `repartidores` falla o el pedido no se asigna, el pedido se queda en estado "pendiente" hasta que ocurre un timeout de **20 minutos**. Al llegar a este límite, pasa a "cancelado" y se gatilla el reembolso a través de una cola persistente.
*   **Pre-check:** Antes de procesar, `pedidos` verifica con múltiples servidores redundantes si hay salud en la red de repartidores y restaurantes. Si hay fallo, se alerta preventivamente.

## 7. Dónde vive cada pieza

| Pieza | Dónde vive | Por qué | Qué pasa si falla |
| :--- | :--- | :--- | :--- |
| **API gateway** | Traefik es la única puerta pública (Opción C). Dirige `/` a la interfaz, `/api/usuarios/` a `usuarios`, `/api/pedidos/` a `pedidos`, etc. | Evita que `pedidos` sea un cuello de botella o punto único de fallo de entrada. | No entran nuevas solicitudes mientras está caído. Los datos ya guardados permanecen; es un punto único de falla aceptado para la demo. |
| **Directorio / DNS** | DNS interno de Docker Compose para llamadas entre servicios. | Evita direcciones IP fijas y simplifica el despliegue local. | Si el DNS falla, los procesos no se encuentran; se restablece el entorno. |
| **Balanceo** | El Gateway o el orquestador reparte peticiones entre múltiples copias (réplicas) sin estado de `repartidores` y `pedidos`. | Permite escalamiento horizontal y tolerancia a fallos de copias individuales. | El cliente reintenta peticiones con clave de idempotencia. |
| **Datos** | PostgreSQL para `pedidos` y `pagos` (consistencia ACID). Bases NoSQL para el resto. | `pedidos` y `pagos` exigen transacciones fuertes para no duplicar cobros. | Si PostgreSQL cae, no se confirman nuevas escrituras. Es un punto único de falla declarado. |
| **Operaciones entre servicios** | Eventos pendientes en base de datos y cola persistente. Llamadas HTTP internas con validadores de idempotencia. | Desacopla servicios críticos y evita transacciones distribuidas complejas. | Si un servicio cae, el evento o la transacción queda pendiente y se reintenta. |
| **Manejo de fallas** | Timeout de **20 minutos** para cancelación/reembolso. Circuit Breaker (Opción C) para que `pedidos` deje de intentar comunicarse con `repartidores` si este falla repetidamente, evitando el efecto cascada. | Protege los recursos del sistema y define límites claros de espera. | Si el circuito se abre, se devuelve error rápido y se procede a la cancelación y reembolso. |

## 8. Stack y cómo se levanta

Python y **FastAPI** se usan en el monolito y los servicios por su facilidad de desarrollo, validación de datos con Pydantic y soporte para escalamiento horizontal (async/await). **PostgreSQL** permite guardar el estado del pedido y los cobros en transacciones locales y aplicar restricciones de unicidad. Docker Compose levanta los servicios, la base y la red interna. 

`docker compose up --build` debe levantar el sistema y mostrar la interfaz. La demostración mínima debe permitir: hacer un pedido; verificar la idempotencia; detener `notificaciones` y comprobar que el aviso se envía al recuperarse; simular la caída de `repartidores` y verificar que el pedido se cancela y reembolsa tras el timeout de 20 minutos.

## 9. Decisiones de arquitectura

| Decisión | Alternativa descartada para esta versión | Por qué |
| :--- | :--- | :--- |
| Empezar con un monolito y separar por ramas. | Crear todos los servicios desde el primer día. | Primero se comprueba el flujo y después se hace visible el efecto de cruzar la red. |
| Centralizar la idempotencia de pagos en la base de datos de `pedidos`. | Darle a `pagos` su propia base de datos o hacerlo responsable de la idempotencia. | Al ser `pagos` una API stateless, centralizar la verdad en `pedidos` elimina el riesgo de inconsistencias y dobles cobros. |
| Usar cola persistente para notificaciones y reembolsos. | Enviar notificaciones o reembolsos síncronamente en la misma petición. | Una falla en notificaciones o pagos no bloquea ni revierte la confirmación del pedido. |
| Separar `notificaciones` y luego `repartidores`. | Separar `pagos` primero. | Separar `pagos` introducía el riesgo de transacciones distribuidas (cobro sin pedido o pedido sin cobro). `repartidores` es más seguro porque depende de que el pedido exista. |
| Usar timeout de 20 minutos para cancelar si falla `repartidores`. | Cancelación inmediata o espera indefinida. | Da margen a que la red o el servicio se recuperen sin colgar al cliente, pero pone un límite estricto para no perder el pedido ni el dinero. |
| Implementar Circuit Breaker. | Reintentos infinitos. | Evita que `pedidos` se sature de peticiones fallidas y caiga todo el sistema por efecto cascada. |

## 10. Preguntas abiertas y desacuerdos

**Preguntas abiertas (para el arquitecto y la defensa):**
1. **Claves no concluidas:** Se mencionó un rango de 10 a 20 minutos. ¿Cuál es el número exacto que fijarán para la duración de las claves de pedidos no concluidos?
2. **Vida de los pedidos:** Se definió un historial de 6 meses para "Mis pedidos". ¿Qué pasa exactamente con los pedidos pasados los 6 meses (se borran físicamente, se archivan en un servidor offline por temas legales)?
3. **Criterio de "zona":** Para la asignación básica sin GPS real, ¿cómo definirán la zona (por colonia, por un número de zona, por un listado de calles)?
4. **Cliente sin repartidor:** Si pasan los 20 minutos y el cliente "decide qué hacer", ¿qué opciones exactas tiene en la interfaz y qué pasa con su cobro?
5. **Costo de fallos:** Si el restaurante ya cocinó la comida y el servicio de `repartidores` falla justo después del pre-check, ¿quién asume el costo de la comida preparada (el restaurante, la plataforma o el cliente)?
6. **Módulo de Atención:** Se mencionó un servicio paralelo de `Atención` para gestionar disputas o forzar estados (ej. entregado con alerta). ¿Es un servicio completamente nuevo en la arquitectura o es una funcionalidad dentro de `pedidos`?
7. **Timeouts internos:** Se definió el timeout de 20 minutos para el reembolso, pero también se mencionó un timeout de 3 a 5 minutos. ¿Ese rango menor aplica para reintentos de red internos entre servicios o para avisar al cliente en caso de fallo técnico inminente?
