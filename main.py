import os
import psycopg2
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

def conectar():
    return psycopg2.connect(DATABASE_URL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        ["Agregar obra", "Ver obras"],
        ["Editar obra", "Eliminar obra"],
        ["Cambiar estado"]
    ]
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True)

    await update.message.reply_text("Bienvenido, elegí una opción:", reply_markup=reply_markup)

async def ver_obras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT o.id, o.presupuesto_numero, o.calle, o.altura, o.estado
        FROM obras o
        ORDER BY o.id DESC
        LIMIT 10;
    """)

    filas = cur.fetchall()

    if not filas:
        texto = "No hay obras cargadas."
    else:
        texto = ""
        for f in filas:
            texto += f"ID: {f[0]} | Presupuesto: {f[1]} | {f[2]} {f[3]} | Estado: {f[4]}\n"

    await update.message.reply_text(texto)

    cur.close()
    conn.close()

async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text

    if texto == "Ver obras":
        await ver_obras(update, context)
    else:
        await update.message.reply_text("Opción en construcción")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_texto))

app.run_polling()
