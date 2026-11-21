from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app import servicio

router = APIRouter(prefix="/api/repartidores", tags=["repartidores"])


class RepartidorNuevo(BaseModel):
    nombre: str = Field(min_length=1)
    zona: int = Field(ge=1, le=5)


class Disponibilidad(BaseModel):
    disponible: bool


@router.post("", status_code=201)
def crear_repartidor(datos: RepartidorNuevo):
    return servicio.crear_repartidor(datos.nombre, datos.zona)


@router.get("")
def listar_repartidores(zona: Optional[int] = Query(default=None, ge=1, le=5), disponible: Optional[bool] = None):
    """Lista los repartidores. Se puede filtrar por zona y por disponibilidad."""
    return servicio.listar_repartidores(zona, disponible)


@router.get("/{repartidor_id}")
def obtener_repartidor(repartidor_id: UUID):
    repartidor = servicio.obtener_repartidor(repartidor_id)
    if repartidor is None:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado")
    return repartidor


@router.patch("/{repartidor_id}")
def cambiar_disponibilidad(repartidor_id: UUID, datos: Disponibilidad):
    repartidor = servicio.cambiar_disponibilidad(repartidor_id, datos.disponible)
    if repartidor is None:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado")
    return repartidor
