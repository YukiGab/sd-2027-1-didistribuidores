from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app import config

_pool = None


def abrir_pool():
    """Crea el pool de conexiones. Espera hasta 30 s a que Postgres esté listo."""
    global _pool
    _pool = ConnectionPool(
        conninfo=config.DB_CONNINFO,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row},  # las filas llegan como diccionarios
        open=False,
    )
    _pool.open(wait=True, timeout=30)


def cerrar_pool():
    if _pool is not None:
        _pool.close()


@contextmanager
def conexion():
    """Da una conexión del pool dentro de una transacción.

    Si el bloque termina bien, hace commit. Si lanza una excepción, hace rollback.
    Todo lo que se haga dentro de un mismo 'with' es una sola transacción.
    """
    with _pool.connection() as conn:
        yield conn