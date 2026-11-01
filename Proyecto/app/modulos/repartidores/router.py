from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modulos.repartidores import servicio

router = APIRouter(prefix="/api/repartidores", tags=["repartidores"])


class RepartidorNuevo(BaseModel):
    nombre: str = Field(min_length=1)
    zona: int = Field(ge=1, le=5)


@router.post("", status_code=201)
def crear_repartidor(datos: RepartidorNuevo):
    return servicio.crear_repartidor(datos.nombre, datos.zona)


@router.get("/{repartidor_id}")
def obtener_repartidor(repartidor_id: UUID):
    repartidor = servicio.obtener_repartidor(repartidor_id)
    if repartidor is None:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado")
    return repartidor
