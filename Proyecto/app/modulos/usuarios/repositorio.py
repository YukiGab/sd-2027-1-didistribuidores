# Capa de persistencia: solo SQL. No decide nada, solo guarda y consulta.
# Recibe la conexión desde el servicio, para que el servicio controle la transacción.
 
 
def crear(conn, nombre, zona):
    return conn.execute(
        """
        INSERT INTO usuarios.usuarios (nombre, zona)
        VALUES (%s, %s)
        RETURNING id, nombre, zona, creado_en
        """,
        (nombre, zona),
    ).fetchone()
 
 
def obtener(conn, usuario_id):
    return conn.execute(
        "SELECT id, nombre, zona, creado_en FROM usuarios.usuarios WHERE id = %s",
        (usuario_id,),
    ).fetchone()
 