import secrets

from app import config, db
from app.errores import Conflicto, Invalido, NoEncontrado
from app.modulos.pagos import servicio as pagos
from app.modulos.pedidos import eventos, repositorio
from app.modulos.repartidores import servicio as repartidores
from app.modulos.restaurantes import servicio as restaurantes
from app.modulos.usuarios import servicio as usuarios


def _completo(conn, pedido):
    """El pedido junto con sus platillos."""
    return {**pedido, "platillos": repositorio.listar_platillos(conn, pedido["id"])}


def _estado_actual(conn, pedido_id):
    pedido = repositorio.obtener(conn, pedido_id)
    if pedido is None:
        raise NoEncontrado("Pedido no encontrado")
    return pedido


def crear_pedido(clave, usuario_id, restaurante_id, items):
    """Crea un pedido de forma idempotente.

    items: lista de (platillo_id, cantidad).
    Devuelve (pedido, creado). creado es False si la clave ya se había usado.
    """
    # 1. ¿Ya existe un pedido con esta clave? Si sí, es un reintento: se devuelve el mismo.
    with db.conexion() as conn:
        existente = repositorio.buscar_por_clave(conn, usuario_id, clave)
        if existente is not None:
            return _completo(conn, existente), False

    # 2. Validar con los otros módulos (solo a través de sus servicios)
    if usuarios.obtener_usuario(usuario_id) is None:
        raise NoEncontrado("Usuario no encontrado")
    restaurante = restaurantes.obtener_restaurante(restaurante_id)
    if restaurante is None:
        raise NoEncontrado("Restaurante no encontrado")

    cantidades = {}  # si un platillo viene repetido, se suman las cantidades
    for platillo_id, cantidad in items:
        cantidades[platillo_id] = cantidades.get(platillo_id, 0) + cantidad

    platillos = restaurantes.obtener_platillos(restaurante_id, list(cantidades))
    precios = {p["id"]: p["precio"] for p in platillos}
    if any(platillo_id not in precios for platillo_id in cantidades):
        raise Invalido("Algún platillo no existe, no es de ese restaurante o no está disponible")

    # El total lo calcula el servidor con los precios del menú, nunca el cliente
    total = sum(precios[pid] * cant for pid, cant in cantidades.items())
    codigo_entrega = f"{secrets.randbelow(10**6):06d}"

    # 3. Insertar. Todo en una sola transacción: el pedido y sus platillos entran juntos o no entran.
    with db.conexion() as conn:
        pedido = repositorio.insertar_si_no_existe(
            conn, usuario_id, restaurante_id, restaurante["zona"], total, clave, codigo_entrega
        )
        if pedido is None:
            # Otra petición con la misma clave se nos adelantó: devolvemos su pedido.
            existente = repositorio.buscar_por_clave(conn, usuario_id, clave)
            return _completo(conn, existente), False

        filas = [(pid, cant, precios[pid]) for pid, cant in cantidades.items()]
        repositorio.insertar_platillos(conn, pedido["id"], filas)
        return _completo(conn, pedido), True


def obtener_pedido(pedido_id):
    with db.conexion() as conn:
        return _completo(conn, _estado_actual(conn, pedido_id))


def pagar_pedido(pedido_id):
    """Paga un pedido. Devuelve (pedido, cambio). cambio es False si ya estaba pagado."""
    with db.conexion() as conn:
        # Revisar y cambiar en una sola instrucción: si dos peticiones llegan a la vez,
        # solo una consigue el cambio. La otra espera, ve que ya no está PENDIENTE_PAGO
        # y recibe 0 filas.
        pedido = repositorio.cambiar_estado(conn, pedido_id, "PENDIENTE_PAGO", "PAGADO")
        if pedido is None:
            actual = _estado_actual(conn, pedido_id)
            if actual["estado"] in ("PAGADO", "ASIGNADO", "ENTREGADO"):
                return _completo(conn, actual), False  # reintento: mismo resultado
            raise Conflicto(f"No se puede pagar un pedido en estado {actual['estado']}")

        # El cobro y el evento van en la MISMA transacción que el cambio de estado
        pagos.cobrar(conn, pedido_id, pedido["total"])
        eventos.registrar(conn, "pedido.pagado", pedido, {"total": float(pedido["total"])})
        return _completo(conn, pedido), True


