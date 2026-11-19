"""Circuit breaker (cortacircuitos) hecho a mano.

Idea: si un servicio al que llamamos falla varias veces SEGUIDAS, seguir llamándolo solo
desperdicia tiempo (cada llamada espera su tiempo límite) y lo ahoga más. Entonces el breaker
"se abre": durante una pausa rechaza las llamadas al instante, sin intentarlas. Pasada la pausa
deja pasar UNA llamada de prueba; si sale bien se cierra, si falla se vuelve a abrir.

Estados:
  CERRADO     todo normal; cada fallo suma uno, un éxito reinicia la cuenta.
  ABIERTO     demasiados fallos seguidos; rechaza sin llamar.
  SEMIABIERTO pasó la pausa; deja pasar una sola llamada de prueba.

Es seguro entre hilos (el núcleo atiende peticiones en varios hilos) y recibe el reloj como
parámetro para poder probarlo con un reloj falso, sin esperar segundos reales.
"""
import logging
import threading
import time

logger = logging.getLogger("uvicorn.error")

CERRADO = "CERRADO"
ABIERTO = "ABIERTO"
SEMIABIERTO = "SEMIABIERTO"


class CircuitoAbierto(Exception):
    """El breaker rechazó la llamada sin intentarla."""


class CircuitBreaker:
    def __init__(self, nombre, fallos_maximos=3, pausa_seg=10.0, reloj=time.monotonic):
        self.nombre = nombre
        self.fallos_maximos = fallos_maximos
        self.pausa_seg = pausa_seg
        self._reloj = reloj
        self._lock = threading.Lock()
        self._estado = CERRADO
        self._fallos = 0
        self._abierto_en = None
        self._prueba_en_curso = False

    # ------------------------------------------------------------------ uso
    def antes_de_llamar(self):
        """Se llama antes de cada llamada. Lanza CircuitoAbierto si no se debe llamar."""
        with self._lock:
            if self._estado == ABIERTO:
                if self._reloj() - self._abierto_en >= self.pausa_seg:
                    self._cambiar(SEMIABIERTO, "pasó la pausa, se deja pasar una llamada de prueba")
                    self._prueba_en_curso = True   # ESTA llamada es la de prueba
                    return
                raise CircuitoAbierto(self.nombre)
            if self._estado == SEMIABIERTO:
                if self._prueba_en_curso:
                    raise CircuitoAbierto(self.nombre)   # ya hay una prueba: las demás esperan
                self._prueba_en_curso = True

    def exito(self):
        with self._lock:
            self._fallos = 0
            self._prueba_en_curso = False
            if self._estado != CERRADO:
                self._cambiar(CERRADO, "la llamada de prueba salió bien")

    def fallo(self):
        with self._lock:
            self._prueba_en_curso = False
            if self._estado == SEMIABIERTO:
                self._abrir("la llamada de prueba falló")
                return
            if self._estado == CERRADO:
                self._fallos += 1
                if self._fallos >= self.fallos_maximos:
                    self._abrir(f"{self._fallos} fallos seguidos")

    def estado_actual(self):
        """Para GET /estado."""
        with self._lock:
            desde = None
            if self._estado != CERRADO and self._abierto_en is not None:
                desde = round(self._reloj() - self._abierto_en, 1)
            return {"circuito": self._estado, "fallos_seguidos": self._fallos, "abierto_desde_hace_seg": desde}

    # ------------------------------------------------------------ internos
    def _abrir(self, motivo):
        self._abierto_en = self._reloj()
        self._cambiar(ABIERTO, motivo)

    def _cambiar(self, nuevo, motivo):
        logger.warning("[circuito %s] %s -> %s (%s)", self.nombre, self._estado, nuevo, motivo)
        self._estado = nuevo
