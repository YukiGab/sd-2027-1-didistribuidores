from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field

from app.modulos.pedidos import servicio

router = APIRouter(prefix="/api/pedidos", tags=["pedidos"])


class ItemPedido(BaseModel):
    platillo_id: UUID
    cantidad: int = Field(ge=1)


class PedidoNuevo(BaseModel):
    usuario_id: UUID
    restaurante_id: UUID
    platillos: List[ItemPedido] = Field(min_length=1)


@router.post("", status_code=201)
def crear_pedido(
    datos: PedidoNuevo,
    response: Response,
    idempotency_key: Optional[str] = Header(default=None),
):
    if idempotency_key is None or not idempotency_key.strip():
        raise HTTPException(status_code=400, detail="Falta el header Idempotency-Key")

    items = [(i.platillo_id, i.cantidad) for i in datos.platillos]
    pedido, creado = servicio.crear_pedido(
        idempotency_key.strip(), datos.usuario_id, datos.restaurante_id, items
    )
    if not creado:
        response.status_code = 200  # reintento: mismo pedido, no se creó otro
    return pedido


# Esta ruta va ANTES de "/{pedido_id}", si no FastAPI intentaría leer "disponibles" como un id
@router.get("/disponibles")
def pedidos_disponibles(repartidor_id: UUID):
    """Pedidos PAGADO sin repartidor de la zona del repartidor."""
    return servicio.listar_disponibles(repartidor_id)


@router.get("/{pedido_id}")
def obtener_pedido(pedido_id: UUID):
    return servicio.obtener_pedido(pedido_id)


@router.post("/{pedido_id}/pago")
def pagar_pedido(pedido_id: UUID):
    pedido, _ = servicio.pagar_pedido(pedido_id)
    return pedido


class Aceptacion(BaseModel):
    repartidor_id: UUID


@router.post("/{pedido_id}/aceptar")
def aceptar_pedido(pedido_id: UUID, datos: Aceptacion):
    pedido, _ = servicio.aceptar_pedido(pedido_id, datos.repartidor_id)
    return pedido


class Entrega(BaseModel):
    codigo: str = Field(min_length=1)


@router.post("/{pedido_id}/entrega")
def entregar_pedido(pedido_id: UUID, datos: Entrega):
    pedido, _ = servicio.entregar_pedido(pedido_id, datos.codigo.strip())
    return pedido
