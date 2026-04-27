# 📁 brain.py
# Núcleo de procesamiento de SARA
# Responsable de: limpiar texto, detectar intención,
# buscar respuesta/comando y retornar resultado estructurado
from config import (
    UMBRAL_PREGUNTA,
    UMBRAL_COMANDO,
    UMBRAL_INTENCION,
    PESO_DIFFLIB,
    PESO_BD,
    PESO_SEMANTICO,
)
from utils import normalizar_texto, similitud, empieza_con_palabras, contiene_palabra_clave
from database import (
    obtener_conocimientos,
    obtener_comandos,
    guardar_intencion,
    guardar_historial,
    incrementar_consulta,
    incrementar_uso_comando,
    obtener_vectores_conocimientos,
    obtener_vectores_comandos
)
import searcher
import embeddings
import logger

# ──────────────────────────────────────────────
# 🔹 CONSTANTES DE PENALIZACIÓN Y SCORING
# ──────────────────────────────────────────────
PENALIZACION_INTENCION_DIFERENTE = 0.65
CONFIANZA_BUSQUEDA = 0.95
PESOS_FALLBACK_DIFFLIB = 0.50
PESOS_FALLBACK_BD = 0.50



# ──────────────────────────────────────────────
# 🔹 CONFIGURACIÓN DE UMBRALES
# ──────────────────────────────────────────────


# Palabras que indican pregunta (se normalizan automáticamente)
PALABRAS_PREGUNTA = (
    "que", "como", "cuando", "donde", "por que", "para que",
    "quien", "cuanto", "cuantos", "cuales", "cual", "dime",
    "explicame", "sabes", "conoces", "puedes decirme"
)

# Palabras que indican comando (se normalizan automáticamente)
PALABRAS_COMANDO = (
    "abre", "abrir", "ejecuta", "ejecutar",
    "pon", "poner", "inicia", "iniciar",
    "cierra", "cerrar", "busca", "buscar",
    "muestra", "mostrar", "reproduce", "reproducir",
    "descarga", "descargar", "instala", "instalar",
    "apaga", "apagar", "reinicia", "reiniciar",
    "crea", "crear", "elimina", "eliminar",
    "quiero que", "necesito que", "quiero", "necesito"
)

# Palabras funcionales para extracción de tema (evitar duplicación)
PALABRAS_FUNCIONALES = {
    # interrogativas
    "que", "como", "cuando", "donde", "quien", "cual", "cuanto",
    "cuantos", "cuales", "por", "para",
    # artículos
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    # preposiciones
    "de", "del", "en", "con", "a", "al", "por", "para",
    "sobre", "entre", "hacia", "desde", "hasta",
    # verbos auxiliares comunes
    "es", "son", "fue", "era", "ser", "estar", "esta", "estan",
    "tiene", "tienen", "hay",
    # conjunciones
    "y", "o", "pero", "sino", "aunque",
    # otros
    "me", "te", "se", "le", "lo", "su", "sus"
}

# Temas comunes a ignorar en extracción de núcleo
TEMAS_COMUNES = {
    # Cuerpos celestes
    "luna", "sol", "tierra", "marte", "venus",
    "planeta", "estrella", "galaxia", "universo",
    # Plataformas (moveidas a config idealmente)
    "youtube", "google", "chrome"
}

# Equivalencias de intención (VERSIÓN CONSOLIDADA con más equivalentes)
EQUIVALENCIAS_INTENCION = {
    "que es": {
        "dime", "explicame", "cuentame", "describe",
        "definicion", "como es", "como seria",
        "como luce", "como se ve", "dime sobre",
        "platícame", "platicame", "habla"
    },
    "como funciona": {
        "como trabaja", "como opera", "mecanismo",
        "como se usa", "para que sirve"
    },
    "cual es": {
        "dime el", "dime la", "cual seria",
        "cuanto mide", "cuanto pesa"
    },
    "donde esta": {
        "ubicacion", "donde se encuentra",
        "donde queda"
    },
}




# ──────────────────────────────────────────────
# 🔹 DETECCIÓN DE INTENCIÓN
# ──────────────────────────────────────────────

def detectar_intencion(texto_original, texto_limpio):
    """
    Detecta si el texto es una pregunta, comando o desconocido.
    Retorna: (tipo, confianza)
    """
    # Capa 1: Signos de pregunta en texto original (¿ o ?)
    if "?" in texto_original or "¿" in texto_original:
        return "pregunta", 0.95

    # Capa 2: Empieza con palabra de pregunta
    if empieza_con_palabras(texto_limpio, PALABRAS_PREGUNTA):
        return "pregunta", 0.85

    # Capa 3: Empieza con palabra de comando
    if empieza_con_palabras(texto_limpio, PALABRAS_COMANDO):
        return "comando", 0.85

    # Capa 4: Contiene palabra de pregunta en cualquier posición
    for palabra in PALABRAS_PREGUNTA:
        if contiene_palabra_clave(texto_limpio, palabra):
            return "pregunta", 0.60

    # Capa 5: Contiene palabra de comando en cualquier posición
    for palabra in PALABRAS_COMANDO:
        if contiene_palabra_clave(texto_limpio, palabra):
            return "comando", 0.60

    return "desconocido", 0.0


# ──────────────────────────────────────────────
# 🔹 BÚSQUEDA DE RESPUESTA
# ──────────────────────────────────────────────
def buscar_respuesta(texto_limpio):
    """
    Busca respuesta usando score ponderado con penalización
    por diferencia de intención.
    """
    datos = obtener_conocimientos()

    if not datos:
        return None, 0.0, None

    mejor_score     = 0.0
    mejor_respuesta = None
    mejor_pregunta  = None

    vectores_list   = obtener_vectores_conocimientos() if embeddings.esta_disponible() else []
    vector_consulta = embeddings.generar_vector(texto_limpio) if embeddings.esta_disponible() else None

    # Optimización: Convertir lista de vectores a diccionario para búsqueda O(1)
    vectores_dict = {}
    if vectores_list:
        for preg, resp, vec in vectores_list:
            vectores_dict[normalizar_texto(preg)] = vec

    # Extraer núcleo interrogativo de la consulta
    nucleo_consulta = _extraer_nucleo_interrogativo(texto_limpio)

    for fila in datos:
        pregunta_bd = normalizar_texto(fila["pregunta"])

        # Capa 3 — difflib
        score_difflib = similitud(texto_limpio, pregunta_bd)

        # Capa 4 — palabras clave
        score_bd = score_difflib

        # Capa 5 — semántico
        score_semantico = 0.0
        if vector_consulta and vectores_dict:
            vec = vectores_dict.get(pregunta_bd)
            if vec:
                score_semantico = embeddings.similitud_coseno(
                    vector_consulta, vec
                )

        # ── Penalización por intención diferente ──
        nucleo_bd = _extraer_nucleo_interrogativo(pregunta_bd)
        penalizacion = 1.0

        if nucleo_consulta and nucleo_bd:
            similitud_nucleos = similitud(nucleo_consulta, nucleo_bd)
            if not _misma_intencion(nucleo_consulta, nucleo_bd):
                penalizacion = PENALIZACION_INTENCION_DIFERENTE
                logger.debug(
                    "brain",
                    f"Penalización aplicada: '{nucleo_consulta}' vs '{nucleo_bd}'",
                    f"similitud nucleos: {similitud_nucleos:.2f}"
                )

        score_semantico_ajustado = score_semantico * penalizacion

        # Score final ponderado
        if embeddings.esta_disponible() and score_semantico > 0:
            score_final = (
                score_difflib            * PESO_DIFFLIB +
                score_bd                 * PESO_BD +
                score_semantico_ajustado * PESO_SEMANTICO
            )
        else:
            score_final = (
                score_difflib * PESOS_FALLBACK_DIFFLIB +
                score_bd * PESOS_FALLBACK_BD
            )

        if score_final > mejor_score:
            mejor_score     = score_final
            mejor_respuesta = fila["respuesta"]
            mejor_pregunta  = fila["pregunta"]

    if mejor_score >= UMBRAL_PREGUNTA:
        incrementar_consulta(mejor_pregunta)
        return mejor_respuesta, mejor_score, mejor_pregunta

    return None, mejor_score, None


