# 📁 database.py
# Módulo central de acceso a datos de SARA
# Todas las operaciones con SQLite pasan por aquí

from config import DB_NAME
import sqlite3
from datetime import datetime



# ──────────────────────────────────────────────
# 🔹 CONEXIÓN
# ──────────────────────────────────────────────

def conectar():
    """
    Retorna una conexión a la base de datos.
    timeout=10 → espera hasta 10 segundos si la BD está ocupada
    en vez de fallar inmediatamente con "database is locked"
    """
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    # Activa WAL mode — permite lecturas simultáneas a escrituras
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# ──────────────────────────────────────────────
# 🔹 CREACIÓN DE TABLAS
# ──────────────────────────────────────────────

def crear_tablas():
    """
    Crea todas las tablas si no existen.
    Seguro para ejecutar múltiples veces.
    """
    with conectar() as conn:
        cursor = conn.cursor()

        # 📚 CONOCIMIENTOS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conocimientos (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        pregunta         TEXT NOT NULL,
        respuesta        TEXT NOT NULL,
        estado           TEXT DEFAULT 'nuevo',
        veces_consultada INTEGER DEFAULT 0,
        vector           TEXT,
       fecha            DATETIME DEFAULT CURRENT_TIMESTAMP
       )

        """)

        # ⚙️ COMANDOS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comandos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre          TEXT NOT NULL,
            palabras_clave  TEXT,
            accion          TEXT NOT NULL,
            tipo            TEXT NOT NULL,
            descripcion     TEXT,
            prioridad       INTEGER DEFAULT 1,
            activo          INTEGER DEFAULT 1,
            veces_usado     INTEGER DEFAULT 0,
            vector          TEXT,
             fecha_creacion  DATETIME DEFAULT CURRENT_TIMESTAMP
          )
        """)

        # 📋 HISTORIAL
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            entrada_original TEXT NOT NULL,
            entrada_limpia   TEXT NOT NULL,
            respuesta        TEXT,
            tipo             TEXT,
            confianza        REAL DEFAULT 0.0,
            fecha            DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 📝 LOGS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo     TEXT NOT NULL,
            mensaje  TEXT NOT NULL,
            detalle  TEXT,
            fecha    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # ✏️ CORRECCIONES
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS correcciones (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            pregunta         TEXT NOT NULL,
            respuesta_antigua TEXT,
            respuesta_nueva  TEXT NOT NULL,
            fecha            DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS acciones_compuestas (
         id          INTEGER PRIMARY KEY AUTOINCREMENT,
        id_comando  INTEGER NOT NULL,
        orden       INTEGER DEFAULT 1,
        accion      TEXT NOT NULL,
        tipo        TEXT NOT NULL,
        descripcion TEXT,
        fecha       DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_comando) REFERENCES comandos(id)
        )
        """)

        # 🧠 INTENCIONES (clave para IA futura)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS intenciones (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            texto_original  TEXT NOT NULL,
            texto_limpio    TEXT NOT NULL,
            tipo            TEXT NOT NULL,
            confianza       REAL DEFAULT 0.0,
            fecha           DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        

        # 👤 USUARIOS (futuro)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre          TEXT NOT NULL,
            fecha_registro  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 🌐 RESULTADOS EXTERNOS (para external_service.py)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resultados_externos (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            query   TEXT NOT NULL,
            resultado TEXT NOT NULL,
            fuente  TEXT DEFAULT 'web',
            fecha   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()


# ──────────────────────────────────────────────
# 🔹 CONOCIMIENTOS
# ──────────────────────────────────────────────

def obtener_conocimientos():
    """Retorna lista de (pregunta, respuesta) de conocimientos activos."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pregunta, respuesta FROM conocimientos")
        return cursor.fetchall()


def guardar_conocimiento(pregunta, respuesta):
    """Inserta un nuevo conocimiento."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conocimientos (pregunta, respuesta)
            VALUES (?, ?)
        """, (pregunta, respuesta))
        conn.commit()


def agregar_pregunta(pregunta, respuesta):
    """Alias semántico de guardar_conocimiento — usado por learning.py."""
    guardar_conocimiento(pregunta, respuesta)


def actualizar_respuesta(pregunta, respuesta_nueva):
    """Actualiza la respuesta de un conocimiento existente y lo marca como corregido."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conocimientos
            SET respuesta = ?, estado = 'corregido'
            WHERE pregunta = ?
        """, (respuesta_nueva, pregunta))
        conn.commit()


def marcar_pregunta_incorrecta(pregunta):
    """Marca un conocimiento como incorrecto para revisión futura."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conocimientos
            SET estado = 'incorrecto'
            WHERE pregunta = ?
        """, (pregunta,))
        conn.commit()


def incrementar_consulta(pregunta):
    """Suma 1 a veces_consultada — útil para detectar preguntas frecuentes."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conocimientos
            SET veces_consultada = veces_consultada + 1
            WHERE pregunta = ?
        """, (pregunta,))
        conn.commit()


# ──────────────────────────────────────────────
# 🔹 COMANDOS
# ──────────────────────────────────────────────

def obtener_comandos():
    """Retorna todos los comandos activos con columnas nombradas."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, palabras_clave, accion,
                   tipo, descripcion, prioridad, activo,
                   veces_usado, fecha_creacion
            FROM comandos
            WHERE activo = 1
            ORDER BY prioridad DESC
        """)
        return cursor.fetchall()


def agregar_comando(nombre, palabras_clave, accion, tipo, descripcion=""):
    """Inserta un nuevo comando."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO comandos (nombre, palabras_clave, accion, tipo, descripcion)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre, palabras_clave, accion, tipo, descripcion))
        conn.commit()


def marcar_comando_incorrecto(nombre):
    """Desactiva un comando marcándolo como inactivo."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE comandos SET activo = 0
            WHERE nombre = ?
        """, (nombre,))
        conn.commit()


def incrementar_uso_comando(id_comando):
    """Suma 1 a veces_usado del comando — para estadísticas futuras."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE comandos
            SET veces_usado = veces_usado + 1
            WHERE id = ?
        """, (id_comando,))
        conn.commit()


# ──────────────────────────────────────────────
# 🔹 HISTORIAL
# ──────────────────────────────────────────────

def guardar_historial(entrada_original, entrada_limpia, respuesta, tipo, confianza=0.0):
    """
    Guarda cada interacción completa.
    Guarda tanto el texto original como el limpio para aprendizaje futuro.
    """
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO historial
                (entrada_original, entrada_limpia, respuesta, tipo, confianza)
            VALUES (?, ?, ?, ?, ?)
        """, (entrada_original, entrada_limpia, respuesta, tipo, confianza))
        conn.commit()


# ──────────────────────────────────────────────
# 🔹 INTENCIONES
# ──────────────────────────────────────────────

def guardar_intencion(texto_original, texto_limpio, tipo, confianza=0.0):
    """
    Guarda cada intención detectada.
    Almacena texto original Y limpio — crítico para entrenamiento futuro.
    """
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO intenciones
                (texto_original, texto_limpio, tipo, confianza)
            VALUES (?, ?, ?, ?)
        """, (texto_original, texto_limpio, tipo, confianza))
        conn.commit()


# ──────────────────────────────────────────────
# 🔹 LOGS
# ──────────────────────────────────────────────

def guardar_log(tipo, mensaje, detalle=""):
    """Log general del sistema."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs (tipo, mensaje, detalle)
            VALUES (?, ?, ?)
        """, (tipo, mensaje, detalle))
        conn.commit()


def guardar_log_comando(registro):
    """
    Log específico de ejecución de comando.
    registro: dict con id_comando, nombre, exito
    """
    mensaje = f"Comando ejecutado: {registro.get('nombre', '?')}"
    detalle = f"id={registro.get('id_comando')} exito={registro.get('exito')}"
    guardar_log("comando", mensaje, detalle)


def guardar_log_pregunta(registro):
    """
    Log específico de interacción con pregunta.
    registro: dict con pregunta, respuesta_usuario, correcta
    """
    mensaje = f"Pregunta procesada: {registro.get('pregunta', '?')}"
    detalle = f"correcta={registro.get('correcta')} respuesta={registro.get('respuesta_usuario')}"
    guardar_log("pregunta", mensaje, detalle)


def guardar_log_error(registro):
    """
    Log específico de error.
    registro: dict con tipo, item, descripcion
    """
    mensaje = f"Error en {registro.get('tipo', '?')}: {registro.get('item', '?')}"
    detalle = registro.get('descripcion', '')
    guardar_log("error", mensaje, detalle)


# ──────────────────────────────────────────────
# 🔹 CORRECCIONES
# ──────────────────────────────────────────────

def guardar_correccion(pregunta, respuesta_antigua, respuesta_nueva):
    """Registra cuando el usuario corrige una respuesta de SARA."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO correcciones
                (pregunta, respuesta_antigua, respuesta_nueva)
            VALUES (?, ?, ?)
        """, (pregunta, respuesta_antigua, respuesta_nueva))
        conn.commit()


# ──────────────────────────────────────────────
# 🔹 RESULTADOS EXTERNOS
# ──────────────────────────────────────────────

def agregar_respuesta_externa(query, resultado, fuente="web"):
    """
    Guarda resultados de búsqueda web o scraping.
    Usado por external_service.py
    """
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO resultados_externos (query, resultado, fuente)
            VALUES (?, ?, ?)
        """, (query, str(resultado), fuente))
        conn.commit()

