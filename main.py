import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# --- Configuración DB ---
DATABASE_URL = os.environ.get("DATABASE_URL")
def get_connection():
    return psycopg2.connect(DATABASE_URL)

# --- Estados ConversationHandler ---
(
    AGREGAR_PRESUPUESTO, AGREGAR_CALLE, AGREGAR_ALTURA, AGREGAR_ESQUINA, AGREGAR_ELEMENTO,
    VER_FILTRO,
    EDITAR_SELECCION, EDITAR_CAMPO, EDITAR_VALOR,
    ELIMINAR_SELECCION, ELIMINAR_CONFIRMAR,
    MODIFICAR_SELECCION, MODIFICAR_ESTADO, MODIFICAR_MOTIVO
) = range(14)

# --- Cancelar ---
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    await update.effective_message.reply_text("❌ Acción cancelada. Volviendo al menú principal.")
    await start(update, context)
    return ConversationHandler.END

# --- Inicio ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Agregar", callback_data="AGREGAR"),
         InlineKeyboardButton("Ver", callback_data="VER")],
        [InlineKeyboardButton("Editar", callback_data="EDITAR"),
         InlineKeyboardButton("Eliminar", callback_data="ELIMINAR")],
        [InlineKeyboardButton("Modificar Estado", callback_data="MODIFICAR")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Bienvenido! Elegí una opción:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.effective_message.reply_text(
            "Bienvenido! Elegí una opción:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# --- AGREGAR OBRA ---
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    await update.effective_message.reply_text("Ingrese número de Presupuesto (o Cancelar):")
    return AGREGAR_PRESUPUESTO

async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar": return await cancelar(update, context)
    context.user_data['presupuesto'] = text
    await update.message.reply_text("Ingrese la Calle (o Omitir / Cancelar):")
    return AGREGAR_CALLE

async def agregar_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar
