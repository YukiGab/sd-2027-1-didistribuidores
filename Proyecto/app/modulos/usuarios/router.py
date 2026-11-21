# Capa HTTP: recibe la petición, llama al servicio y devuelve la respuesta.
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modulos.usuarios import servicio

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


class UsuarioNuevo(BaseModel):
    nombre: str = Field(min_length=1)
    zona: int = Field(ge=1, le=5)


@router.post("", status_code=201)
def crear_usuario(datos: UsuarioNuevo):
    return servicio.crear_usuario(datos.nombre, datos.zona)


@router.get("/{usuario_id}")
def obtener_usuario(usuario_id: UUID):
    usuario = servicio.obtener_usuario(usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario