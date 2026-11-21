def listar(conn):
    return conn.execute(
        "SELECT id, nombre, zona FROM restaurantes.restaurantes ORDER BY nombre"
    ).fetchall()


def obtener(conn, restaurante_id):
    return conn.execute(
        "SELECT id, nombre, zona FROM restaurantes.restaurantes WHERE id = %s",
        (restaurante_id,),
    ).fetchone()


def listar_platillos(conn, restaurante_id):
    return conn.execute(
        """
        SELECT id, nombre, precio
        FROM restaurantes.platillos
        WHERE restaurante_id = %s AND disponible
        ORDER BY nombre
        """,
        (restaurante_id,),
    ).fetchall()


def platillos_por_ids(conn, restaurante_id, ids):
    """Los platillos disponibles de ese restaurante cuyo id esté en la lista."""
    return conn.execute(
        """
        SELECT id, nombre, precio
        FROM restaurantes.platillos
        WHERE restaurante_id = %s AND disponible AND id = ANY(%s)
        """,
        (restaurante_id, list(ids)),
    ).fetchall()