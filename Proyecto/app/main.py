import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import config, db
from app.errores import Conflicto, Invalido, NoEncontrado, ServicioNoDisponible
from app.modulos.pagos.router import router as pagos_router
from app.modulos.pedidos import servicio as pedidos_servicio
from app.modulos.pedidos.publicador import Publicador
from app.modulos.pedidos.router import router as pedidos_router
from app.modulos.restaurantes.router import router as restaurantes_router
from app.modulos.usuarios.router import router as usuarios_router

logger = logging.getLogger("uvicorn.error")


async def _vigilar_timeouts():
    """Tarea en segundo plano: cada pocos segundos avisa los retrasos y cancela los pedidos vencidos."""
    while True:
        try:
            retrasados = await asyncio.to_thread(pedidos_servicio.avisar_retrasados)
            if retrasados:
                logger.info("Retrasos: %s pedido(s) avisado(s) de retraso", retrasados)
            cancelados = await asyncio.to_thread(pedidos_servicio.cancelar_vencidos)
            if cancelados:
                logger.info("Timeouts: %s pedido(s) cancelado(s)", cancelados)
        except Exception:
            logger.exception("Error al revisar los timeouts")
        await asyncio.sleep(config.REVISION_TIMEOUTS_SEG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.abrir_pool()   # al arrancar
    tarea = asyncio.create_task(_vigilar_timeouts())
    publicador = None
    if config.PUBLICADOR_ACTIVO:
        publicador = Publicador()
        publicador.start()
    yield
    if publicador is not None:   # al apagar
        await asyncio.to_thread(publicador.detener)
    tarea.cancel()
    with suppress(asyncio.CancelledError):
        await tarea
    db.cerrar_pool()


app = FastAPI(title="DiDistribuidores - Núcleo", lifespan=lifespan)


def _registrar_errores(app):
    """Convierte los errores de negocio de los servicios en respuestas HTTP."""
    for clase, codigo in ((NoEncontrado, 404), (Invalido, 422), (Conflicto, 409), (ServicioNoDisponible, 503)):

        async def manejador(request, exc, codigo=codigo):
            return JSONResponse(status_code=codigo, content={"detail": exc.mensaje})

        app.add_exception_handler(clase, manejador)


_registrar_errores(app)

# main.py es el único archivo que conoce todos los módulos
app.include_router(usuarios_router)
app.include_router(restaurantes_router)
app.include_router(pedidos_router)
app.include_router(pagos_router)


@app.get("/salud")
def salud():
    with db.conexion() as conn:
        conn.execute("SELECT 1")
    return {"estado": "ok"}
