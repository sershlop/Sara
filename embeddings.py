# 📁 embeddings.py
# Motor de embeddings semánticos de SARA
# Convierte texto en vectores numéricos y calcula similitud coseno
# Si falla la carga del modelo, SARA sigue funcionando sin embeddings
from config import MODELO_EMBEDDINGS, UMBRAL_SEMANTICO
import numpy as np
import logger

# ──────────────────────────────────────────────
# 🔹 CONFIGURACIÓN
# ──────────────────────────────────────────────




# Instancia global del modelo — se carga una sola vez al arrancar
_modelo = None
_disponible = False


# ──────────────────────────────────────────────
# 🔹 CARGA DEL MODELO
# ──────────────────────────────────────────────

def cargar_modelo():
    """
    Carga el modelo de embeddings en memoria.
    Se llama una sola vez desde sara.py al inicializar.
    Si falla, SARA sigue funcionando sin embeddings.

    Retorna: True si cargó correctamente, False si falló
    """
    global _modelo, _disponible

    try:
        from sentence_transformers import SentenceTransformer
        logger.info("embeddings", "Cargando modelo semántico...")
        _modelo = SentenceTransformer(MODELO_EMBEDDINGS)
        _disponible = True
        logger.info("embeddings", f"Modelo '{MODELO_EMBEDDINGS}' cargado correctamente.")
        return True

    except ImportError:
        logger.warning(
            "embeddings",
            "sentence-transformers no instalado.",
            "pip install sentence-transformers"
        )
        _disponible = False
        return False

    except Exception as e:
        logger.log_excepcion("embeddings", "cargar_modelo", e)
        _disponible = False
        return False
import os
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"   
os.environ["TOKENIZERS_PARALLELISM"] = "false" 

import logging
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

def esta_disponible():
    """
    Retorna True si el modelo está listo para usar.
    Usado por brain.py para decidir si aplicar capa 5.
    """
    return _disponible


# ──────────────────────────────────────────────
# 🔹 GENERACIÓN DE VECTORES
# ──────────────────────────────────────────────

def generar_vector(texto):
    """
    Convierte un texto en su vector de embeddings.

    Retorna: list[float] con el vector, o None si no disponible

    Ejemplo:
        generar_vector("que es la luna")
        → [0.23, 0.87, 0.12, -0.45, ...]  (384 dimensiones)
    """
    if not _disponible or not _modelo:
        return None

    if not texto or not isinstance(texto, str):
        return None

    try:
        vector = _modelo.encode(texto, convert_to_numpy=True)
        return vector.tolist()  # Convertir a lista para guardar en BD

    except Exception as e:
        logger.log_excepcion("embeddings", "generar_vector", e)
        return None


def vector_desde_texto(texto):
    """
    Alias semántico de generar_vector.
    Para uso externo desde learning.py
    """
    return generar_vector(texto)


# ──────────────────────────────────────────────
# 🔹 SIMILITUD COSENO
# ──────────────────────────────────────────────

def similitud_coseno(vector_a, vector_b):
    """
    Calcula similitud coseno entre dos vectores.
    Valor entre 0.0 (nada similar) y 1.0 (idéntico semánticamente)

    Retorna: float, o 0.0 si algo falla

    Fórmula:
        cos(θ) = (A · B) / (||A|| × ||B||)
    """
    try:
        a = np.array(vector_a, dtype=np.float32)
        b = np.array(vector_b, dtype=np.float32)

        norma_a = np.linalg.norm(a)
        norma_b = np.linalg.norm(b)

        # Evitar división por cero
        if norma_a == 0 or norma_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norma_a * norma_b))

    except Exception as e:
        logger.log_excepcion("embeddings", "similitud_coseno", e)
        return 0.0


def similitud_semantica(texto_a, texto_b):
    """
    Calcula similitud semántica directamente entre dos textos.
    Genera los vectores internamente.

    Retorna: float entre 0.0 y 1.0, o 0.0 si no disponible

    Ejemplo:
        similitud_semantica("que es la luna", "dime sobre la luna")
        → 0.92
    """
    if not _disponible:
        return 0.0

    try:
        vector_a = generar_vector(texto_a)
        vector_b = generar_vector(texto_b)

        if vector_a is None or vector_b is None:
            return 0.0

        return similitud_coseno(vector_a, vector_b)

    except Exception as e:
        logger.log_excepcion("embeddings", "similitud_semantica", e)
        return 0.0


# ──────────────────────────────────────────────
# 🔹 BÚSQUEDA SEMÁNTICA EN LISTA
# ──────────────────────────────────────────────

def buscar_mas_similar(texto_consulta, lista_vectores):
    """
    Dado un texto y una lista de (id, vector),
    retorna el id del vector más similar semánticamente.

    Usado por brain.py para encontrar la mejor coincidencia
    entre el input del usuario y los vectores guardados en BD.

    lista_vectores: list[ (id, vector) ]
    Retorna: (id_mejor, score) o (None, 0.0)
    """
    if not _disponible or not lista_vectores:
        return None, 0.0

    try:
        vector_consulta = generar_vector(texto_consulta)
        if vector_consulta is None:
            return None, 0.0

        mejor_id    = None
        mejor_score = 0.0

        for item_id, vector in lista_vectores:
            if vector is None:
                continue
            score = similitud_coseno(vector_consulta, vector)
            if score > mejor_score:
                mejor_score = score
                mejor_id    = item_id

        return mejor_id, mejor_score

    except Exception as e:
        logger.log_excepcion("embeddings", "buscar_mas_similar", e)
        return None, 0.0