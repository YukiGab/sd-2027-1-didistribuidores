from app import db
from app.modulos.restaurantes import repositorio


def listar_restaurantes():
    with db.conexion() as conn:
        return repositorio.listar(conn)


def obtener_restaurante(restaurante_id):
    """Devuelve el restaurante o None si no existe."""
    with db.conexion() as conn:
        return repositorio.obtener(conn, restaurante_id)


def listar_platillos(restaurante_id):
    with db.conexion() as conn:
        return repositorio.listar_platillos(conn, restaurante_id)