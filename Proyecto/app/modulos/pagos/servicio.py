from app import db
from app.modulos.pagos import repositorio


def cobrar(conn, pedido_id, monto):
    """Cobro simulado. Recibe la conexión de quien lo llama (pedidos) para que el cobro
    y el cambio de estado del pedido sean una sola transacción."""
    return repositorio.crear(conn, pedido_id, monto)


def obtener_pago(pedido_id):
    """Devuelve el pago del pedido o None si no hay."""
    with db.conexion() as conn:
        return repositorio.obtener_por_pedido(conn, pedido_id)


def reembolsar(conn, pedido_id):
    """Reembolso simulado, también dentro de la transacción de quien lo llama."""
    return repositorio.reembolsar(conn, pedido_id)
