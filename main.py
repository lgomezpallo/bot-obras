import os
import sqlite3 # Importamos el módulo SQLite
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
DATABASE_NAME = 'obras.db' # Nombre del archivo de la base de datos SQLite

def get_db_connection():
    """Establece y retorna una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Para acceder a las columnas por nombre
    return conn

def init_db():
    """Inicializa la base de datos, creando la tabla 'obras' si no existe."""
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
            id_elemento TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# ==========================
# BASE DE DATOS TEMPORAL (ahora no la usaremos directamente)
# ==========================
# OBRAS = []   # Ya no la usaremos directamente, ahora los datos van a SQLite

# ==========================
#      ESTADOS GLOBALES
# ==========================
AGREGAR_PRESUPUESTO = "AGREGAR_PRESUPUESTO"
AGREGAR_CALLE = "AGREGAR_CALLE"
AGREGAR_ALTURA = "AGREGAR_ALTURA"
AGREGAR_ESQUINA = "AGREGAR_ESQUINA"
AGREGAR_ELEMENTO = "AGREGAR_ELEMENTO"
AGREGAR_ID_ELEMENTO = "AGREGAR_ID_ELEMENTO"
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
        [InlineKeyboardButton("Caño", callback_data="ELEM_CAÑO")],
        [InlineKeyboardButton("Cámara", callback_data="ELEM_CAMARA")],
        [InlineKeyboardButton("Sumidero", callback_data="ELEM_SUMIDERO")],
    ]
    await update.message.reply_text("Seleccioná el elemento:", reply_markup=InlineKeyboardMarkup(keyboard))
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    elemento = query.data.replace("ELEM_", "")
    context.user_data["nueva_obra"]["elemento"] = elemento

    await query.edit_message_text("Ingresá el ID del elemento:")
    return AGREGAR_ID_ELEMENTO

async def agregar_id_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nueva_obra"]["id_elemento"] = update.message.text.strip()

    obra = context.user_data["nueva_obra"]

    texto = (
        f"**CONFIRMAR OBRA**\n\n"
        f"Presupuesto: {obra['presupuesto']}\n"
        f"Calle: {obra['calle']}\n"
        f"Altura: {obra['altura']}\n"
        f"Esquina: {obra['esquina']}\n"
        f"Elemento: {obra['elemento']}\n"
        f"ID Elemento: {obra['id_elemento']}\n"
    )

    keyboard = [
        [InlineKeyboardButton("Confirmar", callback_data="CONFIRMAR_OBRA")],
        [InlineKeyboardButton("Cancelar", callback_data="CANCEL")],
    ]

    await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return AGREGAR_CONFIRMAR

async def agregar_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    obra_a_guardar = context.user_data["nueva_obra"]

    # ======= MODIFICACIÓN AQUÍ: GUARDAR EN SQLite =======
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO obras (presupuesto, calle, altura, esquina, elemento, id_elemento) VALUES (?, ?, ?, ?, ?, ?)",
            (
                obra_a_guardar["presupuesto"],
                obra_a_guardar["calle"],
                obra_a_guardar["altura"],
                obra_a_guardar["esquina"],
                obra_a_guardar["elemento"],
                obra_a_guardar["id_elemento"],
            ),
        )
        conn.commit()
        await query.edit_message_text("Obra agregada correctamente a la base de datos.")
    except Exception as e:
        conn.rollback() # En caso de error, deshacemos la transacción
        await query.edit_message_text(f"Hubo un error al guardar la obra: {e}")
    finally:
        conn.close()
    # ====================================================

    context.user_data["nueva_obra"] = {} # Limpiamos los datos temporales

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

    # ======= NUEVO AQUÍ: LECTURA DESDE SQLite =======
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT presupuesto, calle, altura, esquina, elemento, id_elemento FROM obras")
    obras_db = cursor.fetchall() # Obtenemos todas las obras
    conn.close()

    if not obras_db:
        mensaje = "No hay obras registradas aún."
    else:
        mensaje = "**Listado de Obras:**\n\n"
        for i, obra in enumerate(obras_db):
            # Accedemos a los campos por nombre gracias a conn.row_factory = sqlite3.Row
            mensaje += f"**Obra {i+1}:**\n"
            mensaje += f"  Presupuesto: {obra['presupuesto']}\n"
            mensaje += f"  Calle: {obra['calle']}\n"
            mensaje += f"  Altura: {obra['altura']}\n"
            mensaje += f"  Esquina: {obra['esquina']}\n"
            mensaje += f"  Elemento: {obra['elemento']}\n"
            mensaje += f"  ID Elemento: {obra['id_elemento']}\n\n"
    # ====================================================

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
    init_db() # ======= NUEVO: Inicializamos la base de datos al iniciar el bot =======
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
            AGREGAR_ID_ELEMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_id_elemento)],
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
    app.add_handler(CallbackQueryHandler(modificar_start, pattern="^MODIFICAR$"))

    print("Bot iniciado…")
    app.run_polling()
