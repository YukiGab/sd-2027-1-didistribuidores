# Prueba 2: repartidores lento (5 s) y el circuit breaker; después, recuperación sola
paso 'LATENCIA_MS=5000 docker compose up -d repartidores 2>&1 | tail -2'
sleep 10
ID=$(nuevo_pedido); pagar $ID
paso 'for i in 1 2 3 4 5 6; do echo -n "intento $i: "; aceptar_tiempo $ID $REP; done'
paso 'curl -s $B/estado; echo'
paso 'docker compose logs app 2>&1 | grep -E "circuito|\[repartidores\]" | tail -5'
echo "--- recuperación: se quita el retraso"
paso 'docker compose up -d repartidores 2>&1 | tail -2'
sleep 10
paso 'aceptar_tiempo $ID $REP'
sleep 12
paso 'aceptar_tiempo $ID $REP'
paso 'curl -s $B/estado; echo'
paso 'docker compose logs app 2>&1 | grep "circuito" | tail -3'
paso 'estado_pedido $ID'
