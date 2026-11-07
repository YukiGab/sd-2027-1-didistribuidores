"""Estructura de RabbitMQ que comparten el publicador (pedidos) y el consumidor (notificaciones).

IMPORTANTE: este archivo existe igual en app/modulos/pedidos/topologia.py (núcleo). Si cambias algo aquí,
cámbialo en los dos lados, porque RabbitMQ rechaza declarar una cola o un exchange que ya existe
con argumentos distintos.

Por qué la declaran los dos: si el publicador mandara un evento antes de que notificaciones
haya arrancado por primera vez, la cola no existiría y el mensaje se perdería. Declarando la
cola desde los dos lados (es idempotente), los avisos esperan en ella aunque notificaciones
esté apagado.
"""

EXCHANGE = "pedidos.eventos"            # topic: el routing key es el tipo del evento
EXCHANGE_DLX = "pedidos.eventos.dlx"    # a donde van los mensajes que no se pudieron procesar
COLA = "notificaciones.pedidos"         # cola principal de notificaciones
COLA_DLQ = "notificaciones.pedidos.dlq" # cola de mensajes fallidos
CLAVE_DLQ = "notificaciones.pedidos"


def declarar(canal):
    canal.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    canal.exchange_declare(exchange=EXCHANGE_DLX, exchange_type="direct", durable=True)

    canal.queue_declare(queue=COLA_DLQ, durable=True)
    canal.queue_bind(queue=COLA_DLQ, exchange=EXCHANGE_DLX, routing_key=CLAVE_DLQ)

    canal.queue_declare(
        queue=COLA,
        durable=True,
        arguments={
            "x-dead-letter-exchange": EXCHANGE_DLX,
            "x-dead-letter-routing-key": CLAVE_DLQ,
        },
    )
    canal.queue_bind(queue=COLA, exchange=EXCHANGE, routing_key="pedido.*")
