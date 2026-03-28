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
#      ESTADOS GLOBALES
# ==========================
AGREGAR_PRESUPUESTO = "AGREGAR_PRESUPUESTO"
AGREGAR_CALLE = "AGREGAR_CALLE"
AGREGAR_ALTURA = "AGREGAR_ALTURA"
AGREGAR_ESQUINA = "AGREGAR_ESQUINA"
AGREGAR_ELEMENTO = "AGREGAR_ELEMENTO"
AGREGAR_ID_ELEMENTO = "AGREGAR_ID_ELEMENTO"

EDITAR_SELECCION = "EDITAR_SELECCION"
EDITAR_CAMPO = "EDITAR_CAMPO"
EDITAR_GUARDAR = "EDITAR_GUARDAR"

ELIMINAR_SELECCION = "ELIMINAR_SELECCION"
CONFIRMAR_ELIMINAR = "CONFIRMAR_ELIMINAR"

MODIFICAR_ESTADO_SELECCION = "MODIFICAR_ESTADO_SELECCION"
SELECCION_ESTADO = "SELECCION_ESTADO"
INGRESAR_MOTIVO = "INGRESAR_MOTIVO"


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
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Menú Principal", reply_markup=reply_markup)


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
#   PLACEHOLDERS (vacíos)
# ==========================
# Los llenamos luego con tu lógica real.

async def agregar_start(update, context): 
    await update.callback_query.edit_message_text("Agregar obra (placeholder).")
    return AGREGAR_PRESUPUESTO

async def ver_obras(update, context):
    await update.callback_query.edit_message_text("Ver obras (placeholder).")

async def editar_start(update, context):
    await update.callback_query.edit_message_text("Editar obra (placeholder).")
    return EDITAR_SELECCION

async def eliminar_start(update, context):
    await update.callback_query.edit_message_text("Eliminar obra (placeholder).")
    return ELIMINAR_SELECCION

async def modificar_start(update, context):
    await update.callback_query.edit_message_text("Modificar estado (placeholder).")
    return MODIFICAR_ESTADO_SELECCION

async def cancelar(update, context):
    await update.callback_query.edit_message_text("Operación cancelada.")
    return ConversationHandler.END


# ==========================
#      RUN DEL BOT
# ==========================
if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ["TOKEN"]).build()

    # MENÚ PRINCIPAL
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern="^PRINCIPAL$"))

    # AGREGAR
    conv_agregar = ConversationHandler(
        entry_points=[CallbackQueryHandler(agregar_start, pattern="^AGREGAR$")],
        states={
            AGREGAR_PRESUPUESTO: [MessageHandler(filters.TEXT, lambda u, c: None)],
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="^CANCEL$")],
    )
    app.add_handler(conv_agregar)

    # VER
    app.add_handler(CallbackQueryHandler(ver_obras, pattern="^VER$"))

    # EDITAR
    conv_editar = ConversationHandler(
        entry_points=[CallbackQueryHandler(editar_start, pattern="^EDITAR$")],
        states={EDITAR_SELECCION: [CallbackQueryHandler(lambda u, c: None)]},
        fallbacks=[CallbackQueryHandler(cancelar, pattern="^CANCEL$")],
    )
    app.add_handler(conv_editar)

    # ELIMINAR
    conv_eliminar = ConversationHandler(
        entry_points=[CallbackQueryHandler(eliminar_start, pattern="^ELIMINAR$")],
        states={ELIMINAR_SELECCION: [CallbackQueryHandler(lambda u, c: None)]},
        fallbacks=[CallbackQueryHandler(cancelar, pattern="^CANCEL$")],
    )
    app.add_handler(conv_eliminar)

    # MODIFICAR ESTADO
    conv_estado = ConversationHandler(
        entry_points=[CallbackQueryHandler(modificar_start, pattern="^MODIFICAR$")],
        states={MODIFICAR_ESTADO_SELECCION: [CallbackQueryHandler(lambda u, c: None)]},
        fallbacks=[CallbackQueryHandler(cancelar, pattern="^CANCEL$")],
    )
    app.add_handler(conv_estado)

    print("Bot iniciado en Railway…")
    app.run_polling()
