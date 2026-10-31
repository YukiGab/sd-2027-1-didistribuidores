COLUMNAS = """id, usuario_id, restaurante_id, zona, estado, motivo_cancelacion, total,
              clave_idempotencia, repartidor_id, codigo_entrega, version,
              creado_en, actualizado_en"""


def insertar_si_no_existe(conn, usuario_id, restaurante_id, zona, total, clave, codigo):
    """Inserta el pedido. Si ya existe uno con la misma (usuario, clave), no inserta
    nada y devuelve None. La restricción UNIQUE de la base es lo que lo decide, de forma
    atómica: si dos peticiones llegan a la vez, la segunda espera a que la primera termine."""
    return conn.execute(
        f"""
        INSERT INTO pedidos.pedidos
            (usuario_id, restaurante_id, zona, total, clave_idempotencia, codigo_entrega)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (usuario_id, clave_idempotencia) DO NOTHING
        RETURNING {COLUMNAS}
        """,
        (usuario_id, restaurante_id, zona, total, clave, codigo),
    ).fetchone()


def insertar_platillos(conn, pedido_id, filas):
    """filas: lista de (platillo_id, cantidad, precio_unitario)."""
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO pedidos.pedido_platillos
                (pedido_id, platillo_id, cantidad, precio_unitario)
            VALUES (%s, %s, %s, %s)
            """,
            [(pedido_id, pid, cant, precio) for pid, cant, precio in filas],
        )


def buscar_por_clave(conn, usuario_id, clave):
    return conn.execute(
        f"""
        SELECT {COLUMNAS} FROM pedidos.pedidos
        WHERE usuario_id = %s AND clave_idempotencia = %s
        """,
        (usuario_id, clave),
    ).fetchone()


def obtener(conn, pedido_id):
    return conn.execute(
        f"SELECT {COLUMNAS} FROM pedidos.pedidos WHERE id = %s",
        (pedido_id,),
    ).fetchone()


def listar_platillos(conn, pedido_id):
    return conn.execute(
        """
        SELECT platillo_id, cantidad, precio_unitario
        FROM pedidos.pedido_platillos
        WHERE pedido_id = %s
        """,
        (pedido_id,),
    ).fetchall()