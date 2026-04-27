# 📁 sara.py
# Archivo principal de SARA — Sistema Autónomo de Razonamiento Artificial
# Orquesta todos los módulos y controla el flujo completo

import sys
import random
from utils import normalizar_texto
import database
import brain
import io_manager
import commands
import learning
import external_service
import logger
import embeddings
import context
import splitter
import social
import searcher
import voice
from database import actualizar_resultado_intencion, guardar_vector_conocimiento
from config import (
    VERSION,
    MOSTRAR_CONFIANZA,
    BUSQUEDA_EXTERNA_ACTIVA,
    MODO_VOZ,
    USAR_RESPALDO_EXTERNO,
    GUARDAR_RESPALDO_AUTO
)

# ──────────────────────────────────────────────
# 🔹 MEMORIA TEMPORAL
# ──────────────────────────────────────────────

# Constantes de validación
OPCIONES_RESPUESTA_VALIDAS = {"1", "2", "3"}
OPCIONES_RESPUESTA_SIN_EXTERNO = {"1", "2"}
OPCIONES_COMANDO = {"1", "2"}
LOG_TRUNCATE = 50

_ultima_interaccion = {
    "pregunta":  None,
    "respuesta": None,
    "tipo":      None
}


# ──────────────────────────────────────────────
# 🔹 INICIALIZACIÓN
# ──────────────────────────────────────────────

def inicializar():
    """
    Prepara todo el sistema antes de arrancar.
    Retorna: True si todo OK, False si algo falló
    """
    try:
        # 1. Base de datos + migraciones
        database.crear_tablas()
        logger.debug("sara", "Base de datos inicializada.")

        # 2. Embeddings semánticos
        modelo_ok = embeddings.cargar_modelo()
        if modelo_ok:
            logger.info("sara", "Motor semántico activo.")
        else:
            logger.warning("sara", "Motor semántico no disponible.")

        # 3. Conexión a internet si búsqueda externa activa
        if BUSQUEDA_EXTERNA_ACTIVA:
            tiene_internet = external_service.verificar_conexion()
            if not tiene_internet:
                logger.warning("sara", "Sin conexión a internet.")
                io_manager.mostrar_respuesta(
                    "Aviso: Sin conexión. Funcionaré solo con conocimiento local."
                )

        # 5. Modo voz si está activado en config
        if MODO_VOZ:
            voz_ok = voice.inicializar()
            if voz_ok:
                io_manager.activar_modo_voz(voice)
                logger.info("sara", "Modo voz activado al arranque.")
            else:
                logger.warning("sara", "No se pudo inicializar el modo voz.")

        # 6. Registrar inicio
        logger.log_inicio()
        logger.info("sara", f"SARA v{VERSION} iniciada correctamente.")
        io_manager.mostrar_bienvenida()
        return True

    except Exception as e:
        logger.log_excepcion("sara", "inicializar", e)
        print(f"[SARA CRÍTICO] Error al inicializar: {e}")
        return False


# ──────────────────────────────────────────────
# 🔹 FUNCIÓN AUXILIAR (REFACTOR DUPLICACIÓN)
# ──────────────────────────────────────────────

def _procesar_aprendizaje_respuesta(entrada_original):
    """
    Extrae la lógica duplicada de enseñar respuesta.
    Reutilizable en múltiples contextos.
    """
    respuesta_nueva = io_manager.solicitar_respuesta_nueva()

    if not respuesta_nueva:
        return "De acuerdo, lo omito por ahora."

    resultado_aprendizaje = learning.aprender_pregunta(
        entrada_original,
        respuesta_nueva
    )

    exito = resultado_aprendizaje.get("exito", False)
    accion = resultado_aprendizaje.get("accion", "")

    if exito:
        logger.info(
            "sara",
            f"Aprendizaje exitoso: '{entrada_original[:LOG_TRUNCATE]}'"
        )
        return "¡Entendido! Lo recordaré para la próxima."
    elif accion == "duplicada":
        return resultado_aprendizaje.get("mensaje", "")
    else:
        return f"No pude guardar eso. {resultado_aprendizaje.get('mensaje', '')}"