def listar_disponibles(repartidor_id):
    """Los pedidos PAGADO sin repartidor que están en la zona de ese repartidor."""
    repartidor = repartidores.obtener_repartidor(repartidor_id)
    if repartidor is None:
        raise NoEncontrado("Repartidor no encontrado")
    with db.conexion() as conn:
        return repositorio.listar_pagados_por_zona(conn, repartidor["zona"])


def aceptar_pedido(pedido_id, repartidor_id):
    """Un repartidor acepta un pedido. Gana el primero. Devuelve (pedido, cambio)."""
    repartidor = repartidores.obtener_repartidor(repartidor_id)
    if repartidor is None:
        raise NoEncontrado("Repartidor no encontrado")
    if not repartidor["disponible"]:
        raise Invalido("El repartidor no está disponible")

    with db.conexion() as conn:
        actual = _estado_actual(conn, pedido_id)
    if actual["zona"] != repartidor["zona"]:
        raise Invalido("El pedido es de otra zona")

    with db.conexion() as conn:
        pedido = repositorio.asignar(conn, pedido_id, repartidor_id)
        if pedido is None:
            actual = _estado_actual(conn, pedido_id)
            if actual["estado"] == "ASIGNADO" and actual["repartidor_id"] == repartidor_id:
                return _completo(conn, actual), False  # el mismo repartidor repite: mismo resultado
            raise Conflicto("El pedido ya no está disponible")

        eventos.registrar(conn, "pedido.asignado", pedido, {"repartidorId": str(repartidor_id)})
        return _completo(conn, pedido), True


def entregar_pedido(pedido_id, codigo):
    """Confirma la entrega con el código. Devuelve (pedido, cambio)."""
    with db.conexion() as conn:
        pedido = repositorio.confirmar_entrega(conn, pedido_id, codigo)
        if pedido is None:
            actual = _estado_actual(conn, pedido_id)
            if actual["estado"] == "ENTREGADO" and actual["codigo_entrega"] == codigo:
                return _completo(conn, actual), False  # ya estaba entregado: mismo resultado
            if actual["estado"] == "ASIGNADO":
                raise Invalido("Código de entrega incorrecto")
            raise Conflicto(f"No se puede entregar un pedido en estado {actual['estado']}")

        eventos.registrar(conn, "pedido.entregado", pedido, {})
        return _completo(conn, pedido), True


def cancelar_vencidos():
    """Cancela los pedidos vencidos. La llama la tarea de main.py cada pocos segundos.
    Devuelve cuántos canceló."""
    total = 0

    # Pedidos que nunca se pagaron: se cancelan sin reembolso (nunca hubo cobro)
    with db.conexion() as conn:
        for p in repositorio.cancelar_vencidos(
            conn, "PENDIENTE_PAGO", "sin_pago", config.TIMEOUT_PAGO_SEG
        ):
            eventos.registrar(conn, "pedido.cancelado", p,
                              {"motivo": "sin_pago", "reembolsado": False})
            total += 1

    # Pedidos pagados que nadie tomó: la cancelación y el reembolso son UNA transacción.
    # Si algo falla en medio, no queda un pedido cancelado con el pago sin devolver.
    with db.conexion() as conn:
        for p in repositorio.cancelar_vencidos(
            conn, "PAGADO", "sin_repartidor", config.TIMEOUT_ASIGNACION_SEG
        ):
            pagos.reembolsar(conn, p["id"])
            eventos.registrar(conn, "pedido.cancelado", p,
                              {"motivo": "sin_repartidor", "reembolsado": True})
            total += 1

    return total
