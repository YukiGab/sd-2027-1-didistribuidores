# Prueba 5: el núcleo muere (kill, sin apagado ordenado) justo después de confirmar un pago con RabbitMQ apagado
paso 'docker compose stop rabbitmq 2>&1 | tail -1'
ID=$(nuevo_pedido); pagar $ID
paso 'estado_pedido $ID'
paso 'curl -s $B/estado; echo'
paso 'docker compose kill app 2>&1 | tail -1'
paso 'docker compose start rabbitmq 2>&1 | tail -1'
sleep 30
paso 'docker compose up -d app 2>&1 | tail -1'
sleep 25
paso 'curl -s $B/estado; echo'
paso 'avisos $ID'