def _validar_opcion(opcion, opciones_validas):
    """
    Valida que la opción elegida esté en el conjunto válido.
    Retorna: opción si es válida, None si no
    """
    if opcion.strip() in opciones_validas:
        return opcion.strip()
    logger.debug("sara", f"Opción inválida: {opcion}")
    return None


# ──────────────────────────────────────────────
# 🔹 MANEJO DE RESULTADO
# ──────────────────────────────────────────────
def _manejar_resultado(resultado, entrada_original, entrada_usuario=None):
    """
    Interpreta el dict de brain.procesar() y ejecuta la acción.
    entrada_original: texto procesado por contexto (va a BD)
    entrada_usuario:  texto crudo del usuario (se muestra)
    """
    texto_mostrar = entrada_usuario or entrada_original

    tipo      = resultado.get("tipo")
    texto     = resultado.get("texto", "")
    comando   = resultado.get("comando")
    confianza = resultado.get("confianza", 0.0)
    query     = resultado.get("query", "")

    # ── RESPUESTA A PREGUNTA ──────────────────
    if tipo == "respuesta":

        if confianza >= brain.UMBRAL_PREGUNTA:
            logger.log_pregunta(entrada_original, respuesta=texto, correcta=True)
            try:
                actualizar_resultado_intencion(query, "correcto")
            except Exception as e:
                logger.debug("sara", f"No se pudo actualizar intencion correcta: {e}")
            return texto

        else:
            # ── SARA no supo responder ────────────────
            io_manager.mostrar_respuesta(
                f"No tengo respuesta local para: '{texto_mostrar}'"
            )
            logger.log_pregunta(entrada_original, respuesta=None, correcta=False)

            try:
                actualizar_resultado_intencion(query, "sin_respuesta")
            except Exception as e:
                logger.debug("sara", f"No se pudo actualizar intencion sin_respuesta: {e}")

            # ── Preguntar antes de buscar externamente ──

            if USAR_RESPALDO_EXTERNO:
                print("\nSARA: No tengo respuesta local para eso.")
                print("  1. Buscar externamente")
                print("  2. Enseñarme tú la respuesta")
                print("  3. Ignorar")

                try:
                    opcion = io_manager.show_prompt("\n  Selecciona una opción: ")
                    opcion = _validar_opcion(opcion, OPCIONES_RESPUESTA_VALIDAS)
                    if not opcion:
                        return "Opción inválida. Operación cancelada."
                except KeyboardInterrupt:
                    return "De acuerdo, lo dejamos para después."

                if opcion == "1":
                    io_manager.mostrar_respuesta("Buscando en fuentes externas...")
                    respuesta_ext, fuente = external_service.obtener_respuesta_externa(
                        entrada_original
                    )

                    if respuesta_ext:
                        io_manager.mostrar_respuesta(
                            f"[{fuente}]: {respuesta_ext}"
                        )

                        if GUARDAR_RESPALDO_AUTO:
                            resultado_guardado = learning.aprender_pregunta(
                                entrada_original,
                                respuesta_ext
                            )
                            if resultado_guardado.get("exito"):
                                logger.info(
                                    "sara",
                                    f"Respuesta de {fuente} guardada en BD",
                                    f"pregunta: '{entrada_original[:40]}'"
                                )
                                io_manager.mostrar_respuesta(
                                    "✅ Lo aprendí para la próxima vez."
                                )

                        return respuesta_ext

                    io_manager.mostrar_respuesta(
                        "No encontré respuesta externa."
                    )
                    return "De acuerdo, lo dejo para después."

                elif opcion == "2":
                    return _procesar_aprendizaje_respuesta(entrada_original)

                else:
                    logger.info("sara", f"Usuario ignoró: '{entrada_original[:LOG_TRUNCATE]}'")
                    return "De acuerdo, lo tendré en cuenta para mejorar."

            # Si no está habilitado el respaldo externo, preguntar al usuario normal.
            print("\nSARA: ¿Qué quieres hacer?")
            print("  1. Enseñarme tú la respuesta")
            print("  2. Ignorar")

            try:
                opcion = io_manager.show_prompt("\n  Selecciona una opción: ")
                opcion = _validar_opcion(opcion, OPCIONES_RESPUESTA_SIN_EXTERNO)
                if not opcion:
                    return "Opción inválida. Operación cancelada."
            except KeyboardInterrupt:
                return "De acuerdo, lo dejamos para después."

            if opcion == "1":
                return _procesar_aprendizaje_respuesta(entrada_original)
            else:
                logger.info("sara", f"Usuario ignoró: '{entrada_original[:LOG_TRUNCATE]}'")
                return "De acuerdo, lo tendré en cuenta para mejorar."

    # ── EJECUCIÓN DE COMANDO ──────────────────
    elif tipo == "comando":
        if comando and isinstance(comando, dict):
            from database import es_comando_compuesto
            from commands import ejecutar_comando_compuesto

            id_cmd = comando.get("id")

            # ── Verificar si es comando compuesto ────
            if id_cmd and es_comando_compuesto(id_cmd):
                resultado_cmd = ejecutar_comando_compuesto(
                    id_cmd,
                    comando.get("nombre", "")
                )
            else:
                resultado_cmd = commands.ejecutar_comando(comando)

            exito     = resultado_cmd.get("exito", False)
            mensaje_cmd = resultado_cmd.get("mensaje", "")

            logger.log_comando(comando, exito=exito)

            if not exito:
                logger.warning(
                    "sara",
                    f"Comando falló: {comando.get('nombre', '?')}",
                    mensaje_cmd
                )

            return mensaje_cmd if mensaje_cmd else "Comando ejecutado."

        else:
            # ── Comando no reconocido ─────────────────
            io_manager.mostrar_respuesta(
                f"No reconozco ese comando: '{texto_mostrar}'"
            )
            logger.log_intencion_desconocida(entrada_original)

            print("\nSARA: ¿Qué quieres hacer?")
            print("  1. Enseñarme cómo ejecutar este comando")
            print("  2. Ignorar")

            try:
                opcion = input("\n  Selecciona una opción: ").strip()
            except KeyboardInterrupt:
                return "De acuerdo."

            if opcion == "1":
                print("SARA: ¿Cómo quieres llamar a este comando?")
                nombre = input("  → Nombre: ").strip()

                if not nombre:
                    return "Nombre vacío. Registro cancelado."

                # ── Preguntar si es compuesto ─────────
                print("\nSARA: ¿Este comando ejecutará más de una acción?")
                print("  1. No — acción simple (como siempre)")
                print("  2. Sí — comando compuesto (múltiples acciones)")

                try:
                    tipo_cmd = input("\n  Elige (1/2): ").strip()
                except KeyboardInterrupt:
                    return "Registro cancelado."

                if tipo_cmd == "2":
                    # ── Flujo comando compuesto ───────
                    print(f"\nSARA: Registrando comando compuesto '{nombre}'")

                    palabras_clave = input("  → Palabras clave (separadas por coma): ").strip()
                    descripcion    = input("  → Descripción general (opcional): ").strip()

                    acciones = io_manager.solicitar_acciones_multiples()

                    if acciones:
                        resultado_cmd = learning.aprender_comando_compuesto(
                            nombre,
                            palabras_clave,
                            acciones,
                            descripcion
                        )
                        exito   = resultado_cmd.get("exito", False)
                        mensaje = resultado_cmd.get("mensaje", "")

                        if exito:
                            logger.info("sara", f"Comando compuesto aprendido: '{nombre}'")
                            return f"¡Listo! '{nombre}' ejecutará {len(acciones)} acciones."
                        elif resultado_cmd.get("accion") == "duplicada":
                            return mensaje
                        else:
                            return f"No pude guardar el comando. {mensaje}"
                    else:
                        return "Registro cancelado."

                else:
                    # ── Flujo comando simple ──────────
                    datos = io_manager.solicitar_datos_comando()

                    if datos:
                        resultado_cmd = learning.aprender_comando(
                            nombre,
                            datos.get("palabras_clave", ""),
                            datos.get("accion", ""),
                            datos.get("tipo", ""),
                            datos.get("descripcion", "")
                        )
                        exito   = resultado_cmd.get("exito", False)
                        mensaje = resultado_cmd.get("mensaje", "")

                        if exito:
                            logger.info("sara", f"Comando aprendido: '{nombre}'")
                            return f"¡Listo! Aprendí el comando '{nombre}'."
                        elif resultado_cmd.get("accion") == "duplicada":
                            return mensaje
                        else:
                            return f"No pude guardar el comando. {mensaje}"

                    return "Registro cancelado."

            else:
                logger.info(
                    "sara",
                    f"Usuario ignoró comando: '{entrada_original[:50]}'"
                )
                return "De acuerdo, lo omito por ahora."
    # ── BÚSQUEDA DINÁMICA ─────────────────────
    elif tipo == "busqueda":
        busqueda = resultado.get("busqueda", {})
        url      = busqueda.get("url", "")
        mensaje  = busqueda.get("mensaje", "")

        if url:
            resultado_cmd = commands._abrir_web(
                url,
                busqueda.get("plataforma", "")
            )

            exito = resultado_cmd.get("exito", False)

            if exito:
                logger.info(
                    "sara",
                    f"Búsqueda ejecutada: '{busqueda.get('termino')}'",
                    f"plataforma: {busqueda.get('plataforma')}"
                )
                return mensaje

            return f"No pude abrir la búsqueda. {resultado_cmd.get('mensaje', '')}"

        return "No pude construir la búsqueda."

    # ── BÚSQUEDA EXTERNA ─────────────────────
    elif tipo == "externo":
        if BUSQUEDA_EXTERNA_ACTIVA:
            resultado_ext = external_service.buscar_web(query)
            resultados    = resultado_ext.get("resultados", [])

            if resultados:
                external_service.guardar_resultados_web(query, resultados)
                return "\n".join(f"  • {r}" for r in resultados)

        return "No encontré información externa sobre eso."

    # ── DESCONOCIDO ───────────────────────────
    else:
        logger.log_intencion_desconocida(entrada_original)
        return texto if texto else "No entendí lo que dijiste."

# ──────────────────────────────────────────────
# 🔹 CORRECCIÓN
# ──────────────────────────────────────────────

def _manejar_correccion():
    global _ultima_interaccion

    if not _ultima_interaccion["pregunta"]:
        return "No recuerdo qué respondí antes."

    pregunta        = _ultima_interaccion["pregunta"]
    respuesta_vieja = _ultima_interaccion["respuesta"]
    tipo            = _ultima_interaccion["tipo"]

    if tipo != "pregunta":
        return "Solo puedo corregir respuestas a preguntas."

    io_manager.mostrar_respuesta(
        f"Entendido. Mi respuesta anterior fue:\n"
        f"  '{respuesta_vieja}'\n"
        f"¿Cuál es la respuesta correcta?"
    )

    try:
        respuesta_nueva = io_manager.show_prompt("  → ")
    except KeyboardInterrupt:
        return "Corrección cancelada."

    if not respuesta_nueva or respuesta_nueva.lower() == "cancelar":
        return "Corrección cancelada."

    resultado = learning.corregir_pregunta(pregunta, respuesta_nueva)
    exito     = resultado.get("exito", False)

    if exito:
        if embeddings.esta_disponible():
            vector = embeddings.vector_desde_texto(pregunta)
            if vector:
                guardar_vector_conocimiento(pregunta, vector)
                logger.debug("sara", f"Vector regenerado: '{pregunta[:LOG_TRUNCATE]}'")

        try:
            actualizar_resultado_intencion(pregunta, "corregido")
        except Exception as e:
            logger.debug("sara", f"No se pudo actualizar intencion corregida: {e}")

        logger.info(
            "sara",
            f"Corrección aplicada: '{pregunta[:LOG_TRUNCATE]}'",
            f"vieja: '{respuesta_vieja[:LOG_TRUNCATE]}' → nueva: '{respuesta_nueva[:LOG_TRUNCATE]}'"
        )

        _ultima_interaccion = {"pregunta": None, "respuesta": None, "tipo": None}
        return "¡Gracias por la corrección! Lo recordaré correctamente."

    else:
        error_msg = resultado.get('mensaje', '')
        logger.warning("sara", f"Fallo en corrección: {error_msg}")
        return f"No pude aplicar la corrección. {error_msg}"


