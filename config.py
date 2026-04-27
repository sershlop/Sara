# 📁 config.py - Panel de configuración central de SARA

# ──────────────────────────────────────────────
# 🔹 SISTEMA
# ──────────────────────────────────────────────
VERSION           = "0.1.0"
MOSTRAR_CONFIANZA = True 

# ──────────────────────────────────────────────
# 🔹 BASE DE DATOS
# ──────────────────────────────────────────────
DB_NAME = "sara.db"

# ──────────────────────────────────────────────
# 🔹 EMBEDDINGS
# ──────────────────────────────────────────────
MODELO_EMBEDDINGS = "API key aqui "

# ──────────────────────────────────────────────
# 🔹 UMBRALES DE DECISIÓN
# ──────────────────────────────────────────────
UMBRAL_PREGUNTA  = 0.65 
UMBRAL_COMANDO   = 0.70 
UMBRAL_INTENCION = 0.55 
UMBRAL_DUPLICADO = 0.85 
UMBRAL_SEMANTICO = 0.75 
UMBRAL_FUSION    = 0.30 

# ──────────────────────────────────────────────
# 🔹 PESOS DE SCORING
# ──────────────────────────────────────────────
PESO_DIFFLIB   = 0.30 
PESO_BD        = 0.25 
PESO_SEMANTICO = 0.45 


# ──────────────────────────────────────────────
# 🔹 RESPALDO INTELIGENTE
# ──────────────────────────────────────────────

# Activar respaldo con fuentes externas
USAR_RESPALDO_EXTERNO  = False

# Umbral mínimo de confianza para activar respaldo
# Si SARA tiene confianza menor a este valor → busca externamente
UMBRAL_MINIMO_RESPALDO = 0.40

# Guardar automáticamente en BD lo que encuentre el respaldo
# True → SARA aprende de cada búsqueda externa
GUARDAR_RESPALDO_AUTO  = True


# ──────────────────────────────────────────────
# 🔹 BÚSQUEDA Y MOCK (Esencial para Searcher.py)
# ──────────────────────────────────────────────
BUSQUEDA_EXTERNA_ACTIVA = False 
MODO_MOCK               = True  
TIMEOUT_EXTERNO         = 8     

# ──────────────────────────────────────────────
# 🔹 RESPALDO INTELIGENTE 
# ──────────────────────────────────────────────
USAR_GEMINI_BACKUP   = True
UMBRAL_MINIMO_GEMINI = 0.40  # Antes UMBRAL_MINIMO_GROK

# ──────────────────────────────────────────────
# 🔹 BÚSQUEDA Y MOCK (Esencial para Searcher.py)
# ──────────────────────────────────────────────
BUSQUEDA_EXTERNA_ACTIVA = False 
MODO_MOCK               = True  
TIMEOUT_EXTERNO         = 8     

# ──────────────────────────────────────────────
# 🔹 INTERACCIÓN Y LOGGER
# ──────────────────────────────────────────────
MAX_PALABRAS_CORTAS = 3 
NIVEL_CONSOLA       = "DEBUG" 
NIVEL_BD            = "INFO"

# ──────────────────────────────────────────────
# 🔹 VOZ (Configuración de Audio)
# ──────────────────────────────────────────────
MODO_VOZ        = False 
WAKE_WORD       = "sara" 
TIMEOUT_ESCUCHA = 5 
UMBRAL_ENERGIA  = 300 
VELOCIDAD_VOZ   = 150 
VOLUMEN_VOZ     = 1.0 
IDIOMA_VOZ      = "es-MX"