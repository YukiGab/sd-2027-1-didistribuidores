# Prueba 7: el gateway se cae; desde afuera nadie entra, pero los servicios siguen hablándose
paso 'docker compose stop traefik 2>&1 | tail -1'
paso 'curl -s -o /dev/null -w "%{http_code}\n" $B/salud'
paso 'docker compose exec -T app python -c "import httpx; print(httpx.get('"'"'http://repartidores:8000/salud'"'"').json())"'
paso 'docker compose start traefik 2>&1 | tail -1'
sleep 5
paso 'curl -s $B/salud; echo'
