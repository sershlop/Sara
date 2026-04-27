# 📁 logger.py
# Módulo de registro de eventos de SARA
# Centraliza todos los logs del sistema
# Diseñado para escalar hacia archivo de texto, base de datos y niveles de severidad
from config import NIVEL_CONSOLA, NIVEL_BD

import traceback
from database import (
    guardar_log,
    guardar_log_comando,
    guardar_log_pregunta,
    guardar_log_error
)

# ──────────────────────────────────────────────
# 🔹 NIVELES DE LOG
# ──────────────────────────────────────────────
# Inspirado en el estándar Python logging:
# DEBUG    → desarrollo y diagnóstico
# INFO     → eventos normales del sistema
# WARNING  → situaciones inesperadas pero no críticas
# ERROR    → fallos que SARA pudo manejar
# CRITICAL → fallos que detienen el sistema

NIVELES = {
    "DEBUG":    0,
    "INFO":     1,
    "WARNING":  2,
    "ERROR":    3,
    "CRITICAL": 4
}

# Nivel mínimo para mostrar en consola
# En producción cambiar a "WARNING" desde config.py



# ──────────────────────────────────────────────
# 🔹 FUNCIÓN BASE
# ──────────────────────────────────────────────

def _log(nivel, tipo, mensaje, detalle=""):
    """
    Función base interna.
    Todas las funciones públicas pasan por aquí.

    nivel:   DEBUG | INFO | WARNING | ERROR | CRITICAL
    tipo:    categoria del log (sistema, comando, pregunta, error, etc.)
    mensaje: descripción principal
    detalle: información adicional opcional
    """

    nivel_num          = NIVELES.get(nivel, 1)
    nivel_consola_num  = NIVELES.get(NIVEL_CONSOLA, 0)
    nivel_bd_num       = NIVELES.get(NIVEL_BD, 1)

    # Mostrar en consola si supera el umbral
    if nivel_num >= nivel_consola_num:
        _imprimir_consola(nivel, tipo, mensaje, detalle)

    # Guardar en BD si supera el umbral
    if nivel_num >= nivel_bd_num:
        try:
            guardar_log(f"{nivel}:{tipo}", mensaje, detalle)
        except Exception as e:
            # Si falla el log en BD, al menos lo mostramos en consola
            print(f"[LOGGER BD ERROR] No se pudo guardar log: {e}")


def _imprimir_consola(nivel, tipo, mensaje, detalle):
    """
    Formatea e imprime el log en consola.
    Formato: [NIVEL][tipo] mensaje → detalle
    """
    iconos = {
        "DEBUG":    "🔍",
        "INFO":     "ℹ️ ",
        "WARNING":  "⚠️ ",
        "ERROR":    "❌",
        "CRITICAL": "🔥"
    }
    icono = iconos.get(nivel, "▪️")
    linea = f"{icono} [{nivel}][{tipo}] {mensaje}"
    if detalle:
        linea += f"\n    → {detalle}"
    print(linea)


# ──────────────────────────────────────────────
# 🔹 API PÚBLICA — NIVELES
# ──────────────────────────────────────────────

def debug(tipo, mensaje, detalle=""):
    """Log de desarrollo — solo visible durante depuración."""
    _log("DEBUG", tipo, mensaje, detalle)


def info(tipo, mensaje, detalle=""):
    """Log de evento normal del sistema."""
    _log("INFO", tipo, mensaje, detalle)


def warning(tipo, mensaje, detalle=""):
    """Log de situación inesperada pero manejable."""
    _log("WARNING", tipo, mensaje, detalle)


def error(tipo, mensaje, detalle=""):
    """Log de fallo manejado."""
    _log("ERROR", tipo, mensaje, detalle)


def critical(tipo, mensaje, detalle=""):
    """Log de fallo crítico que puede detener SARA."""
    _log("CRITICAL", tipo, mensaje, detalle)


# ──────────────────────────────────────────────
# 🔹 API PÚBLICA — EVENTOS ESPECÍFICOS
# ──────────────────────────────────────────────

def log_inicio():
    """Registra el arranque de SARA."""
    info("sistema", "SARA iniciada correctamente")


def log_cierre():
    """Registra el cierre limpio de SARA."""
    info("sistema", "SARA cerrada por el usuario")


def log_comando(comando, exito=True):
    """
    Registra la ejecución de un comando.
    comando: dict del comando ejecutado (viene de brain.py)
    exito:   True si se ejecutó sin errores
    """
    try:
        registro = {
            "id_comando": comando.get("id"),
            "nombre":     comando.get("nombre", "desconocido"),
            "exito":      exito
        }
        guardar_log_comando(registro)

        if exito:
            info("comando", f"Ejecutado: {registro['nombre']}", f"id={registro['id_comando']}")
        else:
            warning("comando", f"Falló: {registro['nombre']}", f"id={registro['id_comando']}")

    except Exception as e:
        error("logger", "Error en log_comando", str(e))


def log_pregunta(pregunta, respuesta=None, correcta=True):
    """
    Registra el procesamiento de una pregunta.
    pregunta:  texto original del usuario
    respuesta: lo que SARA respondió
    correcta:  si la respuesta fue satisfactoria
    """
    try:
        registro = {
            "pregunta":          pregunta,
            "respuesta_usuario": respuesta,
            "correcta":          correcta
        }
        guardar_log_pregunta(registro)

        if correcta:
            debug("pregunta", f"Respondida: {pregunta[:50]}")
        else:
            warning("pregunta", f"Sin respuesta: {pregunta[:50]}")

    except Exception as e:
        error("logger", "Error en log_pregunta", str(e))


def log_error(tipo, item, descripcion=""):
    """
    Registra un error general del sistema.
    tipo:        categoría (comando, pregunta, sistema, etc.)
    item:        elemento que causó el error
    descripcion: detalle del error
    """
    try:
        registro = {
            "tipo":        tipo,
            "item":        item,
            "descripcion": descripcion
        }
        guardar_log_error(registro)
        error(tipo, f"Error en: {str(item)[:50]}", descripcion[:100] if descripcion else "")

    except Exception as e:
        print(f"[LOGGER CRÍTICO] No se pudo registrar error: {e}")


def log_excepcion(tipo, item, excepcion):
    """
    Registra una excepción Python completa con traceback.
    Ideal para bloques except en sara.py

    Ejemplo de uso:
        except Exception as e:
            logger.log_excepcion("sistema", entrada, e)
    """
    try:
        tb = traceback.format_exc()
        descripcion = f"{type(excepcion).__name__}: {excepcion}\n{tb}"
        registro = {
            "tipo":        tipo,
            "item":        item,
            "descripcion": descripcion
        }
        guardar_log_error(registro)
        error(tipo, f"Excepción en: {str(item)[:50]}", f"{type(excepcion).__name__}: {excepcion}")

    except Exception as e:
        print(f"[LOGGER CRÍTICO] No se pudo registrar excepción: {e}")


def log_intencion_desconocida(texto):
    """
    Registra cuando SARA no pudo clasificar la intención.
    Útil para identificar patrones que SARA aún no entiende.
    """
    warning("intencion", f"No clasificada: {texto[:60]}")