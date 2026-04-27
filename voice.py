# 📁 voice.py
# Motor de voz de SARA
# STT: Google Speech Recognition
# TTS: edge-tts (voz neural mexicana) con fallback a pyttsx3

import speech_recognition as sr
import pyttsx3
import threading
import asyncio
import os
import logger
from utils import normalizar_texto

# ──────────────────────────────────────────────
# 🔹 ESTADOS
# ──────────────────────────────────────────────

HIBERNANDO   = "hibernando"
ACTIVADA     = "activada"
PROCESANDO   = "procesando"
RESPONDIENDO = "respondiendo"

# ──────────────────────────────────────────────
# 🔹 CONFIGURACIÓN
# ──────────────────────────────────────────────

WAKE_WORDS = {
    "sara",
    "zara",
    "sará",
    "sarah",
    "sera",
}

TIMEOUT_ESCUCHA  = 5
TIMEOUT_WAKEWORD = None
UMBRAL_ENERGIA   = 300
VELOCIDAD_VOZ    = 150
VOLUMEN_VOZ      = 1.0
IDIOMA           = "es-MX"

# Voz neural de edge-tts
# Opciones mexicanas:
# "es-MX-DaliaNeural"  → femenina (recomendada)
# "es-MX-JorgeNeural"  → masculina
VOZ_NEURAL       = "es-MX-DaliaNeural"
USAR_VOZ_NEURAL  = True   # False → usa pyttsx3 como antes

# Archivo temporal para audio
AUDIO_TEMP = "sara_temp_audio.mp3"

# ──────────────────────────────────────────────
# 🔹 ESTADO GLOBAL
# ──────────────────────────────────────────────

_estado      = HIBERNANDO
_reconocedor = None
_microfono   = None
_disponible  = False
_hablando    = False
_edge_disponible = False


# ──────────────────────────────────────────────
# 🔹 INICIALIZACIÓN
# ──────────────────────────────────────────────

def inicializar():
    """
    Inicializa STT y TTS.
    Intenta usar edge-tts primero, fallback a pyttsx3.
    Retorna: True si todo OK, False si falló
    """
    global _reconocedor, _microfono, _disponible, _edge_disponible

    try:
        # ── STT ───────────────────────────────
        _reconocedor = sr.Recognizer()
        _reconocedor.energy_threshold         = UMBRAL_ENERGIA
        _reconocedor.dynamic_energy_threshold = True
        _reconocedor.pause_threshold          = 0.8

        _microfono = sr.Microphone()
        with _microfono as fuente:
            _reconocedor.adjust_for_ambient_noise(fuente, duration=1)

        # ── TTS — Verificar edge-tts ──────────
        if USAR_VOZ_NEURAL:
            try:
                import edge_tts
                _edge_disponible = True
                logger.info("voice", f"Voz neural activa: {VOZ_NEURAL}")
            except ImportError:
                _edge_disponible = False
                logger.warning(
                    "voice",
                    "edge-tts no disponible — usando pyttsx3",
                    "pip install edge-tts"
                )

        # ── TTS — Verificar pyttsx3 como fallback ──
        if not _edge_disponible:
            motor_prueba = pyttsx3.init()
            motor_prueba.stop()
            logger.info("voice", "Usando pyttsx3 como motor de voz.")

        _disponible = True
        logger.info("voice", "Motor de voz inicializado correctamente.")
        return True

    except Exception as e:
        logger.log_excepcion("voice", "inicializar", e)
        _disponible = False
        return False


def esta_disponible():
    return _disponible


def obtener_estado():
    return _estado


# ──────────────────────────────────────────────
# 🔹 TEXT TO SPEECH — HABLAR
# ──────────────────────────────────────────────

