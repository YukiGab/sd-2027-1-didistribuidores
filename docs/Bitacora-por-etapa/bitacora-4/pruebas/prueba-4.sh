# Prueba 4: repartidores caído por completo: 503 rápido, circuito abierto; al volver se cierra
paso 'curl -s $B/estado; echo'   # se parte con el circuito CERRADO
paso 'docker compose stop repartidores 2>&1 | tail -2'
ID=$(nuevo_pedido); pagar $ID
paso 'estado_pedido $ID'
paso 'for i in 1 2 3 4 5; do echo -n "intento $i: "; aceptar_tiempo $ID $REP; done'
paso 'curl -s -X POST $B/api/pedidos/$ID/aceptar -H "Content-Type: application/json" -d "{\"repartidor_id\":\"$REP\"}"; echo'
paso 'curl -s $B/estado; echo'
paso 'docker compose start repartidores 2>&1 | tail -2'
sleep 15
paso 'aceptar_tiempo $ID $REP'
paso 'curl -s $B/estado; echo'