# ──────────────────────────────────────────────
# 🔹 FUSIÓN DE RESPUESTAS
# ──────────────────────────────────────────────

def _fusionar_respuestas(resultados):
    for entrada, resultado, respuesta in resultados:
        if resultado.get("tipo") != "respuesta":
            return False, "", 0.0
        if resultado.get("confianza", 0.0) < brain.UMBRAL_PREGUNTA:
            return False, "", 0.0
        if not respuesta or respuesta.startswith("No tengo"):
            return False, "", 0.0

    if len(resultados) > 1 and embeddings.esta_disponible():
        respuesta_base = resultados[0][2]
        for _, _, respuesta in resultados[1:]:
            if embeddings.similitud_semantica(respuesta_base, respuesta) < 0.30:
                return False, "", 0.0

    CONECTORES = ["Además, ", "También, ", "Asimismo, ", "Por otro lado, "]
    partes      = []
    confianzas  = []

    for i, (_, resultado, respuesta) in enumerate(resultados):
        confianzas.append(resultado.get("confianza", 0.0))
        if i == 0:
            parte = respuesta[0].upper() + respuesta[1:] if respuesta else ""
        else:
            conector = random.choice(CONECTORES)
            parte    = conector + respuesta[0].lower() + respuesta[1:] if respuesta else ""
        if parte and not parte.endswith((".", "!", "?")):
            parte += "."
        partes.append(parte)

    return True, " ".join(partes), sum(confianzas) / len(confianzas)


