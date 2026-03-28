from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters, CallbackQueryHandler
)
import os
import psycopg2

# Variables de entorno
TOKEN = os.environ.get("TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not TOKEN or not DATABASE_URL:
    raise ValueError("No se encontró TOKEN o DATABASE_URL")

# Conexión a la DB
def get_connection():
    return psycopg2.connect(DATABASE_URL)

# Crear tabla presupuestos si no existe
def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS presupuestos (
            id SERIAL PRIMARY KEY,
            presupuesto TEXT,
            calle TEXT,
            altura TEXT,
            esquina TEXT,
            elemento TEXT,
            estado TEXT DEFAULT 'Pendiente'
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# Estados del ConversationHandler
PRESUPUESTO, CALLE, ALTURA, ESQUINA, ELEMENTO, ELEMENTO_OTRO = range(6)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot Presupuestos ✅\nComandos disponibles:\n/agregar_obra"
    )

# Inicia flujo agregar obra
async def agregar_obra_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Número de Presupuesto:")
    return PRESUPUESTO

async def agregar_obra_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['presupuesto'] = update.message.text
    await update.message.reply_text("Calle:")
    return CALLE

async def agregar_obra_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['calle'] = update.message.text
    await update.message.reply_text("Altura:")
    return ALTURA

async def agregar_obra_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['altura'] = update.message.text
    await update.message.reply_text("Esquina:")
    return ESQUINA

async def agregar_obra_esquina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['esquina'] = update.message.text
    # Botones para Elemento
    keyboard = [
        [InlineKeyboardButton("Sumidero", callback_data="Sumidero"),
         InlineKeyboardButton("BR", callback_data="BR")],
        [InlineKeyboardButton("C.I.", callback_data="CI"),
         InlineKeyboardButton("Otro", callback_data="Otro")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Seleccioná el Elemento:", reply_markup=reply_markup)
    return ELEMENTO

# Handler para botones Elemento
async def agregar_obra_elemento_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    elemento = query.data
    if elemento == "Otro":
        await query.edit_message_text("Escribí el elemento manualmente:")
        return ELEMENTO_OTRO
    context.user_data['elemento'] = elemento
    # Guardar en DB
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO presupuestos (presupuesto, calle, altura, esquina, elemento)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        context.user_data['presupuesto'],
        context.user_data['calle'],
        context.user_data['altura'],
        context.user_data['esquina'],
        context.user_data['elemento']
    ))
    conn.commit()
    cur.close()
    conn.close()
    await query.edit_message_text(f"Presupuesto agregado ✅ Elemento: {context.user_data['elemento']} Estado: Pendiente")
    return ConversationHandler.END

# Handler si escribe manualmente Elemento (Otro)
async def agregar_obra_elemento_otro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['elemento'] = update.message.text
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO presupuestos (presupuesto, calle, altura, esquina, elemento)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        context.user_data['presupuesto'],
        context.user_data['calle'],
        context.user_data['altura'],
        context.user_data['esquina'],
        context.user_data['elemento']
    ))
    conn.commit()
    cur.close()
    conn.close()
    await update.message.reply_text(f"Presupuesto agregado ✅ Elemento: {context.user_data['elemento']} Estado: Pendiente")
    return ConversationHandler.END

# Cancelar
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada ❌")
    return ConversationHandler.END

# Construimos la app
app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('agregar_obra', agregar_obra_start)],
    states={
        PRESUPUESTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_presupuesto)],
        CALLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_calle)],
        ALTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_altura)],
        ESQUINA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_esquina)],
        ELEMENTO_OTRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_elemento_otro)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(agregar_obra_elemento_callback, pattern="^(Sumidero|BR|CI|Otro)$"))

if __name__ == "__main__":
    print("Bot Presupuestos iniciado")
    app.run_polling()
