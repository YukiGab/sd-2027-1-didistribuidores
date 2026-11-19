# Prueba 1: una Idempotency-Key reutilizada con otro pedido (huella de la petición)
K="huella-$(date +%s)"
CUERPO="{\"usuario_id\":\"$U\",\"restaurante_id\":\"$R\",\"platillos\":[{\"platillo_id\":\"$P\",\"cantidad\":1}]}"
OTRO="{\"usuario_id\":\"$U\",\"restaurante_id\":\"$R\",\"platillos\":[{\"platillo_id\":\"$P\",\"cantidad\":3}]}"
paso 'curl -s -o /dev/null -w "%{http_code}\n" -X POST $B/api/pedidos -H "Content-Type: application/json" -H "Idempotency-Key: $K" -d "$CUERPO"'
paso 'curl -s -o /dev/null -w "%{http_code}\n" -X POST $B/api/pedidos -H "Content-Type: application/json" -H "Idempotency-Key: $K" -d "$CUERPO"'
paso 'curl -s -w "\n%{http_code}\n" -X POST $B/api/pedidos -H "Content-Type: application/json" -H "Idempotency-Key: $K" -d "$OTRO"'
paso 'docker compose exec -T db psql -U postgres -d didistribuidores -c "SELECT count(*) AS pedidos_con_esa_clave, left(max(huella_peticion),16) AS huella FROM pedidos.pedidos WHERE clave_idempotencia='"'"'$K'"'"'"'
