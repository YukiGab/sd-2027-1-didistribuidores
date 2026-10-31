from app import db
from app.modulos.repartidores import repositorio


def crear_repartidor(nombre, zona):
    with db.conexion() as conn:
        return repositorio.crear(conn, nombre, zona)


def obtener_repartidor(repartidor_id):
    """Devuelve el repartidor o None si no existe."""
    with db.conexion() as conn:
        return repositorio.obtener(conn, repartidor_id)
