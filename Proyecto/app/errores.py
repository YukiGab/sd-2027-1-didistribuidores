# Errores de negocio. Los servicios los lanzan sin saber nada de HTTP;
# main.py los convierte en códigos HTTP (404, 422, 409).


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