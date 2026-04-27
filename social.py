# 📁 social.py
# Módulo de respuestas sociales de SARA
# Maneja saludos, despedidas, agradecimientos y entradas cortas
# Se ejecuta ANTES de brain.py — no toca BD ni contexto
# Respuestas variadas para no sonar repetitiva
from config import MAX_PALABRAS_CORTAS
import random
from database import guardar_interaccion_social
from utils import normalizar_texto
import logger

# ──────────────────────────────────────────────
# 🔹 CONFIGURACIÓN
# ──────────────────────────────────────────────

# Longitud máxima de palabras para considerar "entrada corta"


# ──────────────────────────────────────────────
# 🔹 PATRONES DE ENTRADAS SOCIALES
# ──────────────────────────────────────────────

SALUDOS = {
    "hola", "hello", "hi", "hey", "buenas", "buenos dias",
    "buenos tardes", "buenas noches", "buen dia", "buenas tardes",
    "que tal", "que onda", "que pedo", "que hay", "que hubo",
    "como estas", "como esta", "como andas", "como te va",
    "como estas sara", "hola sara", "hey sara", "buenas sara",
    "saludos", "alo", "bueno"
}

DESPEDIDAS = {
    "adios", "hasta luego", "bye", "chao", "chau",
    "nos vemos", "hasta pronto", "hasta manana",
    "me voy", "ahi nos vemos", "cuídate", "cuidate",
    "hasta la proxima", "bye bye"
}

AGRADECIMIENTOS = {
    "gracias", "muchas gracias", "thank you", "thanks",
    "te lo agradezco", "muy amable", "genial gracias",
    "perfecto gracias", "ok gracias", "bien gracias",
    "excelente gracias", "de lujo gracias"
}

AFIRMACIONES = {
    "si", "sip", "yes", "claro", "ok", "okey", "okay",
    "dale", "va", "sale", "entendido", "perfecto",
    "de acuerdo", "está bien", "esta bien", "andale",
    "simon", "nel", "pos si", "efectivamente"
}

NEGACIONES = {
    "no", "nel", "nop", "nope", "para nada",
    "negativo", "de ninguna manera", "no gracias"
}

ELOGIOS = {
    "eres buena", "que inteligente", "muy bien sara",
    "bien hecho", "excelente sara", "que lista",
    "me gustas sara", "eres util", "buen trabajo",
    "te pasas", "chida", "chido", "cool", "gracias"
}

INSULTOS_LEVES = {
    "tonto", "tonta", "mensa", "menso", "inutil",
    "no sirves", "que mala eres", "estas mal"
}


# ──────────────────────────────────────────────
# 🔹 RESPUESTAS VARIADAS
# ──────────────────────────────────────────────

RESPUESTAS_SALUDO = [
    "¡Hola! ¿En qué puedo ayudarte?",
    "¡Buenas! Estoy lista para ayudarte.",
    "¡Hola! ¿Qué necesitas saber?",
    "¡Hey! ¿Cómo puedo ayudarte hoy?",
    "¡Hola! Dime en qué te puedo ayudar."
]

RESPUESTAS_DESPEDIDA = [
    "¡Hasta luego! Fue un gusto ayudarte.",
    "¡Nos vemos! Aquí estaré cuando me necesites.",
    "¡Cuídate! Vuelve cuando quieras.",
    "¡Adiós! Fue un placer.",
    "¡Hasta la próxima!"
]

RESPUESTAS_AGRADECIMIENTO = [
    "¡Con gusto! ¿Hay algo más en que pueda ayudarte?",
    "¡Para eso estoy! ¿Algo más?",
    "¡De nada! Es un placer ayudarte.",
    "¡No hay de qué! ¿Necesitas algo más?",
    "¡Claro que sí! ¿En qué más te puedo ayudar?"
]

RESPUESTAS_AFIRMACION = [
    "Entendido. ¿En qué más te puedo ayudar?",
    "De acuerdo. ¿Hay algo más?",
    "Perfecto. Dime si necesitas algo más.",
    "¡Listo! ¿Algo más en que pueda ayudarte?"
]

RESPUESTAS_NEGACION = [
    "Está bien. Aquí estaré si me necesitas.",
    "De acuerdo. Dime si cambias de opinión.",
    "Sin problema. ¿Hay algo más en que pueda ayudar?",
    "Entendido. ¿Necesitas algo más?"
]

RESPUESTAS_ELOGIO = [
    "¡Gracias! Hago mi mejor esfuerzo.",
    "¡Qué amable! Seguiré aprendiendo para ayudarte mejor.",
    "¡Muchas gracias! ¿En qué más te puedo ayudar?",
    "¡Gracias! Eso me motiva a seguir mejorando."
]

RESPUESTAS_INSULTO = [
    "Entiendo tu frustración. ¿En qué puedo mejorar?",
    "Lo siento si no pude ayudarte bien. ¿Intentamos de nuevo?",
    "Haré mi mejor esfuerzo para mejorar. ¿Qué necesitas?"
]

RESPUESTAS_CORTA_SIN_TEMA = [
    "¿Puedes darme más detalles?",
    "No entendí bien. ¿Puedes explicarte un poco más?",
    "¿Podrías ser más específico?",
    "Necesito un poco más de información para ayudarte."
]
CORRECCIONES = {
    "eso esta mal", "estas mal", "te equivocaste",
    "no es correcto", "eso es incorrecto", "error",
    "no es asi", "incorrecto", "eso no es",
    "no es eso", "esta mal", "te equivocas",
    "eso no es correcto", "no", "falso",
    "no es verdad", "eso no es verdad",
    "corrijo", "correccion", "en realidad",
    "en realidad es", "lo correcto es",
    "deberia ser", "no es exactamente"
}


