import os
import sqlite3
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
import logging # Importar el módulo de logging

# ==========================
# CONFIGURACIÓN DE LOGGING
# ==========================
# Configurar logging básico para ver mensajes en consola (útil para depuración)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================
# BASE DE DATOS - CONFIGURACION
# ==========================
DATABASE_NAME = 'obras.db'

def get_db_connection():
    """Establece y retorna una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Para acceder a las columnas por nombre (como si fuera un diccionario)
    return conn

def init_db():
    """
    Inicializa la base de datos, creando la tabla 'obras' si no existe.
    Si ya existe y faltan columnas, las añade (útil para actualizaciones).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Creamos la tabla principal si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS obras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Verificamos si las columnas 'estado' y 'descripcion_estado' existen
    # Esto es para que no tengas que borrar obras.db si ya lo tenías creado
    cursor.execute("PRAGMA table_info(obras);")
    columns = [info[1] for info in cursor.fetchall()]

    if 'estado' not in columns:
        cursor.execute("ALTER TABLE obras ADD COLUMN estado TEXT DEFAULT 'Pendiente';")
        logger.info("Columna 'estado' añadida a la tabla 'obras'.")
    if 'descripcion_estado' not in columns:
        cursor.execute("ALTER TABLE obras ADD COLUMN descripcion_estado TEXT;")
        logger.info("Columna 'descripcion_estado' añadida a la tabla 'obras'.")

    conn.commit()
    conn.close()
    logger.info("Base de datos inicializada correctamente.")

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
    """Recibe y valida el