# ──────────────────────────────────────────────
# 🔹 COMANDOS INTERNOS
# ──────────────────────────────────────────────

def _manejar_comando_interno(texto):
    texto_lower = texto.strip().lower()

    if texto_lower in ("/ayuda", "/help"):
        ayuda = (
            "\n Comandos internos de SARA:\n"
            "  /ayuda       → Muestra esta ayuda\n"
            "  /stats       → Estadísticas del sistema\n"
            "  /aprender    → Enseñar nueva pregunta/respuesta\n"
            "  /version     → Versión actual de SARA\n"
            "  /plataformas → Plataformas de búsqueda\n"
            "  /voz         → Activar modo voz\n"
            "  /texto       → Desactivar modo voz\n"
            "  /microfonos  → Ver micrófonos disponibles\n"
        )
        return True, ayuda

    elif texto_lower == "/plataformas":
        plataformas = searcher.plataformas_disponibles()
        respuesta   = "\n Plataformas disponibles:\n"
        for p in plataformas:
            respuesta += f"  → {p}\n"
        return True, respuesta

    elif texto_lower == "/version":
        return True, f"SARA — Sistema Autónomo de Razonamiento Artificial v{VERSION}"

    elif texto_lower == "/stats":
        stats        = learning.obtener_estadisticas()
        stats_social = database.obtener_stats_sociales()
        if stats:
            respuesta = (
                f"\n Estadísticas de SARA:\n"
                f"  Conocimientos:  {stats.get('total_conocimientos', 0)}\n"
                f"  Comandos:       {stats.get('total_comandos', 0)}\n"
            )
            if stats_social:
                respuesta += "\n Interacciones sociales:\n"
                for fila in stats_social:
                    respuesta += f"  {fila['tipo_social']:15} → {fila['total']}\n"
        else:
            respuesta = "No se pudieron obtener estadísticas."
        return True, respuesta

    elif texto_lower in ("activar modo voz", "activar voz", "/voz"):
        if io_manager.esta_en_modo_gui():
            return True, "Modo voz no disponible en interfaz GUI. Usa el modo terminal."
        if not voice.esta_disponible():
            voz_ok = voice.inicializar()
            if not voz_ok:
                return True, "No pude inicializar el micrófono."
        io_manager.activar_modo_voz(voice)
        logger.info("sara", "Modo voz activado por usuario.")
        return True, "🎤 Modo voz activado. Di 'sara' para activarme."

    elif texto_lower in ("desactivar modo voz", "desactivar voz","desactiva el modo  voz","desactivar voz", "/texto"):
        io_manager.desactivar_modo_voz()
        logger.info("sara", "Modo voz desactivado por usuario.")
        return True, "⌨️ Modo voz desactivado. Volviendo a modo texto."

    elif texto_lower == "/microfonos":
        if io_manager.esta_en_modo_gui():
            return True, "Comando no disponible en interfaz GUI."
        print("\n Micrófonos disponibles:")
        voice.listar_microfonos()
        return True, ""

    elif texto_lower == "/aprender":
        if io_manager.esta_en_modo_gui():
            return True, "Modo aprendizaje no disponible en interfaz GUI. Usa el modo terminal."
        return True, _flujo_aprendizaje()

    return False, ""