def hablar(texto):
    """
    Convierte texto a voz.
    Usa edge-tts si está disponible (voz natural mexicana)
    Fallback a pyttsx3 si no hay internet o edge-tts falla.
    """
    global _hablando

    if not _disponible or not texto or not texto.strip():
        return

    texto_limpio = _limpiar_para_voz(texto)

    if _edge_disponible and USAR_VOZ_NEURAL:
        _hablar_edge(texto_limpio)
    else:
        _hablar_pyttsx3(texto_limpio)


def hablar_async(texto):
    """Habla en hilo separado para no bloquear SARA."""
    hilo = threading.Thread(
        target=hablar,
        args=(texto,),
        daemon=True
    )
    hilo.start()


def _hablar_edge(texto):
    """
    Habla usando edge-tts — voz neural mexicana.
    """
    global _hablando

    try:
        _hablando = True
        import edge_tts

        # ── Silenciar mensaje de bienvenida de pygame ──
        import os
        os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
        import pygame
        # ───────────────────────────────────────────────

        # Generar audio con voz neural
        async def _generar():
            comunicar = edge_tts.Communicate(texto, VOZ_NEURAL)
            await comunicar.save(AUDIO_TEMP)

        asyncio.run(_generar())

        # Reproducir con pygame
        pygame.mixer.init()
        pygame.mixer.music.load(AUDIO_TEMP)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        pygame.mixer.quit()

        if os.path.exists(AUDIO_TEMP):
            os.remove(AUDIO_TEMP)

        _hablando = False

    except ImportError:
        logger.warning("voice", "pygame no instalado — usando pyttsx3")
        _hablar_pyttsx3(texto)
    except Exception as e:
        _hablando = False
        logger.error("voice", f"Error edge-tts: {e} — usando pyttsx3")
        _hablar_pyttsx3(texto)
def _hablar_pyttsx3(texto):
    """
    Habla usando pyttsx3 — fallback sin internet.
    Crea motor nuevo por llamada para evitar conflictos threading.
    """
    global _hablando

    try:
        _hablando = True
        motor     = pyttsx3.init()
        motor.setProperty("rate",   VELOCIDAD_VOZ)
        motor.setProperty("volume", VOLUMEN_VOZ)

        # Buscar voz en español
        voces = motor.getProperty("voices")
        voz_encontrada = False
        for voz in voces:
            if "spanish" in voz.name.lower() or "es" in voz.id.lower():
                motor.setProperty("voice", voz.id)
                voz_encontrada = True
                break

        if not voz_encontrada:
            logger.warning("voice", "Sin voz española — usando voz por defecto")

        motor.say(texto)
        motor.runAndWait()
        motor.stop()
        _hablando = False

    except Exception as e:
        _hablando = False
        logger.error("voice", f"Error pyttsx3: {e}")


# ──────────────────────────────────────────────
# 🔹 SPEECH TO TEXT — WAKE WORD
# ──────────────────────────────────────────────

