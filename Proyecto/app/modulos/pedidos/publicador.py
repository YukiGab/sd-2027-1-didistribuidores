"""Publicador del outbox: lee los eventos pendientes de pedidos.outbox y los manda a RabbitMQ.

Corre en un hilo aparte dentro del proceso del núcleo. Garantía: AL MENOS UNA VEZ.
Un evento solo se marca como publicado (publicado_en) después de que RabbitMQ confirmó
que lo recibió y lo guardó. Si el proceso se cae justo entre publicar y marcar, el evento se
vuelve a publicar: por eso el consumidor (notificaciones) ignora los duplicados por eventoId.
"""
import json
import logging
import threading

import pika

from app import config, db
from app.modulos.pedidos import topologia

logger = logging.getLogger("uvicorn.error")


class Publicador(threading.Thread):
    def __init__(self):
        super().__init__(name="publicador-outbox", daemon=True)
        self._parar = threading.Event()

    def detener(self):
        self._parar.set()
        self.join(timeout=5)

    def run(self):
        while not self._parar.is_set():
            try:
                self._conectar_y_publicar()
            except Exception:
                logger.exception(
                    "Publicador del outbox: error, se reintenta en %s s", config.REINTENTO_SEG
                )
                self._parar.wait(config.REINTENTO_SEG)

    def _conectar_y_publicar(self):
        conexion = pika.BlockingConnection(pika.URLParameters(config.RABBITMQ_URL))
        try:
            canal = conexion.channel()
            canal.confirm_delivery()        # RabbitMQ confirma cada mensaje; si no lo acepta, lanza error
            topologia.declarar(canal)
            logger.info("Publicador del outbox conectado a RabbitMQ")
            while not self._parar.is_set():
                if self._publicar_lote(canal) == 0:
                    # connection.sleep (y no time.sleep) sigue atendiendo los latidos de la conexión
                    conexion.sleep(config.PUBLICADOR_INTERVALO_SEG)
        finally:
            try:
                if conexion.is_open:
                    conexion.close()
            except Exception:
                pass

    def _publicar_lote(self, canal):
        """Publica hasta PUBLICADOR_LOTE eventos pendientes. Devuelve cuántos publicó."""
        publicados = []
        error = None
        with db.conexion() as conn:
            # SKIP LOCKED: si hubiera dos copias del núcleo, cada una toma eventos distintos
            filas = conn.execute(
                """
                SELECT id, tipo, payload
                FROM pedidos.outbox
                WHERE publicado_en IS NULL
                ORDER BY creado_en
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                (config.PUBLICADOR_LOTE,),
            ).fetchall()

            for fila in filas:
                try:
                    canal.basic_publish(
                        exchange=topologia.EXCHANGE,
                        routing_key=fila["tipo"],
                        body=json.dumps(fila["payload"]).encode("utf-8"),
                        properties=pika.BasicProperties(
                            content_type="application/json",
                            delivery_mode=2,  # persistente: sobrevive a un reinicio de RabbitMQ
                            message_id=str(fila["id"]),
                            type=fila["tipo"],
                        ),
                        mandatory=True,       # si ninguna cola lo recibe, es un error (no se pierde en silencio)
                    )
                    publicados.append(fila["id"])
                except Exception as e:
                    error = e
                    break

            # Se marcan los que sí salieron, aunque el lote haya fallado a la mitad
            if publicados:
                conn.execute(
                    "UPDATE pedidos.outbox SET publicado_en = now() WHERE id = ANY(%s)",
                    (publicados,),
                )

        if error is not None:
            raise error
        return len(publicados)
