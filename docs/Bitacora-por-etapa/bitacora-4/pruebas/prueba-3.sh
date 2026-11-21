# Prueba 3: una copia de repartidores congelada (docker pause): limitación de las llamadas internas por DNS
COPIA=$(docker compose ps -q repartidores | head -1)
paso 'docker pause $COPIA'
paso 'for i in $(seq 1 8); do curl -s -o /dev/null -w "%{http_code} en %{time_total}s\n" "$B/api/pedidos/disponibles?repartidor_id=$REP"; done'
paso 'curl -s $B/estado; echo'
paso 'docker compose logs app 2>&1 | grep -E "\[repartidores\]|circuito" | tail -4'
paso 'docker unpause $COPIA'
