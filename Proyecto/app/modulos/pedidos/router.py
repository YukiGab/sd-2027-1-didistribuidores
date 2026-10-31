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


@router.get("/{pedido_id}")
def obtener_pedido(pedido_id: UUID):
    return servicio.obtener_pedido(pedido_id)