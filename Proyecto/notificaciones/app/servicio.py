"""Reglas de notificaciones: validar el evento, convertirlo en aviso y guardarlo."""
import json
from datetime import datetime, timezone
from uuid import UUID

from app import db, mensajes, repositorio

CAMPOS = ("eventoId", "tipo", "versionPedido", "fecha", "pedidoId", "usuarioId", "datos")


class MensajeInvalido(Exception):
    """El mensaje no se puede interpretar. No tiene caso reintentarlo: va a la cola de fallidos."""


def _uuid(valor, campo):
    try:
        return UUID(str(valor))
    except ValueError:
        raise MensajeInvalido(f"{campo} no es un uuid válido")


def interpretar(cuerpo):
    """Convierte el cuerpo del mensaje en un aviso listo para guardar, o lanza MensajeInvalido."""
    try:
        evento = json.loads(cuerpo)
    except ValueError:  # incluye JSON mal formado y bytes que no son UTF-8
        raise MensajeInvalido("el cuerpo no es JSON")
    if not isinstance(evento, dict):
        raise MensajeInvalido("el JSON debe ser un objeto")

    faltan = [c for c in CAMPOS if c not in evento]
    if faltan:
        raise MensajeInvalido("faltan campos: " + ", ".join(faltan))

    tipo = evento["tipo"]
    if tipo not in mensajes.TIPOS:
        raise MensajeInvalido(f"tipo de evento desconocido: {tipo}")

    version = evento["versionPedido"]
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise MensajeInvalido("versionPedido debe ser un entero mayor o igual a 1")

    datos = evento["datos"]
    if not isinstance(datos, dict):
        raise MensajeInvalido("datos debe ser un objeto")

    try:
        fecha = datetime.fromisoformat(str(evento["fecha"]).replace("Z", "+00:00"))
    except ValueError:
        raise MensajeInvalido("fecha no tiene formato ISO 8601")
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)

    return {
        "evento_id": _uuid(evento["eventoId"], "eventoId"),
        "pedido_id": _uuid(evento["pedidoId"], "pedidoId"),
        "usuario_id": _uuid(evento["usuarioId"], "usuarioId"),
        "tipo": tipo,
        "version_pedido": version,
        "fecha_evento": fecha,
        "mensaje": mensajes.texto(tipo, datos),
    }


def registrar_evento(cuerpo):
    """Guarda el aviso de un evento. Devuelve True si se guardó, False si era un duplicado.

    Si el mensaje es inválido lanza MensajeInvalido. Si la base falla, deja subir el error:
    el consumidor no confirma el mensaje y RabbitMQ lo vuelve a entregar.
    """
    aviso = interpretar(cuerpo)
    with db.conexion() as conn:
        return repositorio.guardar(conn, aviso) is not None


def avisos_de_usuario(usuario_id):
    with db.conexion() as conn:
        return repositorio.listar_por_usuario(conn, usuario_id)


def avisos_de_pedido(pedido_id):
    with db.conexion() as conn:
        return repositorio.listar_por_pedido(conn, pedido_id)


def ultimo_aviso(pedido_id):
    """Devuelve el aviso más reciente (mayor versión) o None si no hay."""
    with db.conexion() as conn:
        return repositorio.ultimo_de_pedido(conn, pedido_id)
