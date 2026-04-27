# 📁 utils.py
# Funciones auxiliares generales para SARA
# Todos los módulos deben importar desde aquí para normalizar texto

import unicodedata
import re
from difflib import SequenceMatcher

# ──────────────────────────────────────────────
# 🔹 NORMALIZACIÓN DE TEXTO
# ──────────────────────────────────────────────

def normalizar_texto(texto):
    """
    Pipeline completo de limpieza:
    1. Minúsculas
    2. Quita acentos (á→a, é→e, etc.)
    3. Quita signos de puntuación y símbolos (¿?¡!.,;:)
    4. Colapsa espacios múltiples
    5. Strip final

    Texto original: "¿Qué ES eso??!"
    Texto limpio:   "que es eso"
    """
    if not texto or not isinstance(texto, str):
        return ""

    # 1. Minúsculas
    texto = texto.lower()

    # 2. Quitar acentos (NFD separa letra+tilde, encode ASCII ignora tildes)
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ASCII', 'ignore').decode('utf-8')

    # 3. Quitar símbolos y puntuación — conservar letras, números y espacios
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)

    # 4. Colapsar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto)

    # 5. Strip
    texto = texto.strip()

    return texto


# ──────────────────────────────────────────────
# 🔹 SIMILITUD ENTRE TEXTOS
# ──────────────────────────────────────────────

def similitud(texto1, texto2):
    """
    Retorna un valor entre 0.0 y 1.0 indicando qué tan parecidos son dos textos.
    Ambos textos se normalizan antes de comparar.

    Ejemplo:
        similitud("¿Qué es Python?", "que es python") → 1.0
        similitud("hola", "adios")                    → 0.0
    """
    a = normalizar_texto(texto1)
    b = normalizar_texto(texto2)

    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio()


def textos_iguales(texto1, texto2):
    """
    Retorna True si los textos son idénticos después de normalizar.
    Útil para búsquedas exactas.
    """
    return normalizar_texto(texto1) == normalizar_texto(texto2)


# ──────────────────────────────────────────────
# 🔹 DETECCIÓN DE PALABRAS CLAVE
# ──────────────────────────────────────────────

def contiene_palabra_clave(texto, palabra_clave):
    """
    Retorna True si la palabra clave aparece en el texto normalizado.
    Ambos se normalizan antes de comparar.

    Ejemplo:
        contiene_palabra_clave("Abre Chrome!!!", "abre") → True
    """
    return normalizar_texto(palabra_clave) in normalizar_texto(texto)


def empieza_con_palabras(texto, palabras):
    """
    Retorna True si el texto normalizado empieza con alguna de las palabras dadas.
    Reemplaza el uso directo de startswith() en brain.py

    Ejemplo:
        empieza_con_palabras("que es python", ("que", "como")) → True
    """
    texto_norm = normalizar_texto(texto)
    for palabra in palabras:
        if texto_norm.startswith(normalizar_texto(palabra)):
            return True
    return False


# ──────────────────────────────────────────────
# 🔹 DEBUG
# ──────────────────────────────────────────────

def print_debug(info, activo=True):
    """
    Imprime información de debug.
    Se puede desactivar globalmente pasando activo=False
    o desde config.py en fases futuras.
    """
    if activo:
        print(f"[DEBUG] {info}")