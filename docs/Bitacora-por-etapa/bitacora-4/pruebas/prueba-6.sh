# Prueba 6: PostgreSQL se reinicia y los servicios se recuperan sin reiniciarse (pool con check_connection)
paso 'docker compose restart db 2>&1 | tail -1'
sleep 20
paso 'curl -s $B/salud; echo'
ID=$(nuevo_pedido); pagar $ID
paso 'echo "pedido $ID: $(estado_pedido $ID)"'
sleep 3
paso 'avisos $ID'
paso 'curl -s "$B/api/repartidores?zona=3" | head -c 120; echo'
paso 'docker compose ps --format "table {{.Service}}\t{{.Status}}"'
