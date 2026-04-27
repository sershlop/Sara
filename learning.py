# 📁 learning.py
# Módulo de aprendizaje de SARA
# Responsable de: guardar nuevos conocimientos, manejar correcciones
# y preparar datos para el aprendizaje automático futuro
from config import UMBRAL_DUPLICADO
from utils import normalizar_texto, similitud
from database import (
    guardar_conocimiento,
    agregar_pregunta,
    agregar_comando,
    actualizar_respuesta,
    marcar_pregunta_incorrecta,
    marcar_comando_incorrecto,
    guardar_correccion,
    obtener_conocimientos,
    obtener_comandos,
    guardar_vector_conocimiento,
    guardar_vector_comando
)
import embeddings
import logger

TIPOS_COMANDOS_VALIDOS = {"web", "app", "sistema"}
ACCION_DUPLICADA = "duplicada"
ACCION_GUARDADA = "guardada"
ACCION_CORREGIDA = "corregida"
ACCION_MARCADA = "marcada"
ACCION_ERROR = "error"



# ──────────────────────────────────────────────
# 🔹 VERIFICACIÓN DE DUPLICADOS
# ──────────────────────────────────────────────

def _ya_existe_pregunta(pregunta_nueva):
    """
    Verifica si una pregunta similar ya existe en la BD.
    Retorna: (existe: bool, pregunta_similar: str | None, score: float)

    Uso interno — evita duplicados en conocimientos.
    """
    conocimientos = obtener_conocimientos()
    pregunta_norm = normalizar_texto(pregunta_nueva)

    mejor_score    = 0.0
    mejor_pregunta = None

    for fila in conocimientos:
        score = similitud(pregunta_norm, normalizar_texto(fila["pregunta"]))
        if score > mejor_score:
            mejor_score    = score
            mejor_pregunta = fila["pregunta"]

    existe = mejor_score >= UMBRAL_DUPLICADO
    return existe, mejor_pregunta, mejor_score


def _ya_existe_comando(nombre_nuevo):
    """
    Verifica si un comando similar ya existe en la BD.
    Retorna: (existe: bool, nombre_similar: str | None, score: float)
    """
    comandos   = obtener_comandos()
    nombre_norm = normalizar_texto(nombre_nuevo)

    mejor_score  = 0.0
    mejor_nombre = None

    for cmd in comandos:
        score = similitud(nombre_norm, normalizar_texto(cmd["nombre"]))
        if score > mejor_score:
            mejor_score  = score
            mejor_nombre = cmd["nombre"]

    existe = mejor_score >= UMBRAL_DUPLICADO
    return existe, mejor_nombre, mejor_score


# ──────────────────────────────────────────────
# 🔹 APRENDER NUEVA PREGUNTA
# ──────────────────────────────────────────────

def aprender_pregunta(pregunta, respuesta):
    """
    Agrega una nueva pregunta y respuesta a la BD.

    Flujo:
    1. Valida que los datos no estén vacíos
    2. Verifica que no exista una pregunta similar
    3. Si no existe → la guarda
    4. Si existe → sugiere actualizar en vez de duplicar

    Retorna: dict con resultado de la operación
    """
    try:
        # 1. Validación
        if not pregunta or not pregunta.strip():
            return _resultado(False, "error", "La pregunta no puede estar vacía.")
        if not respuesta or not respuesta.strip():
            return _resultado(False, "error", "La respuesta no puede estar vacía.")

        # 2. Verificar duplicado
        existe, similar, score = _ya_existe_pregunta(pregunta)

        if existe:
            logger.warning(
                "learning",
                f"Pregunta duplicada detectada (similitud: {round(score*100,1)}%)",
                f"Nueva: '{pregunta}' | Similar: '{similar}'"
            )
            return _resultado(
                False,
                ACCION_DUPLICADA,
                f"Ya existe una pregunta similar ({round(score*100,1)}% de similitud): '{similar}'"
            )

        # 3. Guardar
        agregar_pregunta(pregunta.strip(), respuesta.strip())
        if embeddings.esta_disponible():
            vector = embeddings.vector_desde_texto(
                normalizar_texto(pregunta.strip())
            )
            if vector:
                guardar_vector_conocimiento(pregunta.strip(), vector)
                logger.debug("learning", f"Vector generado para: '{pregunta[:40]}'")

        logger.info("learning", f"Nueva pregunta aprendida: '{pregunta[:50]}'")
        return _resultado(True, ACCION_GUARDADA, "Pregunta aprendida correctamente.")

    except Exception as e:
        logger.log_excepcion("learning", pregunta, e)
        return _resultado(False, "error", f"Error al aprender pregunta: {e}")


