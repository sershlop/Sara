# 📁 io_manager.py
# Módulo de entrada y salida de SARA
# Todo lo que el usuario ve y escribe pasa por aquí
# Si en el futuro se agrega GUI o voz, solo se modifica este archivo

# ──────────────────────────────────────────────
# 🔹 ENTRADA
# ──────────────────────────────────────────────
_modo_voz = False
_voice_module = None
_modo_gui = False
_gui_get_input = None
_gui_show_response = None
_gui_show_prompt = None

def activar_modo_voz(voice_mod):
    """Activa el modo voz con el módulo voice."""
    global _modo_voz, _voice_module
    _modo_voz     = True
    _voice_module = voice_mod
    print("🎤 Modo voz activado. Di 'sara' para activarme.")


def desactivar_modo_voz():
    """Desactiva el modo voz."""
    global _modo_voz, _voice_module
    _modo_voz     = False
    _voice_module = None
    print("⌨️  Modo voz desactivado. Volviendo a modo texto.")


def esta_en_modo_voz():
    """Retorna True si el modo voz está activo."""
    return _modo_voz


def activar_modo_gui(get_input_callback, show_response_callback, show_prompt_callback=None):
    """Activa el modo GUI con callbacks para entrada, salida y prompts."""
    global _modo_gui, _gui_get_input, _gui_show_response, _gui_show_prompt
    _modo_gui = True
    _gui_get_input = get_input_callback
    _gui_show_response = show_response_callback
    _gui_show_prompt = show_prompt_callback
    print("🖥️  Modo GUI activado.")


def esta_en_modo_gui():
    """Retorna True si el modo GUI está activo."""
    return _modo_gui


def show_prompt(question):
    """Muestra un prompt al usuario. En GUI usa callback, en terminal usa input."""
    if _modo_gui and _gui_show_prompt:
        return _gui_show_prompt(question)
    else:
        try:
            return input(question).strip()
        except KeyboardInterrupt:
            return None


def obtener_input():
    if _modo_gui and _gui_get_input:
        return _gui_get_input()
    if _modo_voz and _voice_module:
        primer_ciclo = True
        while True:
            if primer_ciclo:
                print("💤 SARA: En espera... (di 'sara' para activarme)")
                primer_ciclo = False

            # ── NUEVO: desempaquetar tupla ────
            detectado, comando_inline = _voice_module.escuchar_wakeword()

            if detectado:
                # ── CASO 1: Frase unida "sara abre youtube" ──
                if comando_inline:
                    print(f"🗣️  Tú dijiste: 'sara {comando_inline}'")
                    return comando_inline  # ← directo sin segunda escucha

                # ── CASO 2: Solo "sara" → escuchar comando ──
                texto = _voice_module.escuchar_comando()
                if texto:
                    print(f"🗣️  Tú dijiste: '{texto}'")
                    return texto

                print("💤 SARA: En espera...")
                continue

    try:
        texto = input("Tú: ").strip()
        return texto
    except KeyboardInterrupt:
        print("\nSARA: Hasta luego 👋")
        exit(0)
    except EOFError:
        print("\nSARA: Entrada cerrada. Hasta luego.")
        exit(0)


def mostrar_respuesta(texto):
    """
    Muestra respuesta en terminal.
    En modo voz también la habla.
    En modo GUI actualiza la interfaz y también imprime en terminal.
    """
    print(f"SARA: {texto}")

    # En modo voz → hablar también
    if _modo_voz and _voice_module:
        _voice_module.hablar_async(texto)

    # En modo GUI → actualizar interfaz
    if _modo_gui and _gui_show_response:
        _gui_show_response(texto)

def mostrar_error(mensaje):
    """
    Muestra un mensaje de error al usuario.
    """
    print(f"SARA [ERROR]: {mensaje}")


def mostrar_confianza(confianza):
    """
    Muestra el nivel de confianza de SARA en modo debug.
    Solo usar durante desarrollo — desactivar en producción.
    Ejemplo: SARA [confianza: 87.5%]
    """
    porcentaje = round(confianza * 100, 1)
    print(f"SARA [confianza: {porcentaje}%]")


def mostrar_bienvenida():
    """
    Mensaje inicial al arrancar SARA.
    Centralizado aquí para fácil personalización futura.
    """
    print("=" * 40)
    print("  SARA — Sistema Avanzado de Respuesta")
    print("  Escribe 'salir' para cerrar")
    print("=" * 40)


def mostrar_separador():
    """
    Separador visual entre interacciones.
    Opcional — útil para conversaciones largas.
    """
    print("-" * 40)


# ──────────────────────────────────────────────
# 🔹 COMANDOS ESPECIALES DE SALIDA
# ──────────────────────────────────────────────

PALABRAS_SALIDA = {"salir", "exit", "quit", "adios", "chao", "bye"}

