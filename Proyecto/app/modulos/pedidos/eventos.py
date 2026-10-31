from datetime import datetime, timezone
from uuid import uuid4

from psycopg.types.json import Jsonb

from app import config


def registrar(conn, tipo, pedido, datos=None):
    """Guarda un evento en pedidos.outbox según docs/eventos.md.

    Se llama dentro de la misma transacción que cambia el estado del pedido: o se guardan
    los dos o no se guarda ninguno. Si OUTBOX_ACTIVO no está en 1, no hace nada.
    """
    if not config.OUTBOX_ACTIVO:
        return
    evento_id = uuid4()
    payload = {
        "eventoId": str(evento_id),
        "tipo": tipo,
        "versionPedido": pedido["version"],
        "fecha": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "pedidoId": str(pedido["id"]),
        "usuarioId": str(pedido["usuario_id"]),
        "datos": datos or {},
    }
    conn.execute(
        "INSERT INTO pedidos.outbox (id, tipo, payload, creado_en) VALUES (%s, %s, %s, now())",
        (evento_id, tipo, Jsonb(payload)),
    )
