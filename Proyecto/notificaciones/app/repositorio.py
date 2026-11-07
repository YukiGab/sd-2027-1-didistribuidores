# Solo SQL de la base de notificaciones.

COLUMNAS = "id, evento_id, pedido_id, usuario_id, tipo, version_pedido, mensaje, fecha_evento, recibido_en"


def guardar(conn, aviso):
    """Guarda el aviso. Si ya existía uno con el mismo evento_id (evento repetido),
    no hace nada y devuelve None. Es lo que vuelve idempotente al consumidor."""
    return conn.execute(
        """
        INSERT INTO avisos
            (evento_id, pedido_id, usuario_id, tipo, version_pedido, mensaje, fecha_evento)
        VALUES (%(evento_id)s, %(pedido_id)s, %(usuario_id)s, %(tipo)s,
                %(version_pedido)s, %(mensaje)s, %(fecha_evento)s)
        ON CONFLICT (evento_id) DO NOTHING
        RETURNING id
        """,
        aviso,
    ).fetchone()


def listar_por_usuario(conn, usuario_id):
    return conn.execute(
        f"""
        SELECT {COLUMNAS} FROM avisos
        WHERE usuario_id = %s
        ORDER BY fecha_evento DESC, version_pedido DESC
        """,
        (usuario_id,),
    ).fetchall()


def listar_por_pedido(conn, pedido_id):
    return conn.execute(
        f"SELECT {COLUMNAS} FROM avisos WHERE pedido_id = %s ORDER BY version_pedido",
        (pedido_id,),
    ).fetchall()


def ultimo_de_pedido(conn, pedido_id):
    """El aviso con la versión más alta: el estado más reciente que conocemos del pedido."""
    return conn.execute(
        f"""
        SELECT {COLUMNAS} FROM avisos
        WHERE pedido_id = %s
        ORDER BY version_pedido DESC
        LIMIT 1
        """,
        (pedido_id,),
    ).fetchone()
