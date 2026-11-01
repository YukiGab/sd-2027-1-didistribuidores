def crear(conn, nombre, zona):
    return conn.execute(
        """
        INSERT INTO repartidores.repartidores (nombre, zona)
        VALUES (%s, %s)
        RETURNING id, nombre, zona, disponible
        """,
        (nombre, zona),
    ).fetchone()


def obtener(conn, repartidor_id):
    return conn.execute(
        "SELECT id, nombre, zona, disponible FROM repartidores.repartidores WHERE id = %s",
        (repartidor_id,),
    ).fetchone()