# ──────────────────────────────────────────────
# 🔹 VECTORES SEMÁNTICOS
# ──────────────────────────────────────────────

def guardar_vector_conocimiento(pregunta, vector):
    """
    Guarda el vector semántico de una pregunta en conocimientos.
    vector: list[float] serializado como JSON string
    """
    import json
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conocimientos
            SET vector = ?
            WHERE pregunta = ?
        """, (json.dumps(vector), pregunta))
        conn.commit()


def guardar_vector_comando(nombre, vector):
    """
    Guarda el vector semántico de un comando.
    """
    import json
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE comandos
            SET vector = ?
            WHERE nombre = ?
        """, (json.dumps(vector), nombre))
        conn.commit()


def obtener_vectores_conocimientos():
    """
    Retorna lista de (pregunta, respuesta, vector) de conocimientos.
    Solo los que tienen vector generado.
    """
    import json
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pregunta, respuesta, vector
            FROM conocimientos
            WHERE vector IS NOT NULL
        """)
        filas = cursor.fetchall()

    resultado = []
    for fila in filas:
        try:
            vector = json.loads(fila["vector"])
            resultado.append((fila["pregunta"], fila["respuesta"], vector))
        except Exception:
            continue
    return resultado


def obtener_vectores_comandos():
    """
    Retorna lista de (nombre, vector, fila_completa) de comandos activos.
    Solo los que tienen vector generado.
    """
    import json
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, palabras_clave, accion,
                   tipo, descripcion, prioridad, activo,
                   veces_usado, vector
            FROM comandos
            WHERE activo = 1 AND vector IS NOT NULL
        """)
        filas = cursor.fetchall()

    resultado = []
    for fila in filas:
        try:
            vector = json.loads(fila["vector"])
            resultado.append((dict(fila), vector))
        except Exception:
            continue
    return resultado

# ──────────────────────────────────────────────
# 🔹 MIGRACIONES — Agregar sin borrar BD
# ──────────────────────────────────────────────

def migrar_bd():
    """
    Agrega columnas y tablas nuevas a una BD existente
    sin perder datos.
    Se ejecuta de forma segura — si la columna ya existe
    SQLite lanza un error que capturamos y ignoramos.
    """
    with conectar() as conn:
        cursor = conn.cursor()

        try:

            cursor.execute("""

                CREATE TABLE IF NOT EXISTS acciones_compuestas (

                    id          INTEGER PRIMARY KEY AUTOINCREMENT,

                    id_comando  INTEGER NOT NULL,

                    orden       INTEGER DEFAULT 1,

                    accion      TEXT NOT NULL,

                    tipo        TEXT NOT NULL,

                    descripcion TEXT,

                    fecha       DATETIME DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (id_comando) REFERENCES comandos(id)

                )

            """)

            print("✅ Tabla 'acciones_compuestas' creada.")

        except Exception:

            pass

        # ── Columna resultado en intenciones ──

        try:

            cursor.execute("""

                ALTER TABLE intenciones

                ADD COLUMN resultado TEXT DEFAULT 'pendiente'

            """)

            print("✅ Columna 'resultado' agregada a intenciones.")

        except Exception:

            pass  # Ya existe — ignorar

        # ── Tabla interacciones_sociales ──

        try:

            cursor.execute("""

                CREATE TABLE IF NOT EXISTS interacciones_sociales (

                    id          INTEGER PRIMARY KEY AUTOINCREMENT,

                    texto       TEXT NOT NULL,

                    tipo_social TEXT NOT NULL,

                    fecha       DATETIME DEFAULT CURRENT_TIMESTAMP

                )

            """)

            print("✅ Tabla 'interacciones_sociales' creada.")

        except Exception:

            pass

        conn.commit()