def _extraer_nucleo_interrogativo(texto):
    """
    Extrae el núcleo de la intención de una pregunta.
    Elimina palabras funcionales y temas comunes.
    """
    PREPOSICIONES = {"de", "del", "en", "con", "por", "para", "sobre"}
    ARTICULOS = {"el", "la", "los", "las", "un", "una"}

    palabras = texto.split()
    resultado = []

    for palabra in palabras:
        if palabra in TEMAS_COMUNES:
            continue
        if palabra in PREPOSICIONES:
            continue
        if palabra in ARTICULOS:
            continue
        resultado.append(palabra)

    return " ".join(resultado) if resultado else texto


# ──────────────────────────────────────────────
# 🔹 BÚSQUEDA DE COMANDO
# ──────────────────────────────────────────────

def buscar_comando(texto_limpio):
    """
    Busca el mejor comando usando score ponderado por capas.
    Retorna: (comando_dict, score_final)
    """
    comandos = obtener_comandos()

    if not comandos:
        return None, 0.0

    mejor_score   = 0.0
    mejor_comando = None

    vectores_list   = obtener_vectores_comandos() if embeddings.esta_disponible() else []
    vector_consulta = embeddings.generar_vector(texto_limpio) if embeddings.esta_disponible() else None

    # Optimización: Convertir lista de vectores a diccionario para búsqueda O(1)
    vectores_dict = {}
    if vectores_list:
        for cmd_dict, vec in vectores_list:
            vectores_dict[normalizar_texto(cmd_dict["nombre"])] = vec

    for cmd in comandos:
        nombre         = normalizar_texto(cmd["nombre"])
        palabras_clave = cmd["palabras_clave"] or ""

        score_difflib = similitud(texto_limpio, nombre)

        score_bd = score_difflib
        for palabra in palabras_clave.split(","):
            palabra = normalizar_texto(palabra.strip())
            if palabra:
                s = similitud(texto_limpio, palabra)
                if s > score_bd:
                    score_bd = s
                if contiene_palabra_clave(texto_limpio, palabra):
                    score_bd = max(score_bd, 0.80)

        score_semantico = 0.0
        if vector_consulta and vectores_dict:
            vec = vectores_dict.get(nombre)
            if vec:
                score_semantico = embeddings.similitud_coseno(
                    vector_consulta, vec
                )

        if embeddings.esta_disponible() and score_semantico > 0:
            score_final = (
                score_difflib   * PESO_DIFFLIB +
                score_bd        * PESO_BD +
                score_semantico * PESO_SEMANTICO
            )
        else:
            score_final = (
                score_difflib * PESOS_FALLBACK_DIFFLIB +
                score_bd * PESOS_FALLBACK_BD
            )

        if score_final > mejor_score:
            mejor_score   = score_final
            mejor_comando = cmd

    if mejor_score >= UMBRAL_COMANDO:
        incrementar_uso_comando(mejor_comando["id"])
        return dict(mejor_comando), mejor_score

    return None, mejor_score


# ──────────────────────────────────────────────
# 🔹 PROCESAMIENTO PRINCIPAL
# ──────────────────────────────────────────────

