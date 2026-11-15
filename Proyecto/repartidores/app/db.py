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
        kwargs={"row_factory": dict_row},
        open=False,
    )
    _pool.open(wait=True, timeout=30)


def cerrar_pool():
    if _pool is not None:
        _pool.close()


@contextmanager
def conexion():
    """Una conexión dentro de una transacción: commit si todo sale bien, rollback si hay error."""
    with _pool.connection() as conn:
        yield conn