# ──────────────────────────────────────────────
# 🔹 APRENDER NUEVO COMANDO
# ──────────────────────────────────────────────

def aprender_comando(nombre, palabras_clave, accion, tipo, descripcion=""):
    """
    Agrega un nuevo comando a la BD.

    tipo válidos: "web", "app", "sistema"

    Retorna: dict con resultado de la operación
    """
    try:
        # 1. Validación
        if not nombre or not nombre.strip():
            return _resultado(False, "error", "El nombre del comando no puede estar vacío.")
        if not accion or not accion.strip():
            return _resultado(False, "error", "La acción del comando no puede estar vacía.")

        if tipo not in TIPOS_COMANDOS_VALIDOS:
            return _resultado(
                False,
                ACCION_ERROR,
                f"Tipo inválido '{tipo}'. Debe ser: {', '.join(TIPOS_COMANDOS_VALIDOS)}"
            )

        # 2. Verificar duplicado
        existe, similar, score = _ya_existe_comando(nombre)

        if existe:
            logger.warning(
                "learning",
                f"Comando duplicado detectado (similitud: {round(score*100,1)}%)",
                f"Nuevo: '{nombre}' | Similar: '{similar}'"
            )
            return _resultado(
                False,
                ACCION_DUPLICADA,
                f"Ya existe un comando similar ({round(score*100,1)}% de similitud): '{similar}'"
            )

        # 3. Guardar
        agregar_comando(
            nombre.strip(),
            palabras_clave.strip() if palabras_clave else "",
            accion.strip(),
            tipo,
            descripcion.strip() if descripcion else ""
        )
        if embeddings.esta_disponible():
            texto_cmd = normalizar_texto(nombre.strip())
            vector    = embeddings.vector_desde_texto(texto_cmd)
            if vector:
                guardar_vector_comando(nombre.strip(), vector)
                logger.debug("learning", f"Vector generado para comando: '{nombre}'")
        logger.info("learning", f"Nuevo comando aprendido: '{nombre}'")
        return _resultado(True, ACCION_GUARDADA, "Comando aprendido correctamente.")

    except Exception as e:
        logger.log_excepcion("learning", nombre, e)
        return _resultado(False, "error", f"Error al aprender comando: {e}")


# ──────────────────────────────────────────────
# 🔹 MODO APRENDIZAJE
# ──────────────────────────────────────────────

