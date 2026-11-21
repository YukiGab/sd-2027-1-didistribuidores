# Capa de servicio: las reglas del módulo. Es lo único que otros módulos pueden llamar.
from app import db
from app.modulos.usuarios import repositorio


def crear_usuario(nombre, zona):
    with db.conexion() as conn:
        return repositorio.crear(conn, nombre, zona)


def obtener_usuario(usuario_id):
    """Devuelve el usuario o None si no existe."""
    with db.conexion() as conn:
        return repositorio.obtener(conn, usuario_id)