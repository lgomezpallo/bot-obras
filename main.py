import os
import psycopg2
from psycopg2 import sql
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import logging

# ==========================
# CONFIGURACIÓN DE LOGGING
# ==========================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================
# BASE DE DATOS - CONFIGURACION
# ==========================
# URL de conexión a Supabase (PostgreSQL) obtenida de Railway
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    """
    Establece y retorna una conexión a la base de datos PostgreSQL de Supabase
    utilizando la URL de conexión proporcionada en la variable de entorno.
    """
    if not DATABASE_URL:
        logger.error("Error: La variable de entorno 'DATABASE_URL' no está configurada.")
        raise ValueError("DATABASE_URL no configurada.")
    try:
        # psycopg2.connect() ya maneja los parámetros de la URL, incluyendo sslmode.
        # Por ejemplo, la URL de Supabase ya suele incluir?sslmode=require
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos PostgreSQL de Supabase: {e}")
        raise

def init_db():
    """
    Inicializa la base de datos, creando la tabla 'obras' si no existe.
    Si ya existe y faltan columnas, las añade (útil para actualizaciones).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Creamos la tabla principal si no existe.
        # SERIAL PRIMARY KEY es el equivalente de AUTOINCREMENT en PostgreSQL.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS obras (
                id SERIAL PRIMARY KEY,
                presupuesto INTEGER NOT NULL,
                calle TEXT NOT NULL,
                altura INTEGER NOT NULL,
                esquina TEXT,
                elemento TEXT NOT NULL,
                id_elemento TEXT NOT NULL,
                estado TEXT DEFAULT 'Pendiente',
                descripcion_estado TEXT
            )
        ''')

        # Verificamos si las columnas 'estado' y 'descripcion_estado' existen.
        # Usamos information_schema para PostgreSQL.
        cursor.execute(sql.SQL("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'obras'
        """))
        existing_columns = [row[0] for row in cursor.fetchall()]

        if 'estado' not in existing_columns:
            cursor.execute("ALTER TABLE obras ADD COLUMN estado TEXT DEFAULT 'Pendiente';")
            logger.info("Columna 'estado' añadida a la tabla 'obras'.")
        if 'descripcion_estado' not in existing_columns:
            cursor.execute("ALTER TABLE obras ADD COLUMN descripcion_estado TEXT;")
            logger.info("Columna 'descripcion_estado' añadida a la tabla 'obras'.")

        conn.commit()
        logger.info("Base de datos inicializada correctamente.")

    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
        if conn:
            conn.rollback() # Deshace en caso de error
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ==========================
# ESTADOS GLOBALES DE LA CONVERSACIÓN
# ==========================
AGREGAR_PRESUPUESTO = "AGREGAR_PRESUPUESTO"
AGREGAR_CALLE = "AGREGAR_CALLE"
AGREGAR_ALTURA = "AGREGAR_ALTURA"
AGREGAR_ESQUINA = "AGREGAR_ESQUINA"
AGREGAR_ELEMENTO = "AGREGAR_ELEMENTO"
AGREGAR_OTRO_ELEMENTO = "AGREGAR_OTRO_ELEMENTO" # Para el nombre del elemento de texto libre
AGREGAR_ID_ELEMENTO = "AGREGAR_ID_ELEMENTO"
AGREGAR_ESTADO = "AGREGAR_ESTADO" # Para seleccionar el estado de la obra (botón)
AGREGAR_OTRO_ESTADO = "AGREGAR_OTRO_ESTADO" # Para el nombre del estado de texto libre (si se elige 'Otro')
AGREGAR_DESCRIPCION_ESTADO = "AGREGAR_DESCRIPCION_ESTADO" # Para la descripción del estado (si se elige 'Pausada')
AGREGAR_CONFIRMAR = "AGREGAR_CONFIRMAR"

