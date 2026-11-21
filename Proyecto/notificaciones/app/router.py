from uuid import UUID

from fastapi import APIRouter, HTTPException

from app import servicio

router = APIRouter(prefix="/api/notificaciones", tags=["notificaciones"])


@router.get("")
def avisos_de_usuario(usuario_id: UUID):
    """Los avisos de un cliente, del más reciente al más antiguo."""
    return servicio.avisos_de_usuario(usuario_id)


@router.get("/pedido/{pedido_id}")
def avisos_de_pedido(pedido_id: UUID):
    """Todos los avisos de un pedido, ordenados por la versión del pedido."""
    return servicio.avisos_de_pedido(pedido_id)


@router.get("/pedido/{pedido_id}/ultimo")
def ultimo_aviso(pedido_id: UUID):
    """El aviso del estado más reciente del pedido (el de mayor versión)."""
    aviso = servicio.ultimo_aviso(pedido_id)
    if aviso is None:
        raise HTTPException(status_code=404, detail="Ese pedido no tiene avisos")
    return aviso
