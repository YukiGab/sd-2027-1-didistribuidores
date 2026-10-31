from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.modulos.restaurantes import servicio

router = APIRouter(prefix="/api/restaurantes", tags=["restaurantes"])


@router.get("")
def listar_restaurantes():
    return servicio.listar_restaurantes()


@router.get("/{restaurante_id}/platillos")
def listar_platillos(restaurante_id: UUID):
    if servicio.obtener_restaurante(restaurante_id) is None:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")
    return servicio.listar_platillos(restaurante_id)