def escuchar_wakeword():
    """
    Modo hibernación — escucha wake words.

    MEJORA: detecta frases unidas como "sara abre youtube"
    → extrae "abre youtube" directamente
    → evita segunda escucha

    Retorna: (detectado: bool, comando_inline: str | None)
      detectado=True, comando_inline=None   → solo wake word
      detectado=True, comando_inline="texto"→ wake word + comando
      detectado=False, comando_inline=None  → no detectado
    """
    global _estado

    if not _disponible:
        return False, None

    _estado = HIBERNANDO

    try:
        with _microfono as fuente:
            try:
                audio = _reconocedor.listen(
                    fuente,
                    timeout=TIMEOUT_WAKEWORD,
                    phrase_time_limit=5  # ← aumentado a 5s para frases unidas
                )

                texto = _reconocedor.recognize_google(
                    audio,
                    language=IDIOMA
                ).lower().strip()

                texto_norm = normalizar_texto(texto)
                palabras   = texto_norm.split()

                logger.debug("voice", f"Audio detectado: '{texto}'")

                # ── Verificar cada wake word ──────────
                for wake in WAKE_WORDS:
                    wake_norm = normalizar_texto(wake)

                    # CASO 1: Texto exacto = wake word
                    # "sara" → activar, esperar comando
                    if texto_norm == wake_norm:
                        logger.debug("voice", f"Wake word exacta: '{wake}'")
                        return True, None

                    # CASO 2: Empieza con wake word + tiene más texto
                    # "sara abre youtube" → activar + extraer "abre youtube"
                    if texto_norm.startswith(wake_norm + " "):
                        comando_inline = texto_norm[len(wake_norm):].strip()
                        if comando_inline:
                            logger.info(
                                "voice",
                                f"Frase unida detectada: '{texto}'",
                                f"comando: '{comando_inline}'"
                            )
                            return True, comando_inline
                        return True, None

                    # CASO 3: Wake word en frase corta (≤2 palabras)
                    # "oye sara" → activar, esperar comando
                    if len(palabras) <= 2 and wake_norm in palabras:
                        logger.debug("voice", f"Wake word en frase corta: '{wake}'")
                        return True, None

                # Texto largo sin wake word → ignorar
                return False, None

            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                logger.error("voice", f"Error STT: {e}")

        return False, None

    except Exception as e:
        logger.log_excepcion("voice", "escuchar_wakeword", e)
        return False, None


# ──────────────────────────────────────────────
# 🔹 SPEECH TO TEXT — COMANDO
# ──────────────────────────────────────────────

def escuchar_comando():
    """
    Modo activo — captura comando completo.
    Retorna: str con texto, o None si falló/timeout
    """
    global _estado

    if not _disponible:
        return None

    _estado = ACTIVADA
    print("🎤 SARA: Escuchando...")

    try:
        with _microfono as fuente:
            try:
                audio = _reconocedor.listen(
                    fuente,
                    timeout=TIMEOUT_ESCUCHA,
                    phrase_time_limit=10
                )

                _estado = PROCESANDO
                print("🧠 SARA: Procesando...")

                texto = _reconocedor.recognize_google(
                    audio,
                    language=IDIOMA
                ).strip()

                if not texto:
                    return None

                logger.info("voice", f"Comando capturado: '{texto}'")
                return texto

            except sr.WaitTimeoutError:
                print("💤 SARA: No escuché nada, volviendo a espera...")
                return None
            except sr.UnknownValueError:
                print("❓ SARA: No entendí, intenta de nuevo.")
                return None
            except sr.RequestError as e:
                logger.error("voice", f"Error STT: {e}")
                return None

    except Exception as e:
        logger.log_excepcion("voice", "escuchar_comando", e)
        return None

    finally:
        _estado = HIBERNANDO


# ──────────────────────────────────────────────
# 🔹 UTILIDADES
# ──────────────────────────────────────────────

def _limpiar_para_voz(texto):
    """Limpia texto antes de leerlo en voz alta."""
    import re
    texto = re.sub(r'[^\w\s\.\,\!\?\:\-áéíóúüñÁÉÍÓÚÜÑ]', ' ', texto)
    texto = re.sub(r'https?://\S+', 'el enlace', texto)
    texto = re.sub(r'\*+', '', texto)
    texto = re.sub(r'#+', '', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


def listar_microfonos():
    """Lista los micrófonos disponibles."""
    try:
        microfonos = sr.Microphone.list_microphone_names()
        for i, nombre in enumerate(microfonos):
            print(f"  [{i}] {nombre}")
        return microfonos
    except Exception as e:
        logger.error("voice", f"Error listando micrófonos: {e}")
        return []


def agregar_wake_word(palabra):
    """Agrega variante de wake word en tiempo de ejecución."""
    WAKE_WORDS.add(normalizar_texto(palabra))
    logger.info("voice", f"Wake word agregada: '{palabra}'")


def obtener_wake_words():
    """Retorna las wake words activas."""
    return list(WAKE_WORDS)


def detener_voz():
    """Detiene la reproducción activa."""
    global _hablando
    _hablando = False