def procesar(texto_original):
    """
    Función principal de brain.py — llamada desde sara.py.
    """

    # 1. Normalizar
    texto_limpio = normalizar_texto(texto_original)

    if not texto_limpio:
        return _resultado(
            "desconocido",
            "No entendí nada, ¿puedes repetirlo?",
            confianza=0.0
        )

    # ── 2. CAPA 0: COMANDOS DIRECTOS ─────────────
    comando_bd, score_cmd = buscar_comando(texto_limpio)

    if comando_bd and score_cmd >= UMBRAL_COMANDO:
        guardar_intencion(
            texto_original,
            texto_limpio,
            "comando",
            score_cmd
        )

        guardar_historial(
            texto_original,
            texto_limpio,
            comando_bd.get("nombre", ""),
            "comando",
            score_cmd
        )

        return _resultado(
            "comando",
            f"Ejecutando: {comando_bd['nombre']}",
            comando=comando_bd,
            confianza=score_cmd,
            query=texto_limpio
        )

    # ── 3. CAPA: BÚSQUEDA ───────────────────────
    busqueda = searcher.analizar(texto_original)

    if busqueda.get("es_busqueda"):
        guardar_intencion(
            texto_original,
            texto_limpio,
            "busqueda",
            CONFIANZA_BUSQUEDA
        )

        guardar_historial(
            texto_original,
            texto_limpio,
            busqueda.get("mensaje", ""),
            "busqueda",
            CONFIANZA_BUSQUEDA
        )

        return _resultado(
            "busqueda",
            busqueda.get("mensaje", ""),
            confianza=CONFIANZA_BUSQUEDA,
            query=texto_limpio,
            busqueda=busqueda
        )

    # ── 4. DETECTAR INTENCIÓN ──────────────────
    tipo_intencion, confianza_intencion = detectar_intencion(
        texto_original, texto_limpio
    )

    guardar_intencion(
        texto_original,
        texto_limpio,
        tipo_intencion,
        confianza_intencion
    )

    # ── 5. RESPUESTAS ──────────────────────────
    if tipo_intencion == "pregunta":
        respuesta, confianza, _ = buscar_respuesta(texto_limpio)

        if respuesta:
            guardar_historial(
                texto_original,
                texto_limpio,
                respuesta,
                "pregunta",
                confianza
            )

            return _resultado(
                "respuesta",
                respuesta,
                confianza=confianza,
                query=texto_limpio
            )

        # Sin respuesta
        guardar_historial(
            texto_original,
            texto_limpio,
            "sin_respuesta",
            "pregunta",
            0.0
        )

        return _resultado(
            "respuesta",
            "Aún no sé la respuesta a eso. ¿Quieres enseñarme o que le pregunte a Grok?",
            confianza=0.0,
            query=texto_limpio
        )

    # ── 6. COMANDO NO RECONOCIDO ───────────────
    elif tipo_intencion == "comando":
        comando_bd, score_cmd = buscar_comando(texto_limpio)

        if not comando_bd or score_cmd < UMBRAL_COMANDO:
            guardar_historial(
                texto_original,
                texto_limpio,
                "sin_comando",
                "comando",
                0.0
            )

            return _resultado(
                "comando",
                "No reconozco ese comando. ¿Quieres que le pida a Grok que lo cree?",
                confianza=0.0,
                query=texto_limpio
            )

    # ── 7. DESCONOCIDO ─────────────────────────
    guardar_historial(
        texto_original,
        texto_limpio,
        "desconocido",
        "desconocido",
        0.0
    )

    return _resultado(
        "desconocido",
        "No entendí lo que dijiste.",
        confianza=0.0,
        query=texto_limpio
    )




def _misma_intencion(nucleo_a, nucleo_b):
    """
    Verifica si dos núcleos tienen la misma intención.
    """
    if not nucleo_a or not nucleo_b:
        return True

    if similitud(nucleo_a, nucleo_b) >= 0.40:
        return True

    for base, equivalentes in EQUIVALENCIAS_INTENCION.items():
        base_norm = normalizar_texto(base)
        todos = {base_norm} | {normalizar_texto(e) for e in equivalentes}

        coincide_a = any(nucleo_a.startswith(t) for t in todos)
        coincide_b = any(nucleo_b.startswith(t) for t in todos)

        if coincide_a and coincide_b:
            return True

    return False


def _resultado(tipo, texto, comando=None, confianza=0.0, query="", busqueda=None):
    """
    Construye el diccionario de resultado estándar.
    """
    return {
        "tipo": tipo,
        "texto": texto,
        "comando": comando,
        "confianza": round(confianza, 4),
        "query": query,
        "busqueda": busqueda
    }