# ──────────────────────────────────────────────
# 🔹 FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────────
def detectar_entrada_social(texto):
    """
    Detecta si el texto es una entrada social.
    Retorna: (es_social: bool, respuesta: str)
    """
    if not texto or not texto.strip():
        return False, ""

    texto_norm = normalizar_texto(texto)

    if texto_norm in SALUDOS or _empieza_con_saludo(texto_norm):
        _registrar("saludo", texto)
        return True, random.choice(RESPUESTAS_SALUDO)

    if texto_norm in DESPEDIDAS:
        _registrar("despedida", texto)
        return True, random.choice(RESPUESTAS_DESPEDIDA)

    if texto_norm in AGRADECIMIENTOS or _contiene_agradecimiento(texto_norm):
        _registrar("agradecimiento", texto)
        return True, random.choice(RESPUESTAS_AGRADECIMIENTO)

    if texto_norm in AFIRMACIONES:
        _registrar("afirmacion", texto)
        return True, random.choice(RESPUESTAS_AFIRMACION)

    if texto_norm in NEGACIONES:
        _registrar("negacion", texto)
        return True, random.choice(RESPUESTAS_NEGACION)

    if texto_norm in ELOGIOS or _contiene_elogio(texto_norm):
        _registrar("elogio", texto)
        return True, random.choice(RESPUESTAS_ELOGIO)

    if texto_norm in INSULTOS_LEVES or _contiene_insulto(texto_norm):
        _registrar("insulto", texto)
        return True, random.choice(RESPUESTAS_INSULTO)

    if _es_entrada_corta_sin_tema(texto_norm.split()):
        _registrar("corta", texto)
        return True, random.choice(RESPUESTAS_CORTA_SIN_TEMA)

    return False, ""


def _registrar(tipo_social, texto):
    """
    Guarda la interacción social en BD.
    Uso interno — no llamar desde fuera.
    """
    try:
        guardar_interaccion_social(texto, tipo_social)
        logger.debug("social", f"{tipo_social} registrado: '{texto[:30]}'")
    except Exception as e:
        logger.error("social", f"Error registrando social: {e}")

# ──────────────────────────────────────────────
# 🔹 DETECCIONES AUXILIARES
# ──────────────────────────────────────────────

def _empieza_con_saludo(texto):
    """
    Detecta saludos al inicio aunque vengan con más texto.
    "hola sara como estas" → True
    """
    SALUDOS_INICIO = (
        "hola ", "hey ", "buenas ", "buenos ",
        "que tal ", "que onda ", "como estas "
    )
    for saludo in SALUDOS_INICIO:
        if texto.startswith(saludo):
            return True
    return False


def _contiene_agradecimiento(texto):
    """
    Detecta agradecimientos aunque vengan con más texto.
    "muchas gracias sara" → True
    """
    PALABRAS_GRACIAS = ("gracias", "agradezco", "thank")
    for palabra in PALABRAS_GRACIAS:
        if palabra in texto.split():
            return True
    return False


def _contiene_elogio(texto):
    """Detecta elogios parciales."""
    PALABRAS_ELOGIO = ("inteligente", "lista", "util", "chida", "buena sara")
    for palabra in PALABRAS_ELOGIO:
        if palabra in texto:
            return True
    return False


def _contiene_insulto(texto):
    """Detecta insultos leves parciales."""
    PALABRAS_INSULTO = ("inutil", "tonta", "mensa", "no sirves")
    for palabra in PALABRAS_INSULTO:
        if palabra in texto:
            return True
    return False

def es_correccion(texto):
    """
    Detecta si el usuario está corrigiendo la última respuesta de SARA.
    Retorna: True si es una corrección
    """
    texto_norm = normalizar_texto(texto)

    # Coincidencia exacta
    if texto_norm in CORRECCIONES:
        return True

    # Coincidencia parcial — contiene palabra clave de corrección
    PALABRAS_CORRECCION = (
        "mal", "incorrecto", "equivocaste", "error",
        "falso", "no es", "correccion", "en realidad"
    )
    for palabra in PALABRAS_CORRECCION:
        if palabra in texto_norm.split():
            return True

    return False

def _es_entrada_corta_sin_tema(palabras):
    """
    Detecta entradas cortas que no tienen tema identificable.
    No aplica si la entrada corta ES un comando o pregunta válida.

    "ok"     → True  (sin tema)
    "si"     → False (ya manejado como afirmación)
    "luna"   → False (tiene tema — podría ser comando)
    "que"    → True  (incompleta)
    """
    # Solo aplicar a entradas muy cortas
    if len(palabras) > MAX_PALABRAS_CORTAS:
        return False

    # Palabras sueltas sin significado completo
    PALABRAS_VACIAS_SOLAS = {
        "este", "eso", "esa", "asi", "pues",
        "mmm", "hmm", "ah", "oh", "uh",
        "que", "como", "cuando", "donde"
    }

    # Si todas las palabras son vacías → entrada sin tema
    todas_vacias = all(p in PALABRAS_VACIAS_SOLAS for p in palabras)
    if todas_vacias:
        return True

    return False