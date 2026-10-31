from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.modulos.restaurantes.router import router as restaurantes_router
from app.modulos.usuarios.router import router as usuarios_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.abrir_pool()   # al arrancar
    yield
    db.cerrar_pool()  # al apagar


app = FastAPI(title="DiDistribuidores - Núcleo", lifespan=lifespan)

# main.py es el único archivo que conoce todos los módulos
app.include_router(usuarios_router)
app.include_router(restaurantes_router)


@app.get("/salud")
def salud():
    with db.conexion() as conn:
        conn.execute("SELECT 1")
    return {"estado": "ok"}