"""Publica eventos de prueba directamente en RabbitMQ, para probar el consumidor.

Se usa dentro del contenedor de notificaciones (ya tiene pika y la URL de RabbitMQ):

  docker compose exec notificaciones python herramientas/publicar_prueba.py [opciones]

Ejemplos:
  # un evento válido nuevo
  ... publicar_prueba.py --tipo pedido.pagado --version 2
  # el MISMO evento dos veces (el aviso debe guardarse una sola vez)
  ... publicar_prueba.py --evento-id <uuid> --veces 2
  # un mensaje que no es JSON (debe ir a la cola de mensajes fallidos)
  ... publicar_prueba.py --invalido
  # eventos de un pedido que llegan desordenados (versión 4 antes que la 3)
  ... publicar_prueba.py --pedido-id <uuid> --usuario-id <uuid> --tipo pedido.entregado --version 4
  ... publicar_prueba.py --pedido-id <uuid> --usuario-id <uuid> --tipo pedido.asignado --version 3
"""
import argparse
import json
import os
import uuid
from datetime import datetime, timezone

import pika

EXCHANGE = "pedidos.eventos"

DATOS = {
    "pedido.pagado": {"total": 145.0},
    "pedido.retrasado": {"motivo": "buscando_repartidor"},
    "pedido.asignado": {"repartidorId": str(uuid.uuid4())},
    "pedido.entregado": {},
    "pedido.cancelado": {"motivo": "sin_repartidor", "reembolsado": True},
}


def main():
    p = argparse.ArgumentParser(description="Publica eventos de prueba en RabbitMQ")
    p.add_argument("--tipo", default="pedido.pagado", help="tipo del evento (routing key)")
    p.add_argument("--version", type=int, default=2, help="versionPedido")
    p.add_argument("--pedido-id", default=None)
    p.add_argument("--usuario-id", default=None)
    p.add_argument("--evento-id", default=None, help="si se repite, se simula un duplicado")
    p.add_argument("--veces", type=int, default=1, help="cuántas veces publicar el mismo mensaje")
    p.add_argument("--invalido", action="store_true", help="publica un cuerpo que no es JSON")
    a = p.parse_args()

    if a.invalido:
        cuerpo = b"esto no es json"
        print("Publicando un mensaje inválido (no es JSON)")
    else:
        evento = {
            "eventoId": a.evento_id or str(uuid.uuid4()),
            "tipo": a.tipo,
            "versionPedido": a.version,
            "fecha": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "pedidoId": a.pedido_id or str(uuid.uuid4()),
            "usuarioId": a.usuario_id or str(uuid.uuid4()),
            "datos": DATOS.get(a.tipo, {}),
        }
        cuerpo = json.dumps(evento).encode("utf-8")
        print(json.dumps(evento, indent=2))

    conexion = pika.BlockingConnection(pika.URLParameters(os.environ["RABBITMQ_URL"]))
    canal = conexion.channel()
    canal.confirm_delivery()
    for _ in range(a.veces):
        canal.basic_publish(
            exchange=EXCHANGE,
            routing_key=a.tipo,
            body=cuerpo,
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
            mandatory=True,
        )
    conexion.close()
    print(f"Publicado {a.veces} vez/veces en {EXCHANGE} con routing key {a.tipo}")


if __name__ == "__main__":
    main()
