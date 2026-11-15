import os

# Base propia de repartidores (distinta a la del núcleo y a la de notificaciones)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_NAME = os.getenv("DB_NAME", "repartidores_db")

DB_CONNINFO = (
    f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
    f"user={DB_USER} password={DB_PASS}"
)

# Solo para pruebas: retraso artificial (en milisegundos) antes de contestar cualquier petición,
# para comprobar que el núcleo corta la espera con su tiempo límite. En producción vale 0.
LATENCIA_MS = int(os.getenv("LATENCIA_MS", "0"))
