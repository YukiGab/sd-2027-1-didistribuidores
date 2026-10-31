from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import db
from app.errores import Conflicto, Invalido, NoEncontrado
from app.modulos.pagos.router import router as pagos_router
from app.modulos.pedidos.router import router as pedidos_router
from app.modulos.repartidores.router import router as repartidores_router
from app.modulos.restaurantes.router import router as restaurantes_router
from app.modulos.usuarios.router import router as usuarios_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.abrir_pool()   # al arrancar
    yield
    db.cerrar_pool()  # al apagar


app = FastAPI(title="DiDistribuidores - Núcleo", lifespan=lifespan)


def _registrar_errores(app):
    """Convierte los errores de negocio de los servicios en respuestas HTTP."""
    for clase, codigo in ((NoEncontrado, 404), (Invalido, 422), (Conflicto, 409)):

        async def manejador(request, exc, codigo=codigo):
            return JSONResponse(status_code=codigo, content={"detail": exc.mensaje})

        app.add_exception_handler(clase, manejador)


_registrar_errores(app)

# main.py es el único archivo que conoce todos los módulos
app.include_router(usuarios_router)
app.include_router(restaurantes_router)
app.include_router(pedidos_router)
app.include_router(pagos_router)
app.include_router(repartidores_router)


@app.get("/salud")
def salud():
    with db.conexion() as conn:
        conn.execute("SELECT 1")
    return {"estado": "ok"}
