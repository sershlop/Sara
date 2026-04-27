# 📁 commands.py
import webbrowser
import os
import sys
import subprocess
import logger

SISTEMA = sys.platform
TIPOS_COMANDOS_VALIDOS = {"web", "app", "sistema"}
TIMEOUT_COMANDO = 10

def ejecutar_comando(comando):
    try:
        if not comando or not isinstance(comando, dict):
            return _resultado(False, "Comando inválido o vacío.", "error")

        tipo   = comando.get("tipo", "").lower().strip()
        accion = comando.get("accion", "").strip()
        nombre = comando.get("nombre", "desconocido")

        if not accion:
            logger.warning("commands", f"Comando '{nombre}' sin acción definida.")
            return _resultado(False, f"El comando '{nombre}' no tiene acción definida.", "error")

        if tipo not in TIPOS_COMANDOS_VALIDOS:
            logger.warning("commands", f"Tipo desconocido: '{tipo}'")
            return _resultado(False, f"Tipo no reconocido: '{tipo}'. Válidos: {', '.join(TIPOS_COMANDOS_VALIDOS)}", "error")

        if tipo == "web":
            return _abrir_web(accion, nombre)
        elif tipo == "app":
            return _abrir_app(accion, nombre)
        elif tipo == "sistema":
            return _ejecutar_sistema(accion, nombre)

    except Exception as e:
        logger.log_excepcion("commands", comando.get("nombre", "?"), e)
        return _resultado(False, f"Error inesperado: {e}", "error")


def _abrir_web(url, nombre=""):
    try:
        if not url.startswith(("http://", "https://", "steam://", "spotify:")):
            url = "https://" + url
        webbrowser.open(url)
        logger.info("commands", f"Web abierta: {url}", f"comando: {nombre}")
        return _resultado(True, f"Abriendo {url} en el navegador...", "web")
    except Exception as e:
        logger.log_excepcion("commands", url, e)
        return _resultado(False, f"No se pudo abrir la URL: {e}", "web")


def _abrir_app(ruta, nombre=""):
    """
    Apertura universal — carpetas, documentos, imágenes y ejecutables.
    Detecta automáticamente el tipo y aplica la mejor técnica.
    Compatible con juegos, apps y archivos del sistema.
    """
    try:
        # 1. Limpiar ruta
        ruta = ruta.strip('"').strip("'").strip()

        # 2. Detectar protocolos especiales → redirigir a _abrir_web
        if ruta.startswith(("http://", "https://", "steam://", "spotify:")):
            return _abrir_web(ruta, nombre)

        # 3. Normalizar ruta
        ruta_limpia = os.path.normpath(ruta)

        # 4. Verificar existencia
        if not os.path.exists(ruta_limpia):
            logger.error("commands", f"No encontrado: {ruta_limpia}")
            return _resultado(False, f"No se encontró nada en: {ruta_limpia}", "app")

        # 5. Apertura según SO y tipo de archivo
        if SISTEMA == "win32":

            # Extensiones que son ejecutables
            EXE_EXTENSIONS = ('.exe', '.bat', '.cmd', '.msi', '.com')
            es_ejecutable  = ruta_limpia.lower().endswith(EXE_EXTENSIONS)
            es_carpeta     = os.path.isdir(ruta_limpia)

            if es_carpeta or not es_ejecutable:
                # Carpetas, PDFs, imágenes, documentos
                # os.startfile = doble clic nativo de Windows
                os.startfile(ruta_limpia)

            else:
                # Ejecutables — juegos, apps
                # cwd = carpeta del exe para que encuentre sus DLLs
                directorio_trabajo = os.path.dirname(ruta_limpia)
                subprocess.Popen(
                    ruta_limpia,
                    cwd=directorio_trabajo,
                    shell=True,
                    creationflags=subprocess.DETACHED_PROCESS
                )

        elif SISTEMA == "darwin":
            subprocess.Popen(["open", ruta_limpia])

        elif SISTEMA.startswith("linux"):
            subprocess.Popen(["xdg-open", ruta_limpia])

        else:
            return _resultado(False, f"SO no soportado: {SISTEMA}", "app")

        logger.info("commands", f"Apertura exitosa: {nombre or ruta_limpia}")
        return _resultado(True, f"Abriendo {nombre or 'el archivo'}...", "app")

    except PermissionError:
        logger.error("commands", f"Sin permisos: {ruta}")
        return _resultado(False, f"Sin permisos para abrir: {nombre or ruta}", "app")

    except FileNotFoundError:
        logger.error("commands", f"No encontrado: {ruta}")
        return _resultado(False, f"No se encontró: {ruta}", "app")

    except Exception as e:
        logger.log_excepcion("commands", ruta, e)
        return _resultado(False, f"Error al abrir: {str(e)}", "app")


