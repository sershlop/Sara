# 📁 splitter.py
# Detector y divisor de preguntas múltiples para SARA
# Cuando el usuario hace varias preguntas en una sola entrada,
# este módulo las separa para que brain.py las procese individualmente
#
# Ejemplo:
#   "que es la luna y como se formo"
#   → ["que es la luna", "como se formo la luna"]

from utils import normalizar_texto
import logger

# ──────────────────────────────────────────────
# 🔹 CONFIGURACIÓN
# ──────────────────────────────────────────────

# Prefijos sociales que el usuario usa para dirigirse a SARA
# pero no forman parte de la pregunta real
PREFIJOS_SOCIALES = (
    "oye sara", "sara dime", "oye dime", "sara", "oye", "dime", "sara por favor",
    "oye", "a ver", "mira", "escucha", "hey sara",
    "hey", "dime", "cuentame", "explicame", "platicame"
)

# Separadores que indican que hay más de una pregunta
SEPARADORES = (
    " y ademas ", " y tambien ", " y despues ",
    " ademas ", " tambien ", " igualmente ",
    " y ", " pero tambien ", " aunque tambien "
)

# Palabras que indican inicio de pregunta nueva
# Si aparecen después de un separador → es pregunta múltiple
INICIO_PREGUNTA = {
    "que", "como", "cuando", "donde", "quien",
    "cual", "cuanto", "cuantos", "cuanta", "cuantas",
    "dime", "explicame", "cuentame", "por que", "para que"
}

# Palabras que indican inicio de comando nuevo
INICIO_COMANDO = {
    "abre", "abrir", "ejecuta", "pon", "inicia",
    "cierra", "busca", "muestra", "reproduce"
}


# ──────────────────────────────────────────────
# 🔹 FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────────

def dividir_entrada(texto):
    """
    Analiza una entrada del usuario y la divide en
    preguntas/comandos individuales si contiene múltiples.

    Retorna: list[str] con las preguntas separadas
             Si solo hay una → retorna lista con esa sola pregunta

    Ejemplos:
        "que es la luna y como se formo"
        → ["que es la luna", "como se formo la luna"]

        "abre youtube y abre google"
        → ["abre youtube", "abre google"]

        "que es la luna"
        → ["que es la luna"]  ← lista de un solo elemento
    """
    texto_norm = normalizar_texto(texto)

    # PASO 1: Limpiar prefijos sociales
    texto_limpio = _quitar_prefijos(texto_norm)

    # PASO 2: Detectar si hay múltiples preguntas
    if not _tiene_multiples(texto_limpio):
        # Una sola pregunta — retornar tal cual
        return [texto_limpio]

    # PASO 3: Dividir en segmentos
    segmentos = _dividir_segmentos(texto_limpio)

    # PASO 4: Completar segmentos incompletos con contexto
    segmentos_completos = _completar_segmentos(segmentos)

    # PASO 5: Filtrar segmentos vacíos o muy cortos
    resultado = [
        s.strip() for s in segmentos_completos
        if s.strip() and len(s.strip()) > 2
    ]

    if not resultado:
        return [texto_limpio]

    logger.debug(
        "splitter",
        f"Entrada dividida en {len(resultado)} parte(s)",
        f"original: '{texto[:50]}'"
    )

    return resultado


# ──────────────────────────────────────────────
# 🔹 PASO 1 — LIMPIAR PREFIJOS SOCIALES
# ──────────────────────────────────────────────

def _quitar_prefijos(texto):
    """
    Elimina prefijos sociales al inicio del texto.

    "oye sara que es la luna" → "que es la luna"
    "sara dime como se formo" → "como se formo"
    "dime que es el sol"      → "que es el sol"
    """
    for prefijo in PREFIJOS_SOCIALES:
        prefijo_norm = normalizar_texto(prefijo)
        if texto.startswith(prefijo_norm):
            texto = texto[len(prefijo_norm):].strip()
            # Solo quitar el primer prefijo encontrado
            break

    return texto.strip()


# ──────────────────────────────────────────────
# 🔹 PASO 2 — DETECTAR PREGUNTAS MÚLTIPLES
# ──────────────────────────────────────────────