# ──────────────────────────────────────────────
# 🔹 INTENCIONES — actualizar resultado
# ──────────────────────────────────────────────

def actualizar_resultado_intencion(texto_limpio, resultado):
    """
    Marca el resultado de una intención guardada.

    texto_limpio: texto normalizado de la intención
    resultado:    "correcto" | "sin_respuesta" | "corregido"
    """
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE intenciones
            SET resultado = ?
            WHERE texto_limpio = ?
            AND fecha = (
                SELECT MAX(fecha) FROM intenciones
                WHERE texto_limpio = ?
            )
        """, (resultado, texto_limpio, texto_limpio))
        conn.commit()


# ──────────────────────────────────────────────
# 🔹 INTERACCIONES SOCIALES
# ──────────────────────────────────────────────

def guardar_interaccion_social(texto, tipo_social):
    """
    Guarda una interacción social en BD.

    texto:       lo que escribió el usuario
    tipo_social: saludo | despedida | agradecimiento |
                 afirmacion | negacion | elogio |
                 insulto | correccion | corta
    """
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO interacciones_sociales (texto, tipo_social)
            VALUES (?, ?)
        """, (texto, tipo_social))
        conn.commit()


def obtener_stats_sociales():
    """
    Retorna conteo de interacciones sociales por tipo.
    Útil para /stats
    """
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tipo_social, COUNT(*) as total
            FROM interacciones_sociales
            GROUP BY tipo_social
            ORDER BY total DESC
        """)
        return cursor.fetchall()
    
def crear_tablas():
    """
    Crea todas las tablas si no existen.
    Seguro para ejecutar múltiples veces.
    """
    with conectar() as conn:
        cursor = conn.cursor()
        # ... todo el código existente igual ...
        conn.commit()

    # ── NUEVO: Aplicar migraciones ──
    migrar_bd()

# ──────────────────────────────────────────────
# 🔹 ACCIONES COMPUESTAS
# ──────────────────────────────────────────────

def guardar_accion_compuesta(id_comando, orden, accion, tipo, descripcion=""):
    """Guarda una acción individual de un comando compuesto."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO acciones_compuestas
                (id_comando, orden, accion, tipo, descripcion)
            VALUES (?, ?, ?, ?, ?)
        """, (id_comando, orden, accion, tipo, descripcion))
        conn.commit()


def obtener_acciones_compuestas(id_comando):
    """
    Retorna todas las acciones de un comando compuesto
    ordenadas por su campo orden.
    """
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, orden, accion, tipo, descripcion
            FROM acciones_compuestas
            WHERE id_comando = ?
            ORDER BY orden ASC
        """, (id_comando,))
        return cursor.fetchall()


def es_comando_compuesto(id_comando):
    """
    Retorna True si el comando tiene acciones compuestas guardadas.
    """
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM acciones_compuestas
            WHERE id_comando = ?
        """, (id_comando,))
        fila = cursor.fetchone()
        return fila["total"] > 0


def eliminar_acciones_compuestas(id_comando):
    """Elimina todas las acciones de un comando compuesto."""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM acciones_compuestas
            WHERE id_comando = ?
        """, (id_comando,))
        conn.commit()
# ──────────────────────────────────────────────
# 🔹 INICIALIZACIÓN
# ──────────────────────────────────────────────

if __name__ == "__main__":
    crear_tablas()
    print("Base de datos y tablas creadas correctamente.")