def es_comando_salida(texto):
    """
    Retorna True si el usuario quiere cerrar SARA.
    Centralizado aquí para no repetir lógica en sara.py
    Normaliza a minúsculas y quita espacios antes de comparar.
    """
    return texto.strip().lower() in PALABRAS_SALIDA


def mostrar_despedida():
    """
    Mensaje de cierre de SARA.
    """
    print("SARA: Hasta luego 👋")


# ──────────────────────────────────────────────
# 🔹 FLUJO DE APRENDIZAJE INTERACTIVO
# ──────────────────────────────────────────────

def preguntar_si_no(mensaje):
    """
    Hace una pregunta de si/no al usuario.
    Acepta variantes: si/s/yes/y — no/n
    Retorna: True si acepta, False si rechaza
    """
    while True:
        try:
            respuesta = input(f"SARA: {mensaje} (si/no): ").strip().lower()
            if respuesta in ("si", "s", "yes", "y"):
                return True
            elif respuesta in ("no", "n"):
                return False
            else:
                print("SARA: Por favor responde 'si' o 'no'.")
        except KeyboardInterrupt:
            return False

def solicitar_acciones_multiples():
    """
    Guía al usuario para registrar múltiples acciones
    en un comando compuesto.

    Retorna: list[dict] con las acciones, o None si cancela
    """
    try:
        print("\nSARA: ¿Cuántas acciones quieres agregar?")
        print("      (Ejemplo: 3 para abrir VS Code, Chrome y Spotify)")

        try:
            cantidad = int(input("  → Cantidad: ").strip())
        except ValueError:
            print("SARA: Número inválido. Cancelando.")
            return None

        if cantidad <= 0:
            print("SARA: Debe ser al menos 1 acción.")
            return None

        if cantidad > 10:
            print("SARA: Máximo 10 acciones por comando.")
            cantidad = 10

        acciones = []

        for i in range(1, cantidad + 1):
            print(f"\nSARA: Acción {i} de {cantidad}")
            print("─" * 35)

            accion = input(f"  → Acción {i} (URL o ruta): ").strip()
            if not accion or accion.lower() == "cancelar":
                print("SARA: Cancelando registro.")
                return None

            print(f"  → Tipo de acción {i}:")
            print("     [1] web    (URL o página web)")
            print("     [2] app    (aplicación o archivo)")
            print("     [3] sistema (comando de terminal)")

            tipo_opcion = input("  → Elige 1, 2 o 3: ").strip()
            tipos = {"1": "web", "2": "app", "3": "sistema"}
            tipo  = tipos.get(tipo_opcion)

            if not tipo:
                print("SARA: Opción inválida. Usando 'app' por defecto.")
                tipo = "app"

            descripcion = input(f"  → Descripción breve (opcional): ").strip()

            acciones.append({
                "orden":       i,
                "accion":      accion,
                "tipo":        tipo,
                "descripcion": descripcion or accion
            })

            print(f"  ✅ Acción {i} registrada.")

        return acciones if acciones else None

    except KeyboardInterrupt:
        return None
def solicitar_respuesta_nueva():
    """
    Solicita al usuario la respuesta correcta para una pregunta.
    Retorna: str con la respuesta, o None si cancela
    """
    try:
        print("SARA: Escribe la respuesta (o 'cancelar' para omitir):")
        respuesta = show_prompt("  → ")
        if respuesta and respuesta.lower() == "cancelar" or not respuesta:
            return None
        return respuesta
    except KeyboardInterrupt:
        return None


def solicitar_datos_comando():
    """
    Solicita al usuario los datos para registrar un nuevo comando.
    Retorna: dict con los datos, o None si cancela
    """
    try:
        print("SARA: Vamos a registrar el comando.")
        print("      Escribe 'cancelar' en cualquier momento para omitir.\n")

        accion = show_prompt("  → Acción (URL, ruta o comando): ")
        if accion and accion.lower() == "cancelar" or not accion:
            return None

        print("  → Tipo de comando:")
        print("     [1] web    (abrir página)")
        print("     [2] app    (abrir aplicación)")
        print("     [3] sistema (comando de terminal)")
        tipo_opcion = show_prompt("  → Elige 1, 2 o 3: ")

        tipos = {"1": "web", "2": "app", "3": "sistema"}
        tipo  = tipos.get(tipo_opcion)

        if not tipo:
            print("SARA: Opción inválida. Cancelando.")
            return None

        palabras_clave = show_prompt("  → Palabras clave (ej: 'abre chrome, navegar'): ")
        descripcion    = show_prompt("  → Descripción breve (opcional): ")

        return {
            "accion":        accion,
            "tipo":          tipo,
            "palabras_clave": palabras_clave,
            "descripcion":   descripcion
        }

    except KeyboardInterrupt:
        return None