def _tiene_multiples(texto):
    """
    Detecta si el texto contiene más de una pregunta o comando.

    Retorna True solo si:
    - Contiene un separador Y
    - Después del separador hay inicio de pregunta o comando

    Esto evita falsos positivos como:
    "que es blanca y redonda" → False (describe una sola cosa)
    "que es la luna y como se formo" → True (dos preguntas)
    """
    for separador in SEPARADORES:
        if separador in texto:
            # Encontrar la parte después del separador
            partes  = texto.split(separador, 1)
            if len(partes) < 2:
                continue

            despues = partes[1].strip()
            if not despues:
                continue

            # Verificar si después del separador hay pregunta o comando
            primera_palabra = despues.split()[0] if despues.split() else ""

            if primera_palabra in INICIO_PREGUNTA:
                return True
            if primera_palabra in INICIO_COMANDO:
                return True

    return False


# ──────────────────────────────────────────────
# 🔹 PASO 3 — DIVIDIR EN SEGMENTOS
# ──────────────────────────────────────────────

def _dividir_segmentos(texto):
    """
    Divide el texto en segmentos usando los separadores.
    Solo divide donde hay inicio de pregunta o comando real.

    "que es la luna y como se formo y donde esta"
    → ["que es la luna", "como se formo", "donde esta"]
    """
    segmentos = [texto]

    for separador in SEPARADORES:
        nuevos_segmentos = []

        for segmento in segmentos:
            if separador not in segmento:
                nuevos_segmentos.append(segmento)
                continue

            partes = segmento.split(separador)
            for i, parte in enumerate(partes):
                parte = parte.strip()
                if not parte:
                    continue

                # Verificar si esta parte es inicio válido
                if i > 0:
                    primera = parte.split()[0] if parte.split() else ""
                    # Solo agregar como segmento separado si es pregunta/comando
                    if primera in INICIO_PREGUNTA or primera in INICIO_COMANDO:
                        nuevos_segmentos.append(parte)
                    else:
                        # No es inicio válido → unir al segmento anterior
                        if nuevos_segmentos:
                            nuevos_segmentos[-1] += f" {parte}"
                        else:
                            nuevos_segmentos.append(parte)
                else:
                    nuevos_segmentos.append(parte)

        segmentos = nuevos_segmentos

    return segmentos


# ──────────────────────────────────────────────
# 🔹 PASO 4 — COMPLETAR SEGMENTOS CON CONTEXTO
# ──────────────────────────────────────────────
def _completar_segmentos(segmentos):
    """
    Completa segmentos incompletos heredando el tema del primero.
    Un segmento es completo si ya tiene su propio tema identificable.
    """
    if not segmentos:
        return segmentos

    tema = _extraer_tema_segmento(segmentos[0])

    if not tema:
        return segmentos

    resultado = [segmentos[0]]

    for segmento in segmentos[1:]:
        # ── FIX: Verificar si el segmento ya es completo ──
        tema_propio = _extraer_tema_segmento(segmento)

        if tema_propio:
            # Ya tiene su propio tema → no completar
            resultado.append(segmento)
        else:
            # No tiene tema propio → heredar del primero
            segmento_completo = _completar_con_tema(segmento, tema)
            resultado.append(segmento_completo)

    return resultado


def _extraer_tema_segmento(segmento):
    """
    Extrae el tema principal de un segmento.
    Similar a context._extraer_tema() pero independiente.

    "que es la luna" → "luna"
    "abre youtube"   → "youtube"
    """
    PALABRAS_VACIAS = {
        "que", "como", "cuando", "donde", "quien", "cual",
        "cuanto", "es", "son", "fue", "se", "de", "del",
        "la", "el", "los", "las", "un", "una", "tiene",
        "esta", "hace", "abre", "abrir", "dime", "explicame"
    }

    palabras   = segmento.split()
    candidatos = [
        p for p in palabras
        if p not in PALABRAS_VACIAS and len(p) > 2
    ]

    return candidatos[-1] if candidatos else None


def _completar_con_tema(segmento, tema):
    """
    Agrega el tema al segmento si no lo contiene.

    "como se formo" + tema="luna" → "como se formo la luna"
    "cual es su tamaño" + tema="luna" → "cual es su tamaño de la luna"
    """
    if not tema:
        return segmento

    # Si el tema ya está en el segmento → no agregar
    if tema in segmento:
        return segmento

    # Agregar tema al final de forma natural
    if segmento.endswith(("de", "sobre", "en", "con")):
        return f"{segmento} {tema}"
    else:
        return f"{segmento} de la {tema}"


# ──────────────────────────────────────────────
# 🔹 UTILIDADES
# ──────────────────────────────────────────────

def es_entrada_simple(texto):
    """
    Retorna True si la entrada es una sola pregunta/comando.
    Útil para que sara.py decida si usar el flujo normal o el múltiple.
    """
    texto_norm  = normalizar_texto(texto)
    texto_limpio = _quitar_prefijos(texto_norm)
    return not _tiene_multiples(texto_limpio)