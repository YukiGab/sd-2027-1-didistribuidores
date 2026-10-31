import secrets

from app import db
from app.errores import Invalido, NoEncontrado
from app.modulos.pedidos import repositorio
from app.modulos.restaurantes import servicio as restaurantes
from app.modulos.usuarios import servicio as usuarios


def _completo(conn, pedido):
    """El pedido junto con sus platillos."""
    return {**pedido, "platillos": repositorio.listar_platillos(conn, pedido["id"])}


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
        pedido = repositorio.obtener(conn, pedido_id)
        if pedido is None:
            raise NoEncontrado("Pedido no encontrado")
        return _completo(conn, pedido)