# ==========================
# MANEJADORES DEL MENÚ PRINCIPAL
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú principal al iniciar el bot con /start."""
    logger.info("Comando /start recibido.")
    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("¡Hola! ¿Qué quieres hacer hoy?", reply_markup=reply_markup)
    else: # En caso de que se llame desde otro contexto sin update.message
        logger.warning("start() llamado sin update.message. Posiblemente un caso de uso no previsto.")
        # Podrías querer enviar un mensaje a un chat predefinido o hacer algo diferente
        await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Hola! ¿Qué quieres hacer hoy?", reply_markup=reply_markup)

async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vuelve al menú principal desde cualquier otro punto de la conversación."""
    query = update.callback_query
    await query.answer() # Siempre responder a la callback_query
    logger.info(f"Volviendo al menú principal por {query.data}.")

    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Menú Principal", reply_markup=reply_markup)

# ==========================
# MANEJADORES PARA AGREGAR OBRA
# ==========================
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el proceso de agregar una nueva obra."""
    query = update.callback_query
    await query.answer()
    logger.info("Iniciando flujo de agregar obra.")

    context.user_data["nueva_obra"] = {} # Inicializa un diccionario vacío para la nueva obra
    await query.edit_message_text("Ingresá el presupuesto (solo números enteros):")
    return AGREGAR_PRESUPUESTO

async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y valida el presupuesto de la obra."""
    texto = update.message.text.strip()
    logger.info(f"Recibido presupuesto: {texto}")
    try:
        presupuesto = int(texto)
        context.user_data["nueva_obra"]["presupuesto"] = presupuesto
        await update.message.reply_text("Ingresá la calle:")
        return AGREGAR_CALLE
    except ValueError:
        await update.message.reply_text("¡Eso no parece un número entero! Por favor, ingresa el presupuesto solo con números enteros:")
        return AGREGAR_PRESUPUESTO

async def agregar_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la calle de la obra."""
    context.user_data["nueva_obra"]["calle"] = update.message.text.strip()
    logger.info(f"Recibido calle: {context.user_data['nueva_obra']['calle']}")
    await update.message.reply_text("Ingresá la altura (solo números enteros):")
    return AGREGAR_ALTURA

async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y valida la altura de la obra."""
    texto = update.message.text.strip()
    logger.info(f"Recibido altura: {texto}")
    try:
        altura = int(texto)
        context.user_data["nueva_obra"]["altura"] = altura
        await update.message.reply_text("Ingresá la esquina:")
        return AGREGAR_ESQUINA
    except ValueError:
        await update.message.reply_text("¡Eso no parece un número entero! Por favor, ingresa la altura solo con números enteros:")
        return AGREGAR_ALTURA

async def agregar_esquina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la esquina de la obra y pide la selección del elemento."""
    context.user_data["nueva_obra"]["esquina"] = update.message.text.strip()
    logger.info(f"Recibido esquina: {context.user_data['nueva_obra']['esquina']}")

    keyboard = [
        [InlineKeyboardButton("Sumidero", callback_data="ELEM_Sumidero")],
        [InlineKeyboardButton("Cámara intermedia", callback_data="ELEM_Cámara intermedia")],
        [InlineKeyboardButton("Canaleta", callback_data="ELEM_Canaleta")],
        [InlineKeyboardButton("Boca de registro", callback_data="ELEM_Boca de registro")],
        [InlineKeyboardButton("Conducto", callback_data="ELEM_Conducto")],
        [InlineKeyboardButton("Otro", callback_data="ELEM_OTRO")], # Opción para texto libre
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Seleccioná el elemento:", reply_markup=reply_markup)
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la selección del tipo de elemento de la obra."""
    query = update.callback_query
    await query.answer()
    elemento_seleccionado = query.data.replace("ELEM_", "")
    logger.info(f"Elemento seleccionado: {elemento_seleccionado}")

    if elemento_seleccionado == "OTRO":
        await query.edit_message_text("Ingresá el nombre del elemento (texto libre):")
        return AGREGAR_OTRO_ELEMENTO # Pasa a un estado para recibir el texto libre
    else:
        context.user_data["nueva_obra"]["elemento"] = elemento_seleccionado
        await query.edit_message_text("Ingresá el ID del elemento:")
        return AGREGAR_ID_ELEMENTO

async def agregar_otro_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre de un elemento personalizado (texto libre)."""
    texto_libre_elemento = update.message.text.strip()
    if not texto_libre_elemento:
        await update.message.reply_text("No ingresaste ningún nombre para el elemento. Por favor, intentá de nuevo:")
        return AGREGAR_OTRO_ELEMENTO # Se queda en este estado si la entrada es
