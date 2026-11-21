# Solo SQL de la base de repartidores.

COLUMNAS = "id, nombre, zona, disponible, creado_en"


def crear(conn, nombre, zona):
    return conn.execute(
        f"INSERT INTO repartidores (nombre, zona) VALUES (%s, %s) RETURNING {COLUMNAS}",
        (nombre, zona),
    ).fetchone()


def obtener(conn, repartidor_id):
    return conn.execute(
        f"SELECT {COLUMNAS} FROM repartidores WHERE id = %s",
        (repartidor_id,),
    ).fetchone()


def listar(conn, zona=None, disponible=None):
    """zona y disponible son filtros opcionales: None significa "no filtrar"."""
    condiciones, params = [], []
    if zona is not None:
        condiciones.append("zona = %s")
        params.append(zona)
    if disponible is not None:
        condiciones.append("disponible = %s")
        params.append(disponible)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    return conn.execute(
        f"SELECT {COLUMNAS} FROM repartidores {donde} ORDER BY nombre",
        params,
    ).fetchall()


def cambiar_disponibilidad(conn, repartidor_id, disponible):
    return conn.execute(
        f"UPDATE repartidores SET disponible = %s WHERE id = %s RETURNING {COLUMNAS}",
        (disponible, repartidor_id),
    ).fetchone()
