from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uuid

app = FastAPI(title="DiDistribuidores Monolito")

pedidos_db = {}

class Pedido(BaseModel):
    usuario_id: str
    restaurante_id: str
    items: List[str]
    total: float

@app.get("/")
def read_root():
    return {"mensaje": "Bienvenido al Monolito de DiDistribuidores"}

@app.post("/pedidos")
def crear_pedido(pedido: Pedido):
    pedido_id = str(uuid.uuid4())
    pedidos_db[pedido_id] = {"id": pedido_id, "estado": "PENDIENTE_PAGO", **pedido.dict()}
    return {"mensaje": "Pedido creado", "pedido": pedidos_db[pedido_id]}

@app.post("/pedidos/{pedido_id}/pagar")
def procesar_pago(pedido_id: str):
    if pedido_id not in pedidos_db:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedido = pedidos_db[pedido_id]
    if pedido["estado"] != "PENDIENTE_PAGO":
        raise HTTPException(status_code=400, detail="El pedido ya fue pagado")
    pedido["estado"] = "PAGADO"
    return {"mensaje": "Pago exitoso", "pedido": pedido}

@app.post("/pedidos/{pedido_id}/asignar")
def asignar_repartidor(pedido_id: str):
    if pedido_id not in pedidos_db:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedido = pedidos_db[pedido_id]
    if pedido["estado"] != "PAGADO":
        raise HTTPException(status_code=400, detail="El pedido no está pagado")
    pedido["estado"] = "ASIGNADO"
    return {"mensaje": "Repartidor asignado", "pedido": pedido}

@app.get("/pedidos/{pedido_id}")
def consultar_pedido(pedido_id: str):
    if pedido_id not in pedidos_db:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedidos_db[pedido_id]
