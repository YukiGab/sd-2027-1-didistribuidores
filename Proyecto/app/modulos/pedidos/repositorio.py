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


def cambiar_estado(conn, pedido_id, desde, hacia):
    """Cambia el estado SOLO si el pedido sigue en el estado 'desde'.
    Devuelve el pedido actualizado, o None si no estaba en ese estado.
    Es la pieza que evita el problema de revisar y luego cambiar (TOCTOU):
    la revisión y el cambio ocurren en una sola instrucción."""
    return conn.execute(
        f"""
        UPDATE pedidos.pedidos
        SET estado = %s, version = version + 1, actualizado_en = now()
        WHERE id = %s AND estado = %s
        RETURNING {COLUMNAS}
        """,
        (hacia, pedido_id, desde),
    ).fetchone()


def listar_pagados_por_zona(conn, zona):
    return conn.execute(
        f"""
        SELECT {COLUMNAS} FROM pedidos.pedidos
        WHERE estado = 'PAGADO' AND repartidor_id IS NULL AND zona = %s
        ORDER BY actualizado_en
        """,
        (zona,),
    ).fetchall()


def asignar(conn, pedido_id, repartidor_id):
    """Gana el primero que llegue: el UPDATE solo cambia la fila si sigue PAGADO y sin
    repartidor. Al segundo le devuelve None."""
    return conn.execute(
        f"""
        UPDATE pedidos.pedidos
        SET estado = 'ASIGNADO', repartidor_id = %s,
            version = version + 1, actualizado_en = now()
        WHERE id = %s AND estado = 'PAGADO' AND repartidor_id IS NULL
        RETURNING {COLUMNAS}
        """,
        (repartidor_id, pedido_id),
    ).fetchone()


def confirmar_entrega(conn, pedido_id, codigo):
    """Pasa a ENTREGADO solo si el pedido está ASIGNADO y el código coincide."""
    return conn.execute(
        f"""
        UPDATE pedidos.pedidos
        SET estado = 'ENTREGADO', version = version + 1, actualizado_en = now()
        WHERE id = %s AND estado = 'ASIGNADO' AND codigo_entrega = %s
        RETURNING {COLUMNAS}
        """,
        (pedido_id, codigo),
    ).fetchone()


def cancelar_vencidos(conn, estado_actual, motivo, segundos):
    """Cancela los pedidos que llevan más de 'segundos' en 'estado_actual' sin repartidor.
    Devuelve la lista de pedidos cancelados. Como el UPDATE exige el estado actual, si la
    tarea corre dos veces (o hay dos copias de la app) un pedido solo se cancela una vez."""
    return conn.execute(
        f"""
        UPDATE pedidos.pedidos
        SET estado = 'CANCELADO', motivo_cancelacion = %s,
            version = version + 1, actualizado_en = now()
        WHERE estado = %s AND repartidor_id IS NULL
          AND actualizado_en < now() - (%s::double precision * interval '1 second')
        RETURNING {COLUMNAS}
        """,
        (motivo, estado_actual, segundos),
    ).fetchall()
