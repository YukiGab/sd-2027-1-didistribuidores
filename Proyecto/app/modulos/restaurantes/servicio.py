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


def obtener_platillos(restaurante_id, ids):
    """Los platillos disponibles de ese restaurante entre los ids dados.
    Si falta alguno de los ids en el resultado, no existe o no está disponible."""
    with db.conexion() as conn:
        return repositorio.platillos_por_ids(conn, restaurante_id, ids)