def modo_aprendizaje(entrada_original):
    """
    Función para activar el modo enseñanza cuando el usuario elige 
    "enséñame tú" después de que Grok proponga una respuesta o comando.
    """
    try:
        print("\n🧠 Modo enseñanza activado")
        print(f"   Pregunta/Comando: {entrada_original}")
        
        es_pregunta = True  # Por defecto asumimos pregunta
        
        # Detectar si parece un comando
        if any(palabra in entrada_original.lower() for palabra in ["abre", "abrir", "ejecuta", "pon", "reproduce"]):
            es_pregunta = False

        if es_pregunta:
            print("   Escribe la respuesta correcta para esta pregunta:")
            respuesta = input("   → ").strip()
            
            if respuesta and respuesta.lower() not in ["cancelar", "no", "cancel"]:
                resultado = aprender_pregunta(entrada_original, respuesta)
                if resultado["exito"]:
                    print("   ✅ ¡Pregunta aprendida correctamente!")
                else:
                    print(f"   ⚠️  {resultado['mensaje']}")
            else:
                print("   Aprendizaje cancelado.")
                
        else:
            # Flujo simplificado para comandos
            print("   ¿Cómo quieres llamar a este comando?")
            nombre = input("   Nombre: ").strip()
            
            if nombre:
                print("   ¿Qué acción debe ejecutar? (URL, comando del sistema, etc.)")
                accion = input("   Acción: ").strip()
                
                if accion:
                    tipo = "app" if any(x in accion.lower() for x in ["calc", "cmd", "notepad"]) else "web"
                    resultado = aprender_comando(
                        nombre=nombre,
                        palabras_clave=entrada_original.lower(),
                        accion=accion,
                        tipo=tipo,
                        descripcion=f"Comando aprendido vía Grok + usuario: {entrada_original}"
                    )
                    if resultado["exito"]:
                        print(f"   ✅ Comando '{nombre}' guardado correctamente!")
                    else:
                        print(f"   ⚠️  {resultado['mensaje']}")
                else:
                    print("   Acción vacía. Comando no guardado.")
            else:
                print("   Nombre vacío. Comando no guardado.")
                
    except Exception as e:
        logger.log_excepcion("learning", "modo_aprendizaje", e)
        print("   Ocurrió un error en el modo aprendizaje.")


# ──────────────────────────────────────────────
# 🔹 CORRECCIONES
# ──────────────────────────────────────────────

def corregir_pregunta(pregunta, respuesta_nueva):
    """
    Corrige la respuesta de una pregunta existente.

    Flujo:
    1. Valida datos
    2. Guarda la corrección en tabla correcciones (historial de cambios)
    3. Actualiza la respuesta en conocimientos
    4. Registra el evento en logger

    Retorna: dict con resultado
    """
    try:
        if not pregunta or not respuesta_nueva:
            return _resultado(False, "error", "Pregunta y respuesta nueva son obligatorias.")

        # Guardar registro de corrección (historial)
        guardar_correccion(pregunta.strip(), None, respuesta_nueva.strip())

        # Actualizar en conocimientos
        actualizar_respuesta(pregunta.strip(), respuesta_nueva.strip())

        logger.info(
            "learning",
            f"Corrección aplicada: '{pregunta[:50]}'",
            f"Nueva respuesta: '{respuesta_nueva[:50]}'"
        )
        return _resultado(True, ACCION_CORREGIDA, "Respuesta corregida correctamente.")

    except Exception as e:
        logger.log_excepcion("learning", pregunta, e)
        return _resultado(False, ACCION_ERROR, f"Error al corregir: {e}")


def marcar_error(tipo, item):
    """
    Marca un conocimiento o comando como incorrecto.

    tipo: "pregunta" | "comando"
    item: texto de la pregunta o nombre del comando

    Retorna: dict con resultado
    """
    try:
        if tipo == "pregunta":
            marcar_pregunta_incorrecta(item)
            logger.warning("learning", f"Pregunta marcada incorrecta: '{item[:50]}'")
            return _resultado(True, ACCION_MARCADA, "Pregunta marcada como incorrecta.")

        elif tipo == "comando":
            marcar_comando_incorrecto(item)
            logger.warning("learning", f"Comando desactivado: '{item[:50]}'")
            return _resultado(True, ACCION_MARCADA, "Comando marcado como incorrecto y desactivado.")

        else:
            return _resultado(False, ACCION_ERROR, f"Tipo inválido: '{tipo}'. Usa 'pregunta' o 'comando'.")

    except Exception as e:
        logger.log_excepcion("learning", item, e)
        return _resultado(False, ACCION_ERROR, f"Error al marcar error: {e}")


