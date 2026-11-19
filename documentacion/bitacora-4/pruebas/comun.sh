# Variables y funciones auxiliares para las pruebas de la etapa 4.
# Uso (desde Proyecto/, en bash o Git Bash):  source ../documentacion/bitacora-4/pruebas/comun.sh
# Todas las peticiones van por el gateway, como las de cualquier cliente.

B=${B:-http://localhost:8080}
PY=${PY:-$(command -v python3 >/dev/null 2>&1 && echo python3 || echo python)}
J='import sys,json; print(json.load(sys.stdin)'

# Muestra el comando (como en una terminal) y lo ejecuta. Sirve para que la evidencia
# guarde exactamente lo que se corrió y lo que salió.
paso() { echo "\$ $*"; eval "$@"; }

U=$(curl -s -X POST $B/api/usuarios -H "Content-Type: application/json" -d '{"nombre":"Prueba E4","zona":3}' | $PY -c "$J['id'])")
R=$(curl -s $B/api/restaurantes | $PY -c "$J[0]['id'])")
P=$(curl -s $B/api/restaurantes/$R/platillos | $PY -c "$J[0]['id'])")
REP=$(curl -s "$B/api/repartidores?zona=3" | $PY -c "$J[0]['id'])")

nuevo_pedido() {
  curl -s -X POST $B/api/pedidos -H "Content-Type: application/json" -H "Idempotency-Key: e4-$(date +%s%N)" \
    -d "{\"usuario_id\":\"$U\",\"restaurante_id\":\"$R\",\"platillos\":[{\"platillo_id\":\"$P\",\"cantidad\":1}]}" \
    | $PY -c "$J['id'])"
}
pagar()          { curl -s -X POST $B/api/pedidos/$1/pago > /dev/null; }
estado_pedido()  { curl -s $B/api/pedidos/$1 | $PY -c "$J['estado'])"; }
aceptar_tiempo() { curl -s -o /dev/null -w "%{http_code} en %{time_total}s\n" -X POST $B/api/pedidos/$1/aceptar \
                     -H "Content-Type: application/json" -d "{\"repartidor_id\":\"$2\"}"; }
avisos()         { curl -s "$B/api/notificaciones/pedido/$1" \
                     | $PY -c "import sys,json; [print(a['version_pedido'], a['tipo'], '|', a['mensaje']) for a in json.load(sys.stdin)]"; }
