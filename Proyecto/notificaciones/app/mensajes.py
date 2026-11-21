"""El texto del aviso que recibe el cliente para cada tipo de evento."""

TIPOS = (
    "pedido.pagado",
    "pedido.retrasado",
    "pedido.asignado",
    "pedido.entregado",
    "pedido.cancelado",
)


def _dinero(valor):
    try:
        return f"${float(valor):,.2f}"
    except (TypeError, ValueError):
        return ""


def texto(tipo, datos):
    """Devuelve el mensaje para el cliente. 'datos' es el campo datos del evento."""
    if tipo == "pedido.pagado":
        monto = _dinero(datos.get("total"))
        con_monto = f" de {monto}" if monto else ""
        return f"Recibimos tu pago{con_monto}. Estamos buscando un repartidor."
    if tipo == "pedido.retrasado":
        return "Tu pedido se está retrasando: seguimos buscando un repartidor."
    if tipo == "pedido.asignado":
        return "Un repartidor aceptó tu pedido."
    if tipo == "pedido.entregado":
        return "Tu pedido fue entregado. ¡Buen provecho!"
    if tipo == "pedido.cancelado":
        motivo = datos.get("motivo")
        if motivo == "sin_pago":
            return "Cancelamos tu pedido porque no se pagó a tiempo."
        if motivo == "sin_repartidor":
            reembolso = " Tu pago fue reembolsado." if datos.get("reembolsado") else ""
            return "Cancelamos tu pedido porque no encontramos repartidor." + reembolso
        return "Tu pedido fue cancelado."
    raise ValueError(f"tipo desconocido: {tipo}")
