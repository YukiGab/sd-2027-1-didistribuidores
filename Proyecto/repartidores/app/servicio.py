from app import db, repositorio


def crear_repartidor(nombre, zona):
    with db.conexion() as conn:
        return repositorio.crear(conn, nombre, zona)


def obtener_repartidor(repartidor_id):
    """Devuelve el repartidor o None si no existe."""
    with db.conexion() as conn:
        return repositorio.obtener(conn, repartidor_id)


def listar_repartidores(zona=None, disponible=None):
    with db.conexion() as conn:
        return repositorio.listar(conn, zona, disponible)


def cambiar_disponibilidad(repartidor_id, disponible):
    """Devuelve el repartidor actualizado o None si no existe."""
    with db.conexion() as conn:
        return repositorio.cambiar_disponibilidad(conn, repartidor_id, disponible)
