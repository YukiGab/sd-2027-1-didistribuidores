# Capa de persistencia del módulo pagos (solo SQL)


def crear(conn, pedido_id, monto):
    """Registra el cobro. La base garantiza un solo cobro por pedido (UNIQUE en pedido_id)."""
    return conn.execute(
        """
        INSERT INTO pagos.pagos (pedido_id, monto)
        VALUES (%s, %s)
        RETURNING id, pedido_id, monto, estado, creado_en, reembolsado_en
        """,
        (pedido_id, monto),
    ).fetchone()


def obtener_por_pedido(conn, pedido_id):
    return conn.execute(
        """
        SELECT id, pedido_id, monto, estado, creado_en, reembolsado_en
        FROM pagos.pagos WHERE pedido_id = %s
        """,
        (pedido_id,),
    ).fetchone()


def reembolsar(conn, pedido_id):
    """Marca el pago como reembolsado, pero solo si seguía cobrado.
    Si ya estaba reembolsado no cambia nada y devuelve None (no se reembolsa dos veces)."""
    return conn.execute(
        """
        UPDATE pagos.pagos
        SET estado = 'REEMBOLSADO', reembolsado_en = now()
        WHERE pedido_id = %s AND estado = 'COBRADO'
        RETURNING id, pedido_id, monto, estado, creado_en, reembolsado_en
        """,
        (pedido_id,),
    ).fetchone()
