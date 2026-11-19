"""Cliente HTTP del servicio de repartidores.

Etapa 3: tiempo límite (1 s para conectar, 3 s para leer) y 503 si no responde.
Etapa 4: se agregan, en capas, un reintento seguro y un circuit breaker.

   circuit breaker  ->  reintento (máx. 1, solo si es seguro)  ->  tiempo límite  ->  llamada HTTP

Regla de diseño: el registro de repartidores INFORMA (quién es y en qué zona está);
la decisión de quién gana un pedido sigue en pedidos.
"""
import logging
import random
import socket
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as TiempoAgotado
from urllib.parse import urlsplit

import httpx

from app import config
from app.errores import ServicioNoDisponible
from app.resiliencia import CircuitBreaker, CircuitoAbierto

logger = logging.getLogger("uvicorn.error")

_breaker = CircuitBreaker(
    "repartidores", fallos_maximos=config.BREAKER_FALLOS, pausa_seg=config.BREAKER_PAUSA_SEG
)

_URL = urlsplit(config.REPARTIDORES_URL)
_PUERTO = _URL.port or (443 if _URL.scheme == "https" else 80)
# La resolución del nombre corre en estos hilos para poder ponerle tiempo límite (ver _resolver)
_resolutor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="dns-repartidores")


class _SinNombre(Exception):
    """El nombre del servicio no se resolvió: no hay copias vivas o el DNS no contestó a tiempo."""


def _resolver():
    """Resuelve el nombre del servicio con el MISMO tiempo límite de conexión y devuelve una IP.

    El tiempo límite de httpx no cubre la resolución del nombre: con repartidores detenido, el DNS
    de Docker Desktop tarda unos 4 s en decir que el nombre no existe, y la llamada esperaba eso
    (8 s con el reintento) aunque el límite fuera de 1 s para conectar. Medido en la prueba 4.
    """
    futuro = _resolutor.submit(socket.getaddrinfo, _URL.hostname, _PUERTO, type=socket.SOCK_STREAM)
    try:
        direcciones = futuro.result(timeout=config.REPARTIDORES_CONNECT_TIMEOUT_SEG)
    except TiempoAgotado:
        raise _SinNombre("el DNS no contestó a tiempo")
    except socket.gaierror as e:
        raise _SinNombre(str(e))
    return direcciones[0][4][0]   # el DNS de Docker devuelve las copias en orden variable


def _cliente(ip):
    # Un cliente nuevo por llamada: sin conexiones guardadas, cada llamada vuelve a resolver
    # el nombre "repartidores" en el DNS de Docker y puede caer en otra copia del servicio.
    host = f"[{ip}]" if ":" in ip else ip
    return httpx.Client(
        base_url=f"{_URL.scheme}://{host}:{_PUERTO}",
        headers={"Host": _URL.netloc},
        timeout=httpx.Timeout(config.REPARTIDORES_TIMEOUT_SEG, connect=config.REPARTIDORES_CONNECT_TIMEOUT_SEG),
    )


def _pausa():
    """Pausa corta y aleatoria (jitter) antes de reintentar: si muchas peticiones fallan a la
    vez, no vuelven todas en el mismo instante."""
    time.sleep(random.uniform(0.05, 0.15))


def _consultar(repartidor_id):
    """Una consulta con, a lo más, REPARTIDORES_REINTENTOS reintentos seguros.

    Devuelve el repartidor (dict) o None si no existe. Lanza ServicioNoDisponible si falla.

    Cuándo se reintenta (la llamada es de SOLO LECTURA, así que repetirla es inofensiva):
      - No se pudo conectar (rechazada o tiempo de conexión): la petición nunca se envió.
      - El servicio contestó 502, 503 o 504 ("no pude atenderte ahora").
    Cuándo NO: el nombre no se resuelve (no hay ninguna copia viva: reintentar solo duplica la
    espera), tiempo de lectura agotado (ya se esperó lo máximo), 500 u otros errores, y 404
    (es una respuesta válida).
    """
    intentos = 1 + config.REPARTIDORES_REINTENTOS
    for intento in range(1, intentos + 1):
        ultimo = intento == intentos
        try:
            ip = _resolver()
        except _SinNombre as e:
            logger.warning("[repartidores] el nombre no se resuelve (%s)", e)
            raise ServicioNoDisponible("El servicio de repartidores no responde. Intenta de nuevo en unos segundos")
        try:
            with _cliente(ip) as http:
                respuesta = http.get(f"/api/repartidores/{repartidor_id}")
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            if not ultimo:
                logger.warning("[repartidores] reintento tras %s", type(e).__name__)
                _pausa()
                continue
            logger.warning("[repartidores] sin conexión (%s: %s)", type(e).__name__, e)
            raise ServicioNoDisponible("El servicio de repartidores no responde. Intenta de nuevo en unos segundos")
        except httpx.HTTPError as e:   # tiempo de lectura agotado, conexión cortada a la mitad, etc.
            logger.warning("[repartidores] sin respuesta a tiempo (%s: %s)", type(e).__name__, e)
            raise ServicioNoDisponible("El servicio de repartidores no responde. Intenta de nuevo en unos segundos")

        if respuesta.status_code == 404:
            return None
        if respuesta.status_code in (502, 503, 504) and not ultimo:
            logger.warning("[repartidores] reintento tras respuesta %s", respuesta.status_code)
            _pausa()
            continue
        if respuesta.status_code != 200:
            logger.warning("[repartidores] respondió %s", respuesta.status_code)
            raise ServicioNoDisponible("El servicio de repartidores respondió con un error")
        try:
            return respuesta.json()
        except ValueError:
            raise ServicioNoDisponible("El servicio de repartidores respondió algo ilegible")


def obtener(repartidor_id):
    """Devuelve el repartidor como diccionario (id, nombre, zona, disponible), o None si no existe.

    Lanza ServicioNoDisponible si el servicio no responde, o si el circuit breaker está abierto
    (en ese caso ni siquiera se llama). NO adivina: si no puede saber quién es, no sigue.

    Para el breaker, un 404 cuenta como ÉXITO: el servicio contestó bien; que el repartidor
    no exista es una respuesta, no una falla.
    """
    try:
        _breaker.antes_de_llamar()
    except CircuitoAbierto:
        raise ServicioNoDisponible(
            "El servicio de repartidores no está disponible (circuito abierto). Intenta de nuevo en unos segundos"
        )
    try:
        resultado = _consultar(repartidor_id)
    except BaseException:
        _breaker.fallo()
        raise
    _breaker.exito()
    return resultado


def estado_circuito():
    return _breaker.estado_actual()
