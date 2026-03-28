import os
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
# BASE DE DATOS TEMPORAL
# ==========================
OBRAS = []   # Luego lo reemplazamos por una base real

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

    await query.edit_message_text("Ingresá el presupuesto:")
    return AGREGAR_PRESUPUESTO


async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    context.user_data["nueva_obra"]["presupuesto"] = texto

    await update.message.reply_text("Ingresá la calle:")
    return AGREGAR_CALLE


async def agregar_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nueva_obra"]["calle"] = update.message.text.strip()

    await update.message.reply_text("Ingresá la altura:")
    return AGREGAR_ALTURA


async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nueva_obra"]["altura"] = update.message.text.strip()

    await update.message.reply_text("Ingresá la esquina:")
    return AGREGAR_ESQUINA


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

    OBRAS.append(context.user_data["nueva_obra"])
    context.user_data["nueva_obra"] = {}

    await query.edit_message_text("Obra agregada correctamente.")

    return ConversationHandler.END


async def cancelar(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Operación cancelada.")
    return ConversationHandler.END


# ==========================
#   PLACEHOLDERS RESTO
# ==========================
async def ver_obras(update, context):
    await update.callback_query.edit_message_text("Ver obras (placeholder).")

async def editar_start(update, context):
    await update.callback_query.edit_message_text("Editar obra (placeholder).")

async def eliminar_start(update, context):
    await update.callback_query.edit_message_text("Eliminar obra (placeholder).")

async def modificar_start(update, context):
    await update.callback_query.edit_message_text("Modificar estado (placeholder).")


# ==========================
#          RUN
# ==========================
if __name__ == "__main__":
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