def _ejecutar_sistema(comando_str, nombre=""):
    try:
        resultado = subprocess.run(
            comando_str,
            shell=True,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_COMANDO
        )
        if resultado.returncode == 0:
            salida = resultado.stdout.strip() or "Comando ejecutado correctamente."
            logger.info("commands", f"Sistema ejecutado: {comando_str[:50]}")
            return _resultado(True, salida, "sistema")
        else:
            error_msg = resultado.stderr.strip() or "Error desconocido."
            logger.error("commands", f"Falló: {comando_str[:50]}", error_msg[:100])
            return _resultado(False, f"El comando falló: {error_msg}", "sistema")

    except subprocess.TimeoutExpired:
        logger.error("commands", f"Timeout: {comando_str[:50]}")
        return _resultado(False, "El comando tardó demasiado y fue cancelado.", "sistema")
    except Exception as e:
        logger.log_excepcion("commands", comando_str, e)
        return _resultado(False, f"Error al ejecutar: {e}", "sistema")


def formatear_comando(cmd):
    try:
        return {
            "id":             cmd["id"],
            "nombre":         cmd["nombre"],
            "palabras_clave": cmd["palabras_clave"],
            "accion":         cmd["accion"],
            "tipo":           cmd["tipo"],
            "descripcion":    cmd["descripcion"],
            "prioridad":      cmd["prioridad"],
            "activo":         cmd["activo"],
            "veces_usado":    cmd["veces_usado"]
        }
    except Exception as e:
        logger.error("commands", "Error formateando comando", str(e))
        return {}


def obtener_sistema():
    sistemas = {"win32": "Windows", "darwin": "macOS", "linux": "Linux"}
    return sistemas.get(SISTEMA, f"Desconocido ({SISTEMA})")


def _resultado(exito, mensaje, tipo):
    return {
        "exito":   exito,
        "mensaje": mensaje,
        "tipo":    tipo
    }
def ejecutar_comando_compuesto(id_comando, nombre=""):
    """
    Ejecuta todas las acciones de un comando compuesto
    en orden secuencial.

    Retorna: dict con resultado general
    """
    from database import obtener_acciones_compuestas

    acciones = obtener_acciones_compuestas(id_comando)

    if not acciones:
        return _resultado(False, "El comando no tiene acciones guardadas.", "compuesto")

    resultados  = []
    todas_ok    = True
    mensajes    = []

    for accion in acciones:
        orden       = accion["orden"]
        ruta_accion = accion["accion"]
        tipo        = accion["tipo"]
        descripcion = accion["descripcion"] or ruta_accion

        logger.info(
            "commands",
            f"Ejecutando acción {orden}/{len(acciones)}: {descripcion}"
        )

        if tipo == "web":
            resultado = _abrir_web(ruta_accion, descripcion)
        elif tipo == "app":
            resultado = _abrir_app(ruta_accion, descripcion)
        elif tipo == "sistema":
            resultado = _ejecutar_sistema(ruta_accion, descripcion)
        else:
            resultado = _resultado(False, f"Tipo desconocido: {tipo}", tipo)

        resultados.append(resultado)
        mensajes.append(f"  {orden}. {descripcion} → {'✅' if resultado['exito'] else '❌'}")

        if not resultado["exito"]:
            todas_ok = False
            logger.warning(
                "commands",
                f"Falló acción {orden}: {descripcion}",
                resultado.get("mensaje", "")
            )

    # Construir mensaje resumen
    resumen = f"Comando '{nombre}' ejecutado:\n" + "\n".join(mensajes)

    return {
        "exito":      todas_ok,
        "mensaje":    resumen,
        "tipo":       "compuesto",
        "resultados": resultados
    }