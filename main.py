import os
import psycopg2
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL no configurada")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
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
    """)

    conn.commit()
    cur.close()
    conn.close()

# Estados
AGREGAR_PRESUPUESTO, AGREGAR_CALLE, AGREGAR_ALTURA, AGREGAR_ESQUINA, AGREGAR_ELEMENTO, AGREGAR_ID_ELEMENTO, AGREGAR_ESTADO, AGREGAR_CONFIRMAR = range(8)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
    ]
    await update.message.reply_text("Menú:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== AGREGAR =====

async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["obra"] = {}
    await query.message.reply_text("Presupuesto:")
    return AGREGAR_PRESUPUESTO

async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["obra"]["presupuesto"] = int(update.message.text)
        await update.message.reply_text("Calle:")
        return AGREGAR_CALLE
    except:
        await update.message.reply_text("Número inválido")
        return AGREGAR_PRESUPUESTO

async def agregar_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["obra"]["calle"] = update.message.text
    await update.message.reply_text("Altura:")
    return AGREGAR_ALTURA

async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["obra"]["altura"] = int(update.message.text)
        await update.message.reply_text("Esquina:")
        return AGREGAR_ESQUINA
    except:
        await update.message.reply_text("Número inválido")
        return AGREGAR_ALTURA

async def agregar_esquina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["obra"]["esquina"] = update.message.text
    await update.message.reply_text("Elemento:")
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["obra"]["elemento"] = update.message.text
    await update.message.reply_text("ID elemento:")
    return AGREGAR_ID_ELEMENTO

async def agregar_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["obra"]["id_elemento"] = update.message.text

    keyboard = [
        [InlineKeyboardButton("Confirmar", callback_data="CONFIRMAR")]
    ]

    obra = context.user_data["obra"]
    texto = f"""
Confirmar:
{obra}
"""

    await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
    return AGREGAR_CONFIRMAR

# ===== GUARDAR =====

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    obra = context.user_data.get("obra", {})
    logger.info(f"Intentando guardar: {obra}")

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO obras (presupuesto, calle, altura, esquina, elemento, id_elemento)
        VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            obra["presupuesto"],
            obra["calle"],
            obra["altura"],
            obra["esquina"],
            obra["elemento"],
            obra["id_elemento"],
        ))

        conn.commit()

        await query.edit_message_text("✅ Obra guardada correctamente")

    except Exception as e:
        error = str(e)
        logger.error(error)

        await query.edit_message_text(f"❌ ERROR:\n{error}")
        return ConversationHandler.END

    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

    return ConversationHandler.END

# ===== VER =====

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM obras")
    rows = cur.fetchall()

    if not rows:
        texto = "No hay obras"
    else:
        texto = ""
        for r in rows:
            texto += str(r) + "\n"

    await query.edit_message_text(texto)

    cur.close()
    conn.close()

# ===== MAIN =====

if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(agregar_start, pattern="AGREGAR")],
        states={
            AGREGAR_PRESUPUESTO: [MessageHandler(filters.TEXT, agregar_presupuesto)],
            AGREGAR_CALLE: [MessageHandler(filters.TEXT, agregar_calle)],
            AGREGAR_ALTURA: [MessageHandler(filters.TEXT, agregar_altura)],
            AGREGAR_ESQUINA: [MessageHandler(filters.TEXT, agregar_esquina)],
            AGREGAR_ELEMENTO: [MessageHandler(filters.TEXT, agregar_elemento)],
            AGREGAR_ID_ELEMENTO: [MessageHandler(filters.TEXT, agregar_id)],
            AGREGAR_CONFIRMAR: [CallbackQueryHandler(confirmar, pattern="CONFIRMAR")],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(ver, pattern="VER"))

    app.run_polling()