# ──────────────────────────────────────────────
# 🔹 ANÁLISIS DE DATOS (PREPARACIÓN PARA IA)
# ──────────────────────────────────────────────

def obtener_estadisticas():
    """
    Retorna estadísticas básicas del conocimiento actual de SARA.
    Útil para monitorear el crecimiento del sistema.

    Retorna: dict con conteos
    """
    try:
        conocimientos = obtener_conocimientos()
        comandos      = obtener_comandos()

        stats = {
            "total_conocimientos": len(conocimientos),
            "total_comandos":      len(comandos),
        }

        logger.debug("learning", f"Estadísticas: {stats}")
        return stats

    except Exception as e:
        logger.log_excepcion("learning", "obtener_estadisticas", e)
        return {}


def verificar_similitud(texto1, texto2):
    """
    Expone la comparación de similitud normalizada.
    Útil para pruebas y diagnóstico externo.
    Ambos textos se normalizan antes de comparar.

    Retorna: float entre 0.0 y 1.0
    """
    return similitud(normalizar_texto(texto1), normalizar_texto(texto2))


# ──────────────────────────────────────────────
# 🔹 HELPER INTERNO
# ──────────────────────────────────────────────

def _resultado(exito, accion, mensaje):
    """
    Construye el dict de respuesta estándar de learning.py
    Uso interno.
    """
    return {
        "exito":   exito,
        "accion":  accion,
        "mensaje": mensaje
    }
def aprender_comando_compuesto(nombre, palabras_clave, acciones, descripcion=""):
    """
    Guarda un comando compuesto con múltiples acciones.

    nombre:        nombre del comando
    palabras_clave: palabras que activan el comando
    acciones:      list[dict] con orden, accion, tipo, descripcion
    descripcion:   descripción general del comando

    Retorna: dict(exito, accion, mensaje)
    """
    try:
        # Validaciones
        if not nombre or not nombre.strip():
            return _resultado(False, "error", "El nombre no puede estar vacío.")

        if not acciones:
            return _resultado(False, "error", "Debe tener al menos una acción.")

        # Verificar duplicado
        existe, similar, score = _ya_existe_comando(nombre)
        if existe:
            return _resultado(
                False,
                "duplicada",
                f"Ya existe un comando similar: '{similar}'"
            )

        # Guardar comando principal en tabla comandos
        # accion = "COMPUESTO" indica que tiene múltiples acciones
        agregar_comando(
            nombre.strip(),
            palabras_clave.strip() if palabras_clave else "",
            "COMPUESTO",
            "compuesto",
            descripcion.strip() if descripcion else f"Comando compuesto: {nombre}"
        )

        # Obtener el ID del comando recién guardado
        from database import conectar
        with conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM comandos
                WHERE nombre = ?
                ORDER BY id DESC LIMIT 1
            """, (nombre.strip(),))
            fila       = cursor.fetchone()
            id_comando = fila["id"] if fila else None

        if not id_comando:
            return _resultado(False, "error", "No se pudo obtener el ID del comando.")

        # Guardar cada acción individual
        from database import guardar_accion_compuesta
        for accion in acciones:
            guardar_accion_compuesta(
                id_comando,
                accion.get("orden", 1),
                accion.get("accion", ""),
                accion.get("tipo", "app"),
                accion.get("descripcion", "")
            )

        # Generar vector semántico
        if embeddings.esta_disponible():
            vector = embeddings.vector_desde_texto(normalizar_texto(nombre.strip()))
            if vector:
                from database import guardar_vector_comando
                guardar_vector_comando(nombre.strip(), vector)

        logger.info(
            "learning",
            f"Comando compuesto guardado: '{nombre}'",
            f"{len(acciones)} acciones"
        )

        return _resultado(
            True,
            "guardada",
            f"Comando '{nombre}' guardado con {len(acciones)} acciones."
        )

    except Exception as e:
        logger.log_excepcion("learning", nombre, e)
        return _resultado(False, "error", f"Error al guardar comando compuesto: {e}")