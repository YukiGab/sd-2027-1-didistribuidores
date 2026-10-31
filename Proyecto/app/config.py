import os

# Conexión a la base (en Docker, DB_HOST vale "db", el nombre del servicio en el compose)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_NAME = os.getenv("DB_NAME", "didistribuidores")

DB_CONNINFO = (
    f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
    f"user={DB_USER} password={DB_PASS}"
)

# Relojes del pedido, en segundos (valores normales; en la demo se bajan desde el compose)
TIMEOUT_PAGO_SEG = int(os.getenv("TIMEOUT_PAGO_SEG", "600"))
TIMEOUT_ASIGNACION_SEG = int(os.getenv("TIMEOUT_ASIGNACION_SEG", "1200"))

# Cada cuántos segundos revisa la tarea de timeouts si hay pedidos vencidos
REVISION_TIMEOUTS_SEG = int(os.getenv("REVISION_TIMEOUTS_SEG", "5"))