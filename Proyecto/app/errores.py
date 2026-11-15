# Errores de negocio. Los servicios los lanzan sin saber nada de HTTP;
# main.py los convierte en códigos HTTP (404, 422, 409, 503).


class ErrorNegocio(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoEncontrado(ErrorNegocio):
    pass


class Invalido(ErrorNegocio):
    pass


class Conflicto(ErrorNegocio):
    pass


class ServicioNoDisponible(ErrorNegocio):
    """Otro servicio (por ejemplo repartidores) no respondió a tiempo o está caído."""
    pass
