import asyncio
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config, db
from app.router import router as repartidores_router

# Con varias copias del servicio, este nombre (el id del contenedor) dice cuál contestó.
INSTANCIA = socket.gethostname()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.abrir_pool()
    yield
    db.cerrar_pool()


app = FastAPI(title="DiDistribuidores - Repartidores", lifespan=lifespan)
app.include_router(repartidores_router)


@app.middleware("http")
async def marcar_instancia(request, call_next):
    # Solo para pruebas del tiempo límite: LATENCIA_MS=0 en uso normal. /salud no se retrasa,
    # para que el gateway no marque la copia como caída.
    if config.LATENCIA_MS and request.url.path != "/salud":
        await asyncio.sleep(config.LATENCIA_MS / 1000)
    respuesta = await call_next(request)
    respuesta.headers["X-Instancia"] = INSTANCIA
    return respuesta


@app.get("/salud")
def salud():
    with db.conexion() as conn:
        conn.execute("SELECT 1")
    return {"estado": "ok", "instancia": INSTANCIA}
