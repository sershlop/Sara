# 📁 external_service.py
# Módulo de servicios externos de SARA
# Búsquedas web, scraping y herramientas de respaldo

from config import (
    MODO_MOCK,
    TIMEOUT_EXTERNO,
)
import requests
import json
import re
from urllib.parse import quote, urlparse
from utils import normalizar_texto
import logger
from database import agregar_respuesta_externa

# ──────────────────────────────────────────────
# 🔹 HEADERS
# ──────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ──────────────────────────────────────────────
# 🔹 VALIDACIÓN DE URLs
# ──────────────────────────────────────────────


def _es_url_valida(url):
    try:
        resultado = urlparse(url)
        return all([resultado.scheme in ("http", "https"), resultado.netloc])
    except Exception:
        return False


def _normalizar_url(url):
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


# ──────────────────────────────────────────────
# 🔹 BÚSQUEDA WEB
# ──────────────────────────────────────────────

def buscar_web(query):
    """
    Búsqueda web — modo mock por ahora.
    """
    try:
        if not query or not query.strip():
            return _resultado(False, [], "ninguna", "Búsqueda vacía.")

        query = query.strip()
        return _buscar_mock(query) if MODO_MOCK else _buscar_real(query)

    except Exception as e:
        logger.log_excepcion("external", query, e)
        return _resultado(False, [], "error", str(e))


def _buscar_mock(query):
    resultados = [
        f"[MOCK] Resultado 1 para: '{query}'",
        f"[MOCK] Resultado 2 para: '{query}'",
        f"[MOCK] Resultado 3 para: '{query}'"
    ]
    guardar_resultados_web(query, resultados, fuente="mock")
    logger.debug("external", f"Búsqueda mock: '{query[:50]}'")
    return _resultado(True, resultados, "mock")


def _buscar_real(query):
    logger.warning("external", "Modo real no implementado — usando mock.")
    return _buscar_mock(query)


# ──────────────────────────────────────────────
# 🔹 SCRAPING
# ──────────────────────────────────────────────

def scrapear_tabla(url, indice_tabla=0):
    try:
        url = _normalizar_url(url)
        if not _es_url_valida(url):
            return _resultado_tabla(False, None, f"URL inválida: {url}")

        try:
            import pandas as pd
        except ImportError:
            return _resultado_tabla(False, None, "pandas no instalado.")

        tablas = pd.read_html(url)
        if not tablas:
            return _resultado_tabla(False, None, "No se encontraron tablas.")

        if indice_tabla >= len(tablas):
            return _resultado_tabla(False, None, f"Índice {indice_tabla} inválido.")

        tabla    = tablas[indice_tabla]
        filas    = tabla.head(10).to_dict(orient="records")
        columnas = list(tabla.columns)
        resumen  = f"Tabla con {len(tabla)} filas y {len(columnas)} columnas"

        return _resultado_tabla(True, filas, resumen, columnas, url)

    except Exception as e:
        logger.log_excepcion("external", url, e)
        return _resultado_tabla(False, None, f"Error: {e}")


# ──────────────────────────────────────────────
# 🔹 GUARDAR EN BD
# ──────────────────────────────────────────────

def guardar_resultados_web(query, resultados, fuente="web"):
    try:
        if not resultados:
            return _resultado(False, [], fuente, "Sin resultados.")

        guardados = 0
        for r in resultados:
            try:
                agregar_respuesta_externa(query, str(r), fuente)
                guardados += 1
            except Exception as e:
                logger.error("external", f"Error guardando: {str(r)[:40]}", str(e))

        logger.info("external", f"Guardados: {guardados}/{len(resultados)}")
        return _resultado(True, resultados, fuente)

    except Exception as e:
        logger.log_excepcion("external", query, e)
        return _resultado(False, [], fuente, str(e))


def guardar_tabla_bd(url, indice_tabla=0):
    try:
        resultado = scrapear_tabla(url, indice_tabla)
        if not resultado["exito"]:
            return resultado

        filas = resultado["tabla"]
        guardar_resultados_web(url, [str(f) for f in filas], fuente="scraping")
        return _resultado(True, filas, "scraping")

    except Exception as e:
        logger.log_excepcion("external", url, e)
        return _resultado(False, [], "error", str(e))


# ──────────────────────────────────────────────
# 🔹 CONECTIVIDAD
# ──────────────────────────────────────────────

def verificar_conexion(url_prueba="https://www.google.com"):
    try:
        response       = requests.get(url_prueba, timeout=5, headers=HEADERS)
        tiene_conexion = response.status_code == 200
        logger.debug("external", f"Conexión: {'OK' if tiene_conexion else 'SIN INTERNET'}")
        return tiene_conexion

    except requests.ConnectionError:
        logger.warning("external", "Sin conexión a internet.")
        return False

    except Exception as e:
        logger.log_excepcion("external", url_prueba, e)
        return False

# ──────────────────────────────────────────────
# 🔹 RESPALDO INTELIGENTE — FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────────

def obtener_respuesta_externa(pregunta):
    """
    Sistema de respaldo por niveles para preguntas.
    Actualmente desactivado.

    Retorna: (None, None)
    """
    logger.warning("external", f"Respaldo externo desactivado para: '{pregunta[:40]}'")
    return None, None

# ──────────────────────────────────────────────
# 🔹 HELPERS
# ──────────────────────────────────────────────

def _resultado(exito, resultados, fuente, mensaje=""):
    return {
        "exito":      exito,
        "resultados": resultados,
        "fuente":     fuente,
        "modo":       "mock" if MODO_MOCK else "real",
        "mensaje":    mensaje
    }


def _resultado_tabla(exito, tabla, resumen, columnas=None, fuente=""):
    return {
        "exito":    exito,
        "tabla":    tabla,
        "resumen":  resumen,
        "columnas": columnas,
        "fuente":   fuente
    }