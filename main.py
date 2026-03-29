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
    if 'descripcion_estado' not in columns:
        cursor.execute("ALTER TABLE obras ADD COLUMN descripcion_estado TEXT;")

    conn.commit()
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
    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    await update.message.reply_text("¡Hola! ¿Qué quieres hacer hoy?", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vuelve al menú principal desde cualquier otro punto de la conversación."""
    query = update.callback_query
    await query.answer() # Siempre responder a la callback_query

    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    await query.edit_message_text("Menú Principal", reply_markup=InlineKeyboardMarkup(keyboard))

# ==========================
# MANEJADORES PARA AGREGAR OBRA
# ==========================
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el proceso de agregar una nueva obra."""
    query = update.callback_query
    await query.answer()

    context.user_data["nueva_obra"] = {} # Inicializa un diccionario vacío para la nueva obra
    await query.edit_message_text("Ingresá el presupuesto (solo números enteros):")
    return AGREGAR_PRESUPUESTO

async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y valida el presupuesto de la obra."""
    texto = update.message.text.strip()
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
    await update.message.reply_text("Ingresá la altura (solo números enteros):")
    return AGREGAR_ALTURA

async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y valida la altura de la obra."""
    texto = update.message.text.strip()
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

    keyboard = [
        [InlineKeyboardButton("Sumidero", callback_data="ELEM_Sumidero")],
        [InlineKeyboardButton("Cámara intermedia", callback_data="ELEM_Cámara intermedia")],
        [InlineKeyboardButton("Canaleta", callback_data="ELEM_Canaleta")],
        [InlineKeyboardButton("Boca de registro", callback_data="ELEM_Boca de registro")],
        [InlineKeyboardButton("Conducto", callback_data="ELEM_Conducto")],
        [InlineKeyboardButton("Otro", callback_data="ELEM_OTRO")], # Opción para texto libre
    ]
    await update.message.reply_text("Seleccioná el elemento:", reply_markup=InlineKeyboardMarkup(keyboard))
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la selección del tipo de elemento de la obra."""
    query = update.callback_query
    await query.answer()

    elemento_seleccionado = query.data.replace("ELEM_", "")

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
        return AGREGAR_OTRO_ELEMENTO # Se queda en este estado si la entrada es vacía

    context.user_data["nueva_obra"]["elemento"] = texto_libre_elemento
    await update.message.reply_text("Ingresá el ID del elemento:")
    return AGREGAR_ID_ELEMENTO

async def agregar_id_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el ID del elemento y pide la selección del estado de la obra."""
    context.user_data["nueva_obra"]["id_elemento"] = update.message.text.strip()

    keyboard = [
        [InlineKeyboardButton("Pendiente", callback_data="ESTADO_Pendiente")],
        [InlineKeyboardButton("En Ejecución", callback_data="ESTADO_En Ejecucion")],
        [InlineKeyboardButton("Finalizada", callback_data="ESTADO_Finalizada")],
        [InlineKeyboardButton("Pausada", callback_data="ESTADO_Pausada")],
        [InlineKeyboardButton("Otro", callback_data="ESTADO_OTRO")], # Opción para estado libre
    ]
    await update.message.reply_text("Seleccioná el estado de la obra:", reply_markup=InlineKeyboardMarkup(keyboard))
    return AGREGAR_ESTADO

async def agregar_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la selección del estado de la obra."""
    query = update.callback_query
    await query.answer()

    estado_seleccionado = query.data.replace("ESTADO_", "")

    if estado_seleccionado == "OTRO":
        await query.edit_message_text("Ingresá el nombre del estado (texto libre):")
        return AGREGAR_OTRO_ESTADO # Pasa a un estado para recibir el nombre del estado libre
    elif estado_seleccionado == "Pausada":
        context.user_data["nueva_obra"]["estado"] = estado_seleccionado
        await query.edit_message_text(f"Ingresá una descripción para el motivo de '{estado_seleccionado}':")
        return AGREGAR_DESCRIPCION_ESTADO # Pasa a un estado para recibir la descripción de la pausa
    else: # Para Pendiente, En Ejecución, Finalizada
        context.user_data["nueva_obra"]["estado"] = estado_seleccionado
        context.user_data["nueva_obra"]["descripcion_estado"] = None # No hay descripción para estos estados
        return await _confirmar_obra_message(update, context, query)

async def agregar_otro_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre de un estado personalizado (texto libre)."""
    texto_libre_estado = update.message.text.strip()
    if not texto_libre_estado:
        await update.message.reply_text("No ingresaste ningún nombre para el estado. Por favor, intentá de nuevo:")
        return AGREGAR_OTRO_ESTADO # Se queda en este estado si la entrada es vacía

    context.user_data["nueva_obra"]["estado"] = texto_libre_estado
    context.user_data["nueva_obra"]["descripcion_estado"] = None # Los estados personalizados no tienen descripción adicional en este flujo
    return await _confirmar_obra_message(update, context)

async def agregar_descripcion_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la descripción para el estado 'Pausada'."""
    descripcion_estado = update.message.text.strip()
    if not descripcion_estado:
        await update.message.reply_text("No ingresaste una descripción. Por favor, intentá de nuevo:")
        return AGREGAR_DESCR
