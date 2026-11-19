# Regresión de las etapas 1 a 3 sobre el código final (todo por el gateway).
# Uso, desde Proyecto/:  source ../documentacion/bitacora-4/pruebas/comun.sh; source ../documentacion/pruebas/regresion.sh
psql_db() { docker compose exec -T db psql -U postgres -d didistribuidores -c "$1"; }
echo "### E1. Cinco peticiones simultáneas con la misma Idempotency-Key"
K="reg-$(date +%s)"; C="{\"usuario_id\":\"$U\",\"restaurante_id\":\"$R\",\"platillos\":[{\"platillo_id\":\"$P\",\"cantidad\":2}]}"
paso 'for i in 1 2 3 4 5; do curl -s -o /dev/null -w "%{http_code} " -X POST $B/api/pedidos -H "Content-Type: application/json" -H "Idempotency-Key: $K" -d "$C" & done; wait; echo'
paso 'psql_db "SELECT count(*) AS pedidos FROM pedidos.pedidos WHERE clave_idempotencia='"'"'$K'"'"'"'
echo "### E1. Peticiones inválidas: sin clave (400), usuario inexistente (404)"
paso 'curl -s -w " -> %{http_code}\n" -X POST $B/api/pedidos -H "Content-Type: application/json" -d "$C"'
paso 'curl -s -w " -> %{http_code}\n" -X POST $B/api/pedidos -H "Content-Type: application/json" -H "Idempotency-Key: x-$K" -d "{\"usuario_id\":\"00000000-0000-0000-0000-000000000000\",\"restaurante_id\":\"$R\",\"platillos\":[{\"platillo_id\":\"$P\",\"cantidad\":1}]}"'
echo "### E1. Cinco pagos simultáneos: un solo cobro"
ID=$(nuevo_pedido)
paso 'for i in 1 2 3 4 5; do curl -s -o /dev/null -w "%{http_code} " -X POST $B/api/pedidos/$ID/pago & done; wait; echo'
paso 'psql_db "SELECT (SELECT count(*) FROM pagos.pagos WHERE pedido_id='"'"'$ID'"'"') AS cobros, (SELECT version FROM pedidos.pedidos WHERE id='"'"'$ID'"'"') AS version"'
echo "### E1/E3. Dos repartidores aceptan a la vez: uno gana (200) y el otro 409"
REP2=$(curl -s -X POST $B/api/repartidores -H "Content-Type: application/json" -d '{"nombre":"Segundo regresion","zona":3}' | $PY -c "$J['id'])")
paso '( curl -s -o /dev/null -w "REP: %{http_code}\n" -X POST $B/api/pedidos/$ID/aceptar -H "Content-Type: application/json" -d "{\"repartidor_id\":\"$REP\"}" & curl -s -o /dev/null -w "REP2: %{http_code}\n" -X POST $B/api/pedidos/$ID/aceptar -H "Content-Type: application/json" -d "{\"repartidor_id\":\"$REP2\"}" & wait )'
echo "### E1. Entrega: código incorrecto (422), cinco correctas a la vez, versión 4"
COD=$(curl -s $B/api/pedidos/$ID | $PY -c "$J['codigo_entrega'])")
paso 'curl -s -o /dev/null -w "%{http_code}\n" -X POST $B/api/pedidos/$ID/entrega -H "Content-Type: application/json" -d "{\"codigo\":\"000000\"}"'
paso 'for i in 1 2 3 4 5; do curl -s -o /dev/null -w "%{http_code} " -X POST $B/api/pedidos/$ID/entrega -H "Content-Type: application/json" -d "{\"codigo\":\"$COD\"}" & done; wait; echo'
paso 'psql_db "SELECT estado, version FROM pedidos.pedidos WHERE id='"'"'$ID'"'"'"'
echo "### E2. Los avisos llegan por RabbitMQ, uno por cambio de estado, y el outbox queda publicado"
sleep 3
paso 'avisos $ID'
paso 'psql_db "SELECT tipo, publicado_en IS NOT NULL AS publicado FROM pedidos.outbox WHERE payload->>'"'"'pedidoId'"'"'='"'"'$ID'"'"' ORDER BY creado_en"'
paso 'docker compose exec -T rabbitmq rabbitmqctl list_queues name messages consumers 2>/dev/null | grep notificaciones'
echo "### E3. Balanceo: 10 consultas por el gateway, X-Instancia"
paso 'for i in $(seq 1 10); do curl -s -D - -o /dev/null "$B/api/repartidores?zona=3" | grep -i x-instancia; done | sort | uniq -c'
echo "### E3. Tres bases separadas"
paso 'docker compose exec -T db psql -U postgres -c "\l" | grep -E "didistribuidores|notificaciones_db|repartidores_db" | cut -c1-40'
echo "### E1/E3. Cancelación por tiempo con reembolso y aviso de retraso (espera 75 s)"
ID2=$(nuevo_pedido); pagar $ID2
sleep 75
paso 'curl -s $B/api/pedidos/$ID2 | $PY -c "import sys,json; p=json.load(sys.stdin); print(p[\"estado\"], p[\"motivo_cancelacion\"])"'
paso 'curl -s $B/api/pagos/$ID2 | $PY -c "$J['"'"'estado'"'"'])"'
paso 'avisos $ID2'