def _flujo_aprendizaje():
    try:
        io_manager.mostrar_respuesta("Modo aprendizaje activado.")
        io_manager.mostrar_respuesta("Escribe la pregunta (o 'cancelar'):")
        pregunta = io_manager.show_prompt("  Pregunta: ")
        if pregunta and pregunta.lower() == "cancelar":
            return "Aprendizaje cancelado."

        io_manager.mostrar_respuesta("Escribe la respuesta correcta:")
        respuesta = io_manager.show_prompt("  Respuesta: ")

        if not pregunta or not respuesta:
            return "Pregunta o respuesta vacía. Cancelado."

        resultado = learning.aprender_pregunta(pregunta, respuesta)
        return resultado.get("mensaje", "Error en aprendizaje.")

    except KeyboardInterrupt:
        return "\nAprendizaje cancelado."
    except Exception as e:
        logger.log_excepcion("sara", "_flujo_aprendizaje", e)
        return f"Error: {e}"


# ──────────────────────────────────────────────
# 🔹 PROCESAMIENTO CENTRALIZADO DE ENTRADA
# ──────────────────────────────────────────────

def _procesar_entrada_centralizado(entrada_original):
    """
    Lógica CENTRALIZADA de procesamiento de entrada.
    Utilizada por run() y procesar_comando().
    Retorna: (tipo_resultado, respuesta_final)
    """
    # 2. Comandos internos
    manejado, respuesta_interna = _manejar_comando_interno(entrada_original)
    if manejado:
        return "interno", respuesta_interna

    # 3. Corrección
    if social.es_correccion(entrada_original) and _ultima_interaccion["pregunta"]:
        return "correccion", _manejar_correccion()

    # 4. Entrada social
    es_social, respuesta_social = social.detectar_entrada_social(entrada_original)
    if es_social:
        return "social", respuesta_social

    # 5. Splitter
    entradas = splitter.dividir_entrada(entrada_original)

    # Flujo múltiple
    if len(entradas) > 1:
        resultados_multiples = []

        for entrada_individual in entradas:
            entrada_procesada = entrada_individual
            tema_resuelto = None

            if context.necesita_contexto(entrada_individual):
                entrada_procesada, tema_resuelto = context.resolver(entrada_individual)
                if entrada_procesada != entrada_individual:
                    logger.debug(
                        "sara",
                        f"Contexto: '{entrada_individual}' → '{entrada_procesada}'"
                    )

            resultado = brain.procesar(entrada_procesada)
            respuesta_final = _manejar_resultado(resultado, entrada_procesada, entrada_individual)

            if (
                resultado.get("tipo") == "respuesta"
                and resultado.get("confianza", 0) >= brain.UMBRAL_PREGUNTA
            ):
                _ultima_interaccion["pregunta"] = entrada_procesada
                _ultima_interaccion["respuesta"] = respuesta_final
                _ultima_interaccion["tipo"] = "pregunta"

            if resultado.get("tipo") == "respuesta":
                context.actualizar(entrada_procesada, respuesta_final, tema=tema_resuelto)

            resultados_multiples.append((entrada_individual, resultado, respuesta_final))

        fusionado, respuesta_fusion, confianza_fusion = _fusionar_respuestas(
            resultados_multiples
        )

        if fusionado:
            logger.debug("sara", f"Respuestas fusionadas: {len(resultados_multiples)}")
            respuesta_mostrar = respuesta_fusion
            confianza_mostrar = confianza_fusion
        else:
            respuesta_mostrar = "\n".join(
                [r for _, _, r in resultados_multiples]
            )
            confianza_mostrar = (
                sum(r.get("confianza", 0.0) for _, r, _ in resultados_multiples)
                / len(resultados_multiples)
            )

        return "multiple", respuesta_mostrar, confianza_mostrar

    # Flujo normal
    entrada_procesada = entrada_original
    tema_resuelto = None

    if context.necesita_contexto(entrada_original):
        entrada_procesada, tema_resuelto = context.resolver(entrada_original)
        if entrada_procesada != entrada_original:
            logger.debug(
                "sara",
                f"Contexto: '{entrada_original}' → '{entrada_procesada}'"
            )

    resultado = brain.procesar(entrada_procesada)
    respuesta_final = _manejar_resultado(resultado, entrada_procesada, entrada_original)

    if (
        resultado.get("tipo") == "respuesta"
        and resultado.get("confianza", 0) >= brain.UMBRAL_PREGUNTA
    ):
        _ultima_interaccion["pregunta"] = entrada_procesada
        _ultima_interaccion["respuesta"] = respuesta_final
        _ultima_interaccion["tipo"] = "pregunta"

    if resultado.get("tipo") == "respuesta":
        context.actualizar(entrada_procesada, respuesta_final, tema=tema_resuelto)

    return (
        "normal",
        respuesta_final,
        resultado.get("confianza", 0.0),
    )

