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
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa la base de datos, creando la tabla 'obras' y añadiendo nuevas columnas si no existen."""
    conn = get_db_connection()
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

# ==========================
#      ESTADOS GLOBALES
# ==========================
AGREGAR_PRESUPUESTO = "AGREGAR_PRESUPUESTO"
AGREGAR_CALLE = "AGREGAR_CALLE"
AGREGAR_ALTURA = "AGREGAR_ALTURA"
AGREGAR_ESQUINA = "AGREGAR_ESQUINA"
AGREGAR_ELEMENTO = "AGREGAR_ELEMENTO"
AGREGAR_OTRO_ELEMENTO = "AGREGAR_OTRO_ELEMENTO"
AGREGAR_ID_ELEMENTO = "AGREGAR_ID_ELEMENTO"
AGREGAR_ESTADO = "AGREGAR_ESTADO"
AGREGAR_OTRO_ESTADO = "AGREGAR_OTRO_ESTADO" # NUEVO ESTADO: para ingresar el nombre del estado "Otro"
AGREGAR_DESCRIPCION_ESTADO = "AGREGAR_DESCRIPCION_ESTADO" # Este sigue siendo para la descripción de "Pausada"
AGREGAR_CONFIRMAR = "AGREGAR_CONFIRMAR"

# ==========================
#   MENÚ PRINCIPAL
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    await update.message.reply_text("Menú Principal", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    await query.edit_message_text("Menú Principal", reply_markup=InlineKeyboardMarkup(keyboard))

# ==========================
#   AGREGAR OBRA - PASO 1
# ==========================
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["nueva_obra"] = {}

    await query.edit_message_text("Ingresá el presupuesto (solo números enteros):")
    return AGREGAR_PRESUPUESTO

async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    context.user_data["nueva_obra"]["calle"] = update.message.text.strip()

    await update.message.reply_text("Ingresá la altura (solo números enteros):")
    return AGREGAR_ALTURA

async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    context.user_data["nueva_obra"]["esquina"] = update.message.text.strip()

    keyboard = [
        [InlineKeyboardButton("Sumidero", callback_data="ELEM_Sumidero")],
        [InlineKeyboardButton("Cámara intermedia", callback_data="ELEM_Cámara intermedia")],
        [InlineKeyboardButton("Canaleta", callback_data="ELEM_Canaleta")],
        [InlineKeyboardButton("Boca de registro", callback_data="ELEM_Boca de registro")],
        [InlineKeyboardButton("Conducto", callback_data="ELEM_Conducto")],
        [InlineKeyboardButton("Otro", callback_data="ELEM_OTRO")],
    ]
    await update.message.reply_text("Seleccioná el elemento:", reply_markup=InlineKeyboardMarkup(keyboard))
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    elemento_seleccionado = query.data.replace("ELEM_", "")

    if elemento_seleccionado == "OTRO":
        await query.edit_message_text("Ingresá el nombre del elemento (texto libre):")
        return AGREGAR_OTRO_ELEMENTO
    else:
        context.user_data["nueva_obra"]["elemento"] = elemento_seleccionado
        await query.edit_message_text("Ingresá el ID del elemento:")
        return AGREGAR_ID_ELEMENTO

async def agregar_otro_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_libre_elemento = update.message.text.strip()
    if not texto_libre_elemento:
        await update.message.reply_text("No ingresaste ningún nombre para el elemento. Por favor, intentá de nuevo:")
        return AGREGAR_OTRO_ELEMENTO

    context.user_data["nueva_obra"]["elemento"] = texto_libre_elemento
    await update.message.reply_text("Ingresá el ID del elemento:")
    return AGREGAR_ID_ELEMENTO

async def agregar_id_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    query = update.callback_query
    await query.answer()

    estado_seleccionado = query.data.replace("ESTADO_", "")

    if estado_seleccionado == "OTRO": # Si selecciona "Otro", pide el nombre del estado
        await query.edit_message_text("Ingresá el nombre del estado (texto libre):")
        return AGREGAR_OTRO_ESTADO # Va al nuevo estado para el nombre del estado "Otro"
    elif estado_seleccionado == "Pausada": # Si selecciona "Pausada", pide la descripción
        context.user_data["nueva_obra"]["estado"] = estado_seleccionado
        await query.edit_message_text(f"Ingresá una descripción para el estado '{estado_seleccionado}':")
        return AGREGAR_DESCRIPCION_ESTADO
    else: # Para Pendiente, En Ejecución, Finalizada
        context.user_data["nueva_obra"]["estado"] = estado_seleccionado
        context.user_data["nueva_obra"]["descripcion_estado"] = None
        return await _confirmar_obra_message(update, context, query)

# NUEVA FUNCIÓN: Manejar la entrada de texto libre para el estado "Otro"
async def agregar_otro_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_libre_estado = update.message.text.strip()
    if not texto_libre_estado:
        await update.message.reply_text("No ingresaste ningún nombre para el estado. Por favor, intentá de nuevo:")
        return AGREGAR_OTRO_ESTADO

    context.user_data["nueva_obra"]["estado"] = texto_libre_estado
    context.user_data["nueva_obra"]["descripcion_estado"] = None # No hay descripción para estados personalizados por ahora
    return await _confirmar_obra_message(update, context)

async def agregar_descripcion_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descripcion_estado = update.message.text.strip()
    if not descripcion_estado:
        await update.message.reply_text("No ingresaste una descripción. Por favor, intentá de nuevo:")
        return AGREGAR_DESCRIPCION_ESTADO

    context.user_data["nueva_obra"]["descripcion_estado"] = descripcion_estado
    return await _confirmar_obra_message(update, context)

async def _confirmar_obra_message(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    obra = context.user_data["nueva_obra"]

    texto = (
        f"**CONFIRMAR OBRA**\n\n"
        f"Presupuesto: {obra['presupuesto']}\n"
        f"Calle: {obra['calle']}\n"
        f"Altura: {obra['altura']}\n"
        f"Esquina: {obra['esquina']}\n"
        f"Elemento: {obra['elemento']}\n"
        f"ID Elemento: {obra['id_elemento']}\n"
        f"Estado: {obra.get('estado', 'No definido')}\n"
    )
    if obra.get('descripcion_estado'):
        texto += f"Descripción Estado: {obra['descripcion_estado']}\n"

    keyboard = [
        [InlineKeyboardButton("Confirmar", callback_data="CONFIRMAR_OBRA")],
        [InlineKeyboardButton("Cancelar", callback_data="CANCEL")],
    ]

    if query:
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return AGREGAR_CONFIRMAR

async def agregar_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    obra_a_guardar = context.user_data["nueva_obra"]

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO obras (presupuesto, calle, altura, esquina, elemento, id_elemento, estado, descripcion_estado) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                obra_a_guardar["presupuesto"],
                obra_a_guardar["calle"],
                obra_a_guardar["altura"],
                obra_a_guardar["esquina"],
                obra_a_guardar["elemento"],
                obra_a_guardar["id_elemento"],
                obra_a_guardar.get("estado", "Pendiente"),
                obra_a_guardar.get("descripcion_estado"),
            ),
        )
        conn.commit()
        await query.edit_message_text("Obra agregada correctamente a la base de datos.")
    except Exception as e:
        conn.rollback()
        await query.edit_message_text(f"Hubo un error al guardar la obra: {e}")
    finally:
        conn.close()

    context.user_data["nueva_obra"] = {}

    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    await query.edit_message_text("Menú Principal", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def cancelar(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Operación cancelada. Volviendo al menú principal.")
    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    await query.edit_message_text("Menú Principal", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

# ==========================
#   PLACEHOLDERS RESTO
# ==========================
async def ver_obras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, presupuesto, calle, altura, esquina, elemento, id_elemento, estado, descripcion_estado FROM obras")
    obras_db = cursor.fetchall()
    conn.close()

    if not obras_db:
        mensaje = "No hay obras registradas aún."
    else:
        mensaje = "**Listado de Obras:**\n\n"
        for i, obra in enumerate(obras_db):
            mensaje += f"**Obra {obra['id']}:**\n"
            mensaje += f"  Presupuesto: {obra['presupuesto']}\n"
            mensaje += f"  Calle: {obra['calle']}\n"
            mensaje += f"  Altura: {obra['altura']}\n"
            mensaje += f"  Esquina: {obra['esquina']}\n"
            mensaje += f"  Elemento: {obra['elemento']}\n"
            mensaje += f"  ID Elemento: {obra['id_elemento']}\n"
            mensaje += f"  Estado: {obra['estado']}\n"
            if obra['descripcion_estado']:
                mensaje += f"  Descripción Estado: {obra['descripcion_estado']}\n"
            mensaje += "\n"

    await query.edit_message_text(mensaje, parse_mode="Markdown")
    keyboard = [[InlineKeyboardButton("Volver al Menú Principal", callback_data="PRINCIPAL")]]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def editar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Editar obra (placeholder).")
    keyboard = [[InlineKeyboardButton("Volver al Menú Principal", callback_data="PRINCIPAL")]]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def eliminar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Eliminar obra (placeholder).")
    keyboard = [[InlineKeyboardButton("Volver al Menú Principal", callback_data="PRINCIPAL")]]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def modificar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Modificar estado (placeholder).")
    keyboard = [[InlineKeyboardButton("Volver al Menú Principal", callback_data="PRINCIPAL")]]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

# ==========================
#          RUN
# ==========================
if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(os.environ["TOKEN"]).build()

    # MENÚ PRINCIPAL
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern="^PRINCIPAL$"))

    # AGREGAR OBRA
    conv_agregar = ConversationHandler(
        entry_points=[CallbackQueryHandler(agregar_start, pattern="^AGREGAR$")],
        states={
            AGREGAR_PRESUPUESTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_presupuesto)],
            AGREGAR_CALLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_calle)],
            AGREGAR_ALTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_altura)],
            AGREGAR_ESQUINA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_esquina)],
            AGREGAR_ELEMENTO: [CallbackQueryHandler(agregar_elemento)],
            AGREGAR_OTRO_ELEMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_otro_elemento)],
            AGREGAR_ID_ELEMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_id_elemento)],
            AGREGAR_ESTADO: [CallbackQueryHandler(agregar_estado)],
            AGREGAR_OTRO_ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_otro_estado)], # Manejador para el estado "Otro"
            AGREGAR_DESCRIPCION_ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_descripcion_estado)],
            AGREGAR_CONFIRMAR: [CallbackQueryHandler(agregar_confirmar, pattern="^CONFIRMAR_OBRA$")],
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="^CANCEL$")],
    )
    app.add_handler(conv_agregar)

    # VER
    app.add_handler(CallbackQueryHandler(ver_obras, pattern="^VER$"))

    # EDITAR
    app.add_handler(CallbackQueryHandler(editar_start, pattern="^EDITAR$"))

    # ELIMINAR
    app.add_handler(CallbackQueryHandler(eliminar_start, pattern="^ELIMINAR$"))

    # MODIFICAR ESTADO
    app.add_handler(CallbackQueryHandler(modificar
