import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.consumidor import Consumidor
from app.router import router as notificaciones_router

consumidor = Consumidor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.abrir_pool()
    consumidor.start()   # empieza a escuchar la cola de RabbitMQ
    yield
    await asyncio.to_thread(consumidor.detener)
    db.cerrar_pool()


app = FastAPI(title="DiDistribuidores - Notificaciones", lifespan=lifespan)
app.include_router(notificaciones_router)


@app.get("/salud")
def salud():
    with db.conexion() as conn:
        conn.execute("SELECT 1")
    return {"estado": "ok", "consumidor_conectado": consumidor.conectado}