# ──────────────────────────────────────────────
# 🔹 BUCLE PRINCIPAL
# ──────────────────────────────────────────────

def run():
    """Bucle principal del sistema SARA (Modo Terminal/CLI)."""
    while True:
        try:
            entrada = io_manager.obtener_input()

            if not entrada or not entrada.strip():
                continue

            # 1. Verificar salida
            if io_manager.es_comando_salida(entrada):
                logger.log_cierre()
                io_manager.mostrar_despedida()
                break

            # Procesar entrada centralizado
            tipo_resultado, respuesta, *confianza_opt = _procesar_entrada_centralizado(
                entrada
            )

            io_manager.mostrar_respuesta(respuesta)

            if MOSTRAR_CONFIANZA and confianza_opt:
                io_manager.mostrar_confianza(confianza_opt[0])

            io_manager.mostrar_separador()

        except KeyboardInterrupt:
            logger.log_cierre()
            io_manager.mostrar_despedida()
            break

        except Exception as e:
            logger.log_excepcion("sara", "run", e)
            io_manager.mostrar_error(f"Error inesperado: {e}")


# ──────────────────────────────────────────────
# 🔹 PROCESAR COMANDO (PARA GUI)
# ──────────────────────────────────────────────

def procesar_comando(entrada):
    """Procesa una entrada del usuario (versión para GUI)."""
    try:
        if not entrada or not entrada.strip():
            return

        # Procesar entrada centralizado
        tipo_resultado, respuesta, *confianza_opt = _procesar_entrada_centralizado(
            entrada
        )

        io_manager.mostrar_respuesta(respuesta)

        if MOSTRAR_CONFIANZA and confianza_opt:
            io_manager.mostrar_confianza(confianza_opt[0])

    except Exception as e:
        logger.log_excepcion("sara", "procesar_comando", e)
        io_manager.mostrar_error(f"Error inesperado: {e}")


# ──────────────────────────────────────────────
# 🔹 PUNTO DE ENTRADA
# ──────────────────────────────────────────────

if __name__ == "__main__":
    if not inicializar():
        logger.critical("sara", "Fallo en inicialización.")
        sys.exit(1)
    run()

    #  .\sara.bat 
    