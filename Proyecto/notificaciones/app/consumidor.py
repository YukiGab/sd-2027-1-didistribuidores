"""Consumidor de RabbitMQ: recibe los eventos de los pedidos y guarda los avisos.

Corre en un hilo aparte dentro del proceso de notificaciones.

Reglas que sigue con cada mensaje:
  1. Lo guarda en la base (si el evento ya estaba guardado, lo ignora).
  2. SOLO DESPUÉS de guardarlo hace ack, o sea, le dice a RabbitMQ "ya puedes borrarlo".
     Si el proceso se cae antes del ack, RabbitMQ vuelve a entregar el mensaje y el
     evento_id UNIQUE evita que se guarde dos veces.
  3. Si el mensaje no se puede interpretar, lo rechaza sin reencolar (nack, requeue=False)
     y RabbitMQ lo manda a la cola de mensajes fallidos. Así no bloquea a los demás.
  4. Si falla algo temporal (por ejemplo, la base de datos), cierra la conexión sin hacer ack:
     RabbitMQ devuelve los mensajes pendientes a la cola y el consumidor reintenta al reconectar.
"""
import logging
import threading

import pika

from app import config, servicio, topologia

logger = logging.getLogger("uvicorn.error")


class Consumidor(threading.Thread):
    def __init__(self):
        super().__init__(name="consumidor-notificaciones", daemon=True)
        self._parar = threading.Event()
        self._conexion = None
        self._canal = None
        self.conectado = False   # lo lee /salud

    def detener(self):
        """Pide que termine. Se llama desde otro hilo, por eso usa add_callback_threadsafe."""
        self._parar.set()
        conexion, canal = self._conexion, self._canal
        if conexion is not None and conexion.is_open and canal is not None:
            try:
                conexion.add_callback_threadsafe(canal.stop_consuming)
            except Exception:
                pass
        self.join(timeout=5)

    def run(self):
        while not self._parar.is_set():
            try:
                self._consumir()
            except Exception:
                logger.exception(
                    "Consumidor de notificaciones: error, se reintenta en %s s", config.REINTENTO_SEG
                )
            self.conectado = False
            if not self._parar.is_set():
                self._parar.wait(config.REINTENTO_SEG)

    def _consumir(self):
        self._conexion = pika.BlockingConnection(pika.URLParameters(config.RABBITMQ_URL))
        try:
            self._canal = self._conexion.channel()
            topologia.declarar(self._canal)
            self._canal.basic_qos(prefetch_count=10)  # a lo más 10 mensajes sin confirmar a la vez
            self._canal.basic_consume(queue=topologia.COLA, on_message_callback=self._al_recibir)
            self.conectado = True
            logger.info("Consumidor de notificaciones esperando eventos en %s", topologia.COLA)
            self._canal.start_consuming()
        finally:
            self.conectado = False
            try:
                if self._conexion.is_open:
                    self._conexion.close()   # lo que no tenga ack vuelve a la cola
            except Exception:
                pass

    def _al_recibir(self, canal, metodo, propiedades, cuerpo):
        try:
            guardado = servicio.registrar_evento(cuerpo)
        except servicio.MensajeInvalido as e:
            logger.warning("Mensaje inválido, se manda a la cola de fallidos: %s", e)
            canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
            return
        # Cualquier otro error (la base caída, por ejemplo) sube: corta la conexión sin ack
        # y el mensaje se reentrega. No se traga el error a propósito.
        if guardado:
            logger.info("Aviso guardado (mensaje %s)", propiedades.message_id)
        else:
            logger.info("Evento repetido, se ignora (mensaje %s)", propiedades.message_id)
        canal.basic_ack(delivery_tag=metodo.delivery_tag)
