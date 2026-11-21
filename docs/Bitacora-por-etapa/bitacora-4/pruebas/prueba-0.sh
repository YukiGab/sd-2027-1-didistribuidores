# Prueba 0: el sistema levanta y /estado muestra el circuito cerrado y el outbox vacío
paso 'docker compose ps --format "table {{.Service}}\t{{.Status}}"'
paso 'curl -s $B/salud; echo'
paso 'curl -s $B/estado; echo'
