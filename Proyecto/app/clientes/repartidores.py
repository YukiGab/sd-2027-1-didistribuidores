"""Cliente HTTP del servicio de repartidores.

Desde la etapa 3, repartidores es un servicio aparte: el núcleo ya no lee su base ni importa su
código. Solo le pregunta por HTTP, con un tiempo límite, y decide qué hacer si no responde.

Regla de diseño (la misma que "la caché muestra, nunca decide"): el registro de repartidores
INFORMA (quién es y en qué zona está); la decisión de quién gana un pedido sigue en pedidos.
"""
import logging

import httpx

from app import config
from app.errores import ServicioNoDisponible

logger = logging.getLogger("uvicorn.error")


def _cliente():
    # Un cliente nuevo por llamada: sin conexiones guardadas, así cada llamada vuelve a resolver
    # el nombre "repartidores" en el DNS de Docker y puede caer en otra copia del servicio.
    return httpx.Client(
        base_url=config.REPARTIDORES_URL,
        timeout=httpx.Timeout(config.REPARTIDORES_TIMEOUT_SEG, connect=config.REPARTIDORES_CONNECT_TIMEOUT_SEG),
    )


def obtener(repartidor_id):
    """Devuelve el repartidor como diccionario (id, nombre, zona, disponible), o None si no existe.

    Lanza ServicioNoDisponible si el servicio no responde a tiempo, rechaza la conexión o
    contesta algo inesperado. NO adivina: si no puede saber quién es el repartidor, no sigue.
    """
    try:
        with _cliente() as http:
            respuesta = http.get(f"/api/repartidores/{repartidor_id}")
    except httpx.HTTPError as e:  # timeout, conexión rechazada, DNS, etc.
        logger.warning("[repartidores] sin respuesta (%s: %s)", type(e).__name__, e)
        raise ServicioNoDisponible("El servicio de repartidores no responde. Intenta de nuevo en unos segundos")

    if respuesta.status_code == 404:
        return None
    if respuesta.status_code != 200:
        logger.warning("[repartidores] respondió %s", respuesta.status_code)
        raise ServicioNoDisponible("El servicio de repartidores respondió con un error")
    try:
        return respuesta.json()
    except ValueError:
        raise ServicioNoDisponible("El servicio de repartidores respondió algo ilegible")
