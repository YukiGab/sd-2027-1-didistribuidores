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

# Guardar los eventos en pedidos.outbox (la tabla la crea db/03-outbox.sql)
OUTBOX_ACTIVO = os.getenv("OUTBOX_ACTIVO", "0") == "1"

# --- Etapa 2: publicación de los eventos del outbox a RabbitMQ ---
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
PUBLICADOR_ACTIVO = os.getenv("PUBLICADOR_ACTIVO", "0") == "1"
PUBLICADOR_INTERVALO_SEG = float(os.getenv("PUBLICADOR_INTERVALO_SEG", "1"))  # espera si no hay pendientes
PUBLICADOR_LOTE = int(os.getenv("PUBLICADOR_LOTE", "50"))                      # eventos por vuelta
REINTENTO_SEG = float(os.getenv("REINTENTO_SEG", "3"))                         # espera tras un error
