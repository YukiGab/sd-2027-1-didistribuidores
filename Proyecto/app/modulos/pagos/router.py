from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.modulos.pagos import servicio

router = APIRouter(prefix="/api/pagos", tags=["pagos"])


@router.get("/{pedido_id}")
def obtener_pago(pedido_id: UUID):
    """Consulta el pago de un pedido (sirve para comprobar cobros y reembolsos)."""
    pago = servicio.obtener_pago(pedido_id)
    if pago is None:
        raise HTTPException(status_code=404, detail="Ese pedido no tiene pago")
    return pago
