# DiDistribuidores — Sistema de Gestión y Entrega de Pedidos
 
## ¿Qué es el sistema?
 
Es un sistema distribuido para pedidos de comida a domicilio. Un cliente consulta el menú de un
restaurante, hace un pedido, lo paga (pago simulado) y un repartidor lo recoge y lo entrega.
 
Su prioridad es la **consistencia sobre la disponibilidad**: preferimos retrasar o rechazar un
pedido antes que perderlo, duplicarlo o cobrarlo dos veces.
 
Garantías que nunca se rompen:
 
- Nunca se cobra un pedido que no se confirmó.
- Nunca se pierde un pedido ya confirmado.
- Un reintento con la misma `Idempotency-Key` devuelve el mismo pedido, sin segundo cobro.
- La entrega se registra una sola vez, aunque el repartidor confirme dos veces.
## ¿Quiénes somos?
 
- Yukioayax Canek Gabriel Hernández ([@YukiGab](https://github.com/YukiGab))
- Erick Isaac Echeverria Goicochea ([@ErickI07](https://github.com/ErickI07))
Materia: Sistemas Distribuidos 2027-1, Grupo 2, FI-UNAM.
 
## ¿Cómo se levanta?
 
Requisitos: Docker y Docker Compose.
 
```bash
cd Proyecto
docker compose up --build
```
 
La aplicación queda en <http://localhost:8000> (documentación interactiva en `/docs`).
 
Para apagar el sistema (conservando los datos): `docker compose down`.
Para apagarlo y borrar los datos: `docker compose down -v`.
 
## Estructura del repositorio
 
```
.
├── README.md          ← este archivo
├── docs/
│   └── PRD.md         ← requisitos, alcance y decisiones de arquitectura
└── Proyecto/          ← código y docker-compose.yml
```
 
## Plan de ramas
 
El sistema empieza como un monolito y se parte por etapas, cada una en su rama.
 
| Rama | Qué se comprueba |
|---|---|
| `main` | README y PRD |
| `01-monolito` | Una aplicación y una base. Flujo completo de pedidos con idempotencia |
| `02-separacion` | `notificaciones` como proceso aparte, con cola persistente. Los pedidos siguen funcionando con ese proceso apagado |
| `03-separacion` | `repartidores` como servicio propio; gana el primer repartidor que acepta |
| `04-resiliencia` | Reintentos, deduplicación, timeout con reembolso, circuit breaker y pruebas de caídas |
 
## Estado actual
 
Etapa 0: se está ajustando el alcance del PRD. El monolito (`01-monolito`) es una primera
versión en construcción.
 
## Documentación
 
- [PRD](docs/PRD.md): problema, alcance, "dónde vive cada pieza" y decisiones de arquitectura.