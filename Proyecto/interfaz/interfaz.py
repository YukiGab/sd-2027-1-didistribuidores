"""Interfaz de escritorio de DiDistribuidores.

Una ventana con tres pestañas que habla con el sistema SOLO por el gateway (http://localhost:8080),
igual que cualquier cliente externo:

  Cliente       crea su usuario, elige restaurante y platillos, pide, paga y sigue su pedido
                (estado, código de entrega y avisos que llegan por RabbitMQ).
  Repartidor    elige quién es, ve los pedidos pagados de su zona, acepta uno y confirma
                la entrega con el código que le da el cliente.
  Sistema       insignias del gateway, del circuito hacia repartidores y del outbox, el
                balanceo entre las dos copias de repartidores y la bitácora de peticiones.

No necesita instalar nada: usa solo la biblioteca estándar de Python (tkinter y urllib).

    python interfaz.py                         # contra http://localhost:8080
    python interfaz.py --url http://otra:8080  # contra otro gateway

Regla de diseño: la interfaz MUESTRA, nunca decide. Todas las reglas (idempotencia, quién gana
un pedido, el código de entrega, los relojes) viven en el servidor; aquí solo se llaman los
endpoints y se enseña lo que contestan.
"""
import argparse
import json
import queue
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import uuid
import webbrowser
from tkinter import messagebox, ttk

URL_POR_DEFECTO = "http://localhost:8080"
REFRESCO_MS = 2000          # cada cuánto se actualizan las insignias y el pedido en curso
TIEMPO_LIMITE_SEG = 10      # la interfaz nunca se queda esperando para siempre
ESTADOS = ("PENDIENTE_PAGO", "PAGADO", "ASIGNADO", "ENTREGADO")


# ---------------------------------------------------------------------------- cliente HTTP
class Respuesta:
    def __init__(self, estado, datos, ms, instancia=None):
        self.estado = estado          # código HTTP; 0 si no hubo conexión
        self.datos = datos            # JSON ya interpretado (o None)
        self.ms = ms
        self.instancia = instancia    # encabezado X-Instancia (qué copia de repartidores contestó)

    @property
    def ok(self):
        return 200 <= self.estado < 300

    def error(self):
        """El mensaje para la persona: el 'detail' del servidor o algo legible."""
        if self.estado == 0:
            return "Sin conexión con el sistema. ¿Está levantado con docker compose?"
        if isinstance(self.datos, dict) and isinstance(self.datos.get("detail"), str):
            return f"{self.estado}: {self.datos['detail']}"
        return f"Error {self.estado}"


class Api:
    """Llamadas HTTP al gateway. Cada llamada queda en la bitácora (método, ruta, código, ms)."""

    def __init__(self, url_base, bitacora):
        self.url_base = url_base.rstrip("/")
        self._bitacora = bitacora

    def llamar(self, metodo, ruta, cuerpo=None, encabezados=None, registrar=True):
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        peticion = urllib.request.Request(self.url_base + ruta, data=datos, method=metodo)
        peticion.add_header("Content-Type", "application/json")
        for nombre, valor in (encabezados or {}).items():
            peticion.add_header(nombre, valor)
        inicio = time.perf_counter()
        try:
            with urllib.request.urlopen(peticion, timeout=TIEMPO_LIMITE_SEG) as r:
                estado, crudo, instancia = r.status, r.read(), r.headers.get("X-Instancia")
        except urllib.error.HTTPError as e:      # 4xx y 5xx también traen cuerpo
            estado, crudo, instancia = e.code, e.read(), e.headers.get("X-Instancia")
        except (urllib.error.URLError, OSError):
            estado, crudo, instancia = 0, b"", None
        ms = round((time.perf_counter() - inicio) * 1000)
        try:
            contenido = json.loads(crudo) if crudo else None
        except ValueError:
            contenido = None
        respuesta = Respuesta(estado, contenido, ms, instancia)
        if registrar:
            self._bitacora(metodo, ruta, respuesta)
        return respuesta


# ------------------------------------------------------------------------------- ventana
class Interfaz(tk.Tk):
    def __init__(self, url_base):
        super().__init__()
        self.title("DiDistribuidores")
        self.geometry("980x680")
        self.minsize(860, 600)
        self._resultados = queue.Queue()     # los hilos dejan aquí lo que la ventana debe pintar
        self.api = Api(url_base, self._anotar)

        # Estado de la sesión (solo lo que la interfaz necesita recordar)
        self.usuario = None
        self.restaurantes = []
        self.menu = []
        self.pedido = None
        self.ultima_peticion = None        # (clave, cuerpo) para poder repetirla y ver la idempotencia
        self.repartidores = []
        self.repartidor = None
        self.pedido_repartidor = None

        self._estilos()
        self._insignias()
        cuaderno = ttk.Notebook(self)
        cuaderno.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._pestana_cliente(cuaderno)
        self._pestana_repartidor(cuaderno)
        self._pestana_sistema(cuaderno)

        self.after(100, self._atender_resultados)
        self.after(200, self._refrescar)
        self._en_segundo_plano(self._cargar_inicio)

    # ------------------------------------------------------------------ infraestructura
    def _en_segundo_plano(self, trabajo, *args):
        """Corre 'trabajo' en un hilo para que la ventana no se congele mientras espera la red.
        trabajo devuelve una función (o None) que se ejecuta después en el hilo de la ventana."""
        def correr():
            try:
                pintar = trabajo(*args)
            except Exception as e:  # un error de la interfaz no debe tumbar la ventana
                pintar = lambda e=e: messagebox.showerror("DiDistribuidores", str(e))
            if pintar:
                self._resultados.put(pintar)
        threading.Thread(target=correr, daemon=True).start()

    def _atender_resultados(self):
        while not self._resultados.empty():
            self._resultados.get()()
        self.after(100, self._atender_resultados)

    def _anotar(self, metodo, ruta, r):
        """Una línea por petición en la pestaña Sistema (se llama desde los hilos)."""
        linea = f"{time.strftime('%H:%M:%S')}  {r.estado or '---'}  {metodo:<5} {ruta[:60]}  {r.ms} ms"
        if r.instancia:
            linea += f"  [{r.instancia}]"
        if not r.ok and isinstance(r.datos, dict) and isinstance(r.datos.get("detail"), str):
            linea += f"\n          {r.datos['detail']}"
        self._resultados.put(lambda: self._agregar_bitacora(linea, r.estado))

    def _estilos(self):
        estilo = ttk.Style(self)
        if "vista" in estilo.theme_names():
            estilo.theme_use("vista")
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 13, "bold"))
        estilo.configure("Grande.TLabel", font=("Segoe UI", 18, "bold"))
        estilo.configure("Acento.TButton", font=("Segoe UI", 10, "bold"))

    def _insignias(self):
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=10, pady=8)
        ttk.Label(barra, text="DiDistribuidores", style="Titulo.TLabel").pack(side="left")
        ttk.Label(barra, text=f"   gateway: {self.api.url_base}").pack(side="left")
        self.insignias = {}
        for clave in ("outbox", "circuito", "gateway"):
            etiqueta = tk.Label(barra, text=f" {clave}: … ", bg="#d1d1d6", padx=8, pady=2,
                                font=("Segoe UI", 9, "bold"))
            etiqueta.pack(side="right", padx=3)
            self.insignias[clave] = etiqueta

    def _pintar_insignia(self, clave, texto, color):
        colores = {"verde": "#34c759", "ambar": "#ff9f0a", "rojo": "#ff3b30", "gris": "#d1d1d6"}
        self.insignias[clave].configure(text=f" {texto} ", bg=colores[color],
                                        fg="white" if color != "gris" else "black")

    # ------------------------------------------------------------------ pestaña Cliente
    def _pestana_cliente(self, cuaderno):
        marco = ttk.Frame(cuaderno, padding=12)
        cuaderno.add(marco, text="  Cliente  ")
        marco.columnconfigure(0, weight=1)
        marco.columnconfigure(1, weight=1)
        marco.rowconfigure(1, weight=1)

        # Usuario
        cuadro = ttk.LabelFrame(marco, text="1. ¿Quién pide?", padding=8)
        cuadro.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(cuadro, text="Nombre").pack(side="left")
        self.nombre_cliente = ttk.Entry(cuadro, width=22)
        self.nombre_cliente.insert(0, "Cliente demo")
        self.nombre_cliente.pack(side="left", padx=4)
        ttk.Label(cuadro, text="Zona").pack(side="left")
        self.zona_cliente = ttk.Spinbox(cuadro, from_=1, to=5, width=4)
        self.zona_cliente.set(3)
        self.zona_cliente.pack(side="left", padx=4)
        ttk.Button(cuadro, text="Crear usuario", command=self._crear_usuario).pack(side="left", padx=6)
        self.lbl_usuario = ttk.Label(cuadro, text="Sin usuario todavía.")
        self.lbl_usuario.pack(side="left", padx=8)

        # Menú
        izquierda = ttk.LabelFrame(marco, text="2. Elige restaurante y platillos", padding=8)
        izquierda.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        izquierda.columnconfigure(0, weight=1)
        izquierda.rowconfigure(1, weight=1)
        self.combo_restaurante = ttk.Combobox(izquierda, state="readonly")
        self.combo_restaurante.grid(row=0, column=0, sticky="ew")
        self.combo_restaurante.bind("<<ComboboxSelected>>", lambda e: self._elegir_restaurante())
        self.marco_menu = ttk.Frame(izquierda)
        self.marco_menu.grid(row=1, column=0, sticky="nsew", pady=8)
        self.cantidades = {}
        botones = ttk.Frame(izquierda)
        botones.grid(row=2, column=0, sticky="ew")
        self.lbl_total = ttk.Label(botones, text="Total: $0.00", style="Titulo.TLabel")
        self.lbl_total.pack(side="left")
        ttk.Button(botones, text="Pedir", style="Acento.TButton", command=self._pedir).pack(side="right")
        ttk.Button(botones, text="Repetir la misma petición", command=self._repetir_pedido).pack(side="right", padx=6)

        # Seguimiento
        derecha = ttk.LabelFrame(marco, text="3. Sigue tu pedido", padding=8)
        derecha.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        derecha.columnconfigure(0, weight=1)
        derecha.rowconfigure(5, weight=1)
        self.lbl_estado = ttk.Label(derecha, text="Aún no hay pedido.", style="Grande.TLabel")
        self.lbl_estado.grid(row=0, column=0, sticky="w")
        self.lbl_detalle = ttk.Label(derecha, text="", wraplength=380, justify="left")
        self.lbl_detalle.grid(row=1, column=0, sticky="w", pady=4)
        self.lbl_codigo = ttk.Label(derecha, text="", style="Titulo.TLabel")
        self.lbl_codigo.grid(row=2, column=0, sticky="w")
        acciones = ttk.Frame(derecha)
        acciones.grid(row=3, column=0, sticky="ew", pady=6)
        self.btn_pagar = ttk.Button(acciones, text="Pagar", style="Acento.TButton", command=self._pagar,
                                    state="disabled")
        self.btn_pagar.pack(side="left")
        ttk.Button(acciones, text="Nuevo pedido", command=self._nuevo_pedido).pack(side="left", padx=6)
        ttk.Label(derecha, text="Avisos (llegan por RabbitMQ desde el servicio de notificaciones):").grid(
            row=4, column=0, sticky="w")
        self.lista_avisos = tk.Listbox(derecha, height=7)
        self.lista_avisos.grid(row=5, column=0, sticky="nsew")

    def _cargar_inicio(self):
        r = self.api.llamar("GET", "/api/restaurantes")
        if not r.ok:
            return lambda: self.lbl_usuario.configure(text=r.error())
        self.restaurantes = r.datos
        def pintar():
            self.combo_restaurante["values"] = [f"{x['nombre']}  (zona {x['zona']})" for x in self.restaurantes]
            if self.restaurantes:
                self.combo_restaurante.current(0)
                self._elegir_restaurante()
        return pintar

    def _crear_usuario(self):
        nombre, zona = self.nombre_cliente.get().strip(), int(self.zona_cliente.get())
        def trabajo():
            r = self.api.llamar("POST", "/api/usuarios", {"nombre": nombre, "zona": zona})
            if not r.ok:
                return lambda: messagebox.showwarning("Usuario", r.error())
            self.usuario = r.datos
            return lambda: self.lbl_usuario.configure(
                text=f"{self.usuario['nombre']} · zona {self.usuario['zona']} · id {self.usuario['id'][:8]}…")
        self._en_segundo_plano(trabajo)

    def _restaurante_actual(self):
        i = self.combo_restaurante.current()
        return self.restaurantes[i] if i >= 0 else None

    def _elegir_restaurante(self):
        restaurante = self._restaurante_actual()
        def trabajo():
            r = self.api.llamar("GET", f"/api/restaurantes/{restaurante['id']}/platillos")
            if not r.ok:
                return lambda: messagebox.showwarning("Menú", r.error())
            self.menu = r.datos
            return self._pintar_menu
        self._en_segundo_plano(trabajo)

    def _pintar_menu(self):
        for hijo in self.marco_menu.winfo_children():
            hijo.destroy()
        self.cantidades = {}
        for fila, platillo in enumerate(self.menu):
            ttk.Label(self.marco_menu, text=platillo["nombre"]).grid(row=fila, column=0, sticky="w", pady=2)
            ttk.Label(self.marco_menu, text=f"${float(platillo['precio']):.2f}").grid(row=fila, column=1, padx=12)
            cantidad = tk.IntVar(value=0)
            caja = ttk.Spinbox(self.marco_menu, from_=0, to=20, width=4, textvariable=cantidad,
                               command=self._actualizar_total)
            caja.grid(row=fila, column=2)
            caja.bind("<KeyRelease>", lambda e: self._actualizar_total())
            self.cantidades[platillo["id"]] = cantidad
        self.marco_menu.columnconfigure(0, weight=1)
        self._actualizar_total()

    def _items(self):
        items = []
        for platillo_id, var in self.cantidades.items():
            try:
                cantidad = int(var.get())
            except (tk.TclError, ValueError):
                cantidad = 0
            if cantidad > 0:
                items.append({"platillo_id": platillo_id, "cantidad": cantidad})
        return items

    def _actualizar_total(self):
        precios = {p["id"]: float(p["precio"]) for p in self.menu}
        total = sum(precios[i["platillo_id"]] * i["cantidad"] for i in self._items())
        self.lbl_total.configure(text=f"Total: ${total:.2f}")  # solo informativo: el total real lo calcula el servidor

    def _pedir(self):
        if self.usuario is None:
            messagebox.showinfo("Pedido", "Primero crea el usuario (paso 1).")
            return
        items = self._items()
        if not items:
            messagebox.showinfo("Pedido", "Elige al menos un platillo.")
            return
        cuerpo = {"usuario_id": self.usuario["id"], "restaurante_id": self._restaurante_actual()["id"],
                  "platillos": items}
        # Una clave nueva por cada pedido nuevo; si se repite la petición se reutiliza la misma clave.
        self.ultima_peticion = (str(uuid.uuid4()), cuerpo)
        self._enviar_pedido()

    def _repetir_pedido(self):
        if self.ultima_peticion is None:
            messagebox.showinfo("Idempotencia", "Primero haz un pedido; luego repítelo para ver que no se duplica.")
            return
        self._enviar_pedido()

    def _enviar_pedido(self):
        clave, cuerpo = self.ultima_peticion
        def trabajo():
            r = self.api.llamar("POST", "/api/pedidos", cuerpo, {"Idempotency-Key": clave})
            if not r.ok:
                return lambda: messagebox.showwarning("Pedido", r.error())
            repetido = r.estado == 200 and self.pedido is not None and r.datos["id"] == self.pedido["id"]
            self.pedido = r.datos
            def pintar():
                self._pintar_pedido([])
                if repetido:
                    messagebox.showinfo("Idempotencia",
                                        "El servidor respondió 200 con el MISMO pedido: no se creó otro ni se cobró dos veces.")
            return pintar
        self._en_segundo_plano(trabajo)

    def _pagar(self):
        if self.pedido is None:
            return
        pedido_id = self.pedido["id"]
        def trabajo():
            r = self.api.llamar("POST", f"/api/pedidos/{pedido_id}/pago")
            if not r.ok:
                return lambda: messagebox.showwarning("Pago", r.error())
            self.pedido = r.datos
            return lambda: self._pintar_pedido(None)
        self._en_segundo_plano(trabajo)

    def _nuevo_pedido(self):
        self.pedido = None
        self.ultima_peticion = None
        self.lbl_estado.configure(text="Aún no hay pedido.")
        self.lbl_detalle.configure(text="")
        self.lbl_codigo.configure(text="")
        self.btn_pagar.configure(state="disabled")
        self.lista_avisos.delete(0, "end")

    def _pintar_pedido(self, avisos):
        p = self.pedido
        mensajes = {
            "PENDIENTE_PAGO": "Confirma tu pago para que busquemos repartidor.",
            "PAGADO": "Pago recibido. Buscando repartidor…",
            "ASIGNADO": "Tu repartidor aceptó. Dale el código al recibir.",
            "ENTREGADO": "Tu pedido fue entregado. ¡Buen provecho!",
            "CANCELADO": f"Pedido cancelado ({p.get('motivo_cancelacion')}). Si pagaste, se reembolsó.",
        }
        self.lbl_estado.configure(text=p["estado"])
        self.btn_pagar.configure(state="normal" if p["estado"] == "PENDIENTE_PAGO" else "disabled")
        self.lbl_detalle.configure(
            text=f"Pedido {p['id'][:8]}… · total ${float(p['total']):.2f} · versión {p['version']}\n"
                 f"{mensajes.get(p['estado'], '')}")
        self.lbl_codigo.configure(
            text=f"Código de entrega: {p['codigo_entrega']}" if p["estado"] == "ASIGNADO" else "")
        if avisos is not None:
            self.lista_avisos.delete(0, "end")
            for a in avisos:
                self.lista_avisos.insert("end", f"v{a['version_pedido']}  {a['mensaje']}")

    # ------------------------------------------------------------------ pestaña Repartidor
    def _pestana_repartidor(self, cuaderno):
        marco = ttk.Frame(cuaderno, padding=12)
        cuaderno.add(marco, text="  Repartidor  ")
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(1, weight=1)

        cuadro = ttk.LabelFrame(marco, text="1. ¿Quién eres?", padding=8)
        cuadro.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(cuadro, text="Zona").pack(side="left")
        self.zona_repartidor = ttk.Spinbox(cuadro, from_=1, to=5, width=4)
        self.zona_repartidor.set(3)
        self.zona_repartidor.pack(side="left", padx=4)
        ttk.Button(cuadro, text="Buscar repartidores", command=self._buscar_repartidores).pack(side="left", padx=4)
        self.combo_repartidor = ttk.Combobox(cuadro, state="readonly", width=34)
        self.combo_repartidor.pack(side="left", padx=4)
        self.combo_repartidor.bind("<<ComboboxSelected>>", lambda e: self._elegir_repartidor())
        self.btn_disponible = ttk.Button(cuadro, text="Marcar no disponible", command=self._cambiar_disponibilidad)
        self.btn_disponible.pack(side="left", padx=4)

        cuadro = ttk.LabelFrame(marco, text="2. Pedidos pagados de tu zona", padding=8)
        cuadro.grid(row=1, column=0, sticky="nsew")
        cuadro.columnconfigure(0, weight=1)
        cuadro.rowconfigure(0, weight=1)
        columnas = ("pedido", "total", "pagado_desde")
        self.tabla_disponibles = ttk.Treeview(cuadro, columns=columnas, show="headings", height=8)
        for col, titulo, ancho in zip(columnas, ("Pedido", "Total", "Creado"), (260, 120, 260)):
            self.tabla_disponibles.heading(col, text=titulo)
            self.tabla_disponibles.column(col, width=ancho)
        self.tabla_disponibles.grid(row=0, column=0, sticky="nsew")
        botones = ttk.Frame(cuadro)
        botones.grid(row=1, column=0, sticky="ew", pady=6)
        ttk.Button(botones, text="Actualizar", command=self._listar_disponibles).pack(side="left")
        ttk.Button(botones, text="Aceptar pedido", style="Acento.TButton", command=self._aceptar).pack(side="left", padx=6)

        cuadro = ttk.LabelFrame(marco, text="3. Entrega", padding=8)
        cuadro.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.lbl_entrega = ttk.Label(cuadro, text="No tienes un pedido en curso.")
        self.lbl_entrega.pack(side="left")
        ttk.Button(cuadro, text="Confirmar entrega", style="Acento.TButton", command=self._entregar).pack(side="right")
        self.codigo = ttk.Entry(cuadro, width=10)
        self.codigo.pack(side="right", padx=6)
        ttk.Label(cuadro, text="Código que te dio el cliente:").pack(side="right")

    def _buscar_repartidores(self):
        zona = int(self.zona_repartidor.get())
        def trabajo():
            r = self.api.llamar("GET", f"/api/repartidores?zona={zona}")
            if not r.ok:
                return lambda: messagebox.showwarning("Repartidores", r.error())
            self.repartidores = r.datos
            def pintar():
                self.combo_repartidor["values"] = [
                    f"{x['nombre']}  ({'disponible' if x['disponible'] else 'no disponible'})" for x in self.repartidores]
                if self.repartidores:
                    self.combo_repartidor.current(0)
                    self._elegir_repartidor()
            return pintar
        self._en_segundo_plano(trabajo)

    def _elegir_repartidor(self):
        self.repartidor = self.repartidores[self.combo_repartidor.current()]
        self.btn_disponible.configure(
            text="Marcar no disponible" if self.repartidor["disponible"] else "Marcar disponible")
        self._listar_disponibles()

    def _cambiar_disponibilidad(self):
        if self.repartidor is None:
            return
        rep = self.repartidor
        def trabajo():
            r = self.api.llamar("PATCH", f"/api/repartidores/{rep['id']}", {"disponible": not rep["disponible"]})
            if not r.ok:
                return lambda: messagebox.showwarning("Disponibilidad", r.error())
            return self._buscar_repartidores
        self._en_segundo_plano(trabajo)

    def _listar_disponibles(self):
        if self.repartidor is None:
            return
        rep_id = self.repartidor["id"]
        def trabajo():
            r = self.api.llamar("GET", f"/api/pedidos/disponibles?repartidor_id={rep_id}")
            def pintar():
                self.tabla_disponibles.delete(*self.tabla_disponibles.get_children())
                if not r.ok:
                    # Con repartidores caído o el circuito abierto, el núcleo contesta 503 sin quedarse colgado
                    self.lbl_entrega.configure(text=r.error())
                    return
                for p in r.datos:
                    self.tabla_disponibles.insert("", "end", iid=p["id"],
                                                  values=(p["id"], f"${float(p['total']):.2f}", p["creado_en"]))
            return pintar
        self._en_segundo_plano(trabajo)

    def _aceptar(self):
        seleccion = self.tabla_disponibles.selection()
        if not seleccion or self.repartidor is None:
            messagebox.showinfo("Aceptar", "Elige un repartidor y un pedido de la lista.")
            return
        pedido_id, rep_id = seleccion[0], self.repartidor["id"]
        def trabajo():
            r = self.api.llamar("POST", f"/api/pedidos/{pedido_id}/aceptar", {"repartidor_id": rep_id})
            if not r.ok:
                # 409: otro repartidor llegó primero; 503: repartidores no responde o el circuito está abierto
                return lambda: (messagebox.showwarning("Aceptar", r.error()), self._listar_disponibles())
            self.pedido_repartidor = r.datos
            def pintar():
                self.lbl_entrega.configure(text=f"En curso: pedido {pedido_id[:8]}… · pide el código al cliente.")
                self._listar_disponibles()
            return pintar
        self._en_segundo_plano(trabajo)

    def _entregar(self):
        if self.pedido_repartidor is None:
            messagebox.showinfo("Entrega", "Primero acepta un pedido.")
            return
        pedido_id, codigo = self.pedido_repartidor["id"], self.codigo.get().strip()
        def trabajo():
            r = self.api.llamar("POST", f"/api/pedidos/{pedido_id}/entrega", {"codigo": codigo})
            if not r.ok:
                return lambda: messagebox.showwarning("Entrega", r.error())
            self.pedido_repartidor = None
            return lambda: (self.lbl_entrega.configure(text="Entregado. ¡Buen trabajo!"),
                            self.codigo.delete(0, "end"))
        self._en_segundo_plano(trabajo)

    # ------------------------------------------------------------------ pestaña Sistema
    def _pestana_sistema(self, cuaderno):
        marco = ttk.Frame(cuaderno, padding=12)
        cuaderno.add(marco, text="  Sistema  ")
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(2, weight=1)

        cuadro = ttk.LabelFrame(marco, text="Estado operativo (GET /estado)", padding=8)
        cuadro.grid(row=0, column=0, sticky="ew")
        self.lbl_estado_sistema = ttk.Label(cuadro, text="…", font=("Consolas", 10))
        self.lbl_estado_sistema.pack(anchor="w")

        botones = ttk.Frame(marco)
        botones.grid(row=1, column=0, sticky="ew", pady=8)
        ttk.Button(botones, text="Balanceo: 10 consultas a repartidores", command=self._balanceo).pack(side="left")
        for texto, url in (("Panel web", self.api.url_base + "/panel/"),
                           ("Swagger", self.api.url_base + "/docs"),
                           ("Traefik", "http://localhost:8081"),
                           ("RabbitMQ", "http://localhost:15672")):
            ttk.Button(botones, text=texto, command=lambda u=url: webbrowser.open(u)).pack(side="right", padx=3)

        cuadro = ttk.LabelFrame(marco, text="Bitácora de peticiones (lo que ve el gateway)", padding=6)
        cuadro.grid(row=2, column=0, sticky="nsew")
        cuadro.columnconfigure(0, weight=1)
        cuadro.rowconfigure(0, weight=1)
        self.bitacora = tk.Text(cuadro, height=12, font=("Consolas", 9), state="disabled", wrap="none")
        self.bitacora.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(cuadro, command=self.bitacora.yview)
        barra.grid(row=0, column=1, sticky="ns")
        self.bitacora.configure(yscrollcommand=barra.set)
        for familia, color in (("2", "#1b7f3b"), ("4", "#b25e00"), ("5", "#c62828"), ("0", "#c62828")):
            self.bitacora.tag_configure(familia, foreground=color)

    def _agregar_bitacora(self, linea, estado):
        self.bitacora.configure(state="normal")
        self.bitacora.insert("end", linea + "\n", str(estado)[0] if estado else "0")
        self.bitacora.see("end")
        self.bitacora.configure(state="disabled")

    def _balanceo(self):
        def trabajo():
            conteo = {}
            for _ in range(10):
                r = self.api.llamar("GET", "/api/repartidores?zona=3")
                nombre = r.instancia or f"sin respuesta ({r.estado})"
                conteo[nombre] = conteo.get(nombre, 0) + 1
            texto = "\n".join(f"{copia}: {n} de 10" for copia, n in conteo.items())
            return lambda: messagebox.showinfo("Balanceo entre copias de repartidores", texto)
        self._en_segundo_plano(trabajo)

    # ------------------------------------------------------------------ refresco periódico
    def _refrescar(self):
        self._en_segundo_plano(self._consultar_estado)
        self.after(REFRESCO_MS, self._refrescar)

    def _consultar_estado(self):
        salud = self.api.llamar("GET", "/salud", registrar=False)
        estado = self.api.llamar("GET", "/estado", registrar=False)
        avisos = None
        if self.pedido is not None:
            r = self.api.llamar("GET", f"/api/pedidos/{self.pedido['id']}", registrar=False)
            if r.ok:
                self.pedido = r.datos
            a = self.api.llamar("GET", f"/api/notificaciones/pedido/{self.pedido['id']}", registrar=False)
            avisos = a.datos if a.ok else None

        def pintar():
            self._pintar_insignia("gateway", "gateway: ok" if salud.ok else "gateway: caído",
                                  "verde" if salud.ok else "rojo")
            if estado.ok:
                circuito = estado.datos["repartidores"]["circuito"]
                color = {"CERRADO": "verde", "SEMIABIERTO": "ambar", "ABIERTO": "rojo"}.get(circuito, "gris")
                self._pintar_insignia("circuito", f"circuito: {circuito}", color)
                pendientes = estado.datos["outbox_pendientes"]
                self._pintar_insignia("outbox", f"outbox: {pendientes} pendientes",
                                      "verde" if pendientes == 0 else "ambar")
                self.lbl_estado_sistema.configure(text=json.dumps(estado.datos, indent=2, ensure_ascii=False))
            else:
                self._pintar_insignia("circuito", "circuito: ?", "gris")
                self._pintar_insignia("outbox", "outbox: ?", "gris")
                self.lbl_estado_sistema.configure(text=estado.error())
            if self.pedido is not None:
                self._pintar_pedido(avisos)
        return pintar


def main():
    parser = argparse.ArgumentParser(description="Interfaz de escritorio de DiDistribuidores")
    parser.add_argument("--url", default=URL_POR_DEFECTO, help="dirección del gateway (por defecto %(default)s)")
    args = parser.parse_args()
    Interfaz(args.url).mainloop()


if __name__ == "__main__":
    main()
