import os
import psycopg2
import logging
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

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- CONFIG ----------------
DATABASE_URL = os.environ.get("DATABASE_URL")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

RESET_DB = True  # ⚠️ activar borrado de tabla

if not DATABASE_URL:
    raise ValueError("❌ Falta DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("❌ Falta BOT_TOKEN")

# ---------------- DB ----------------
def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Tabla base
    cur.execute("""
    CREATE TABLE IF NOT EXISTS obras (
        id SERIAL PRIMARY KEY
    )
    """)

    # Columnas existentes
    cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name='obras'
    """)
    cols = [c[0] for c in cur.fetchall()]

    def add_col(name, sql):
        if name not in cols:
            logger.info(f"🛠 Agregando columna: {name}")
            cur.execute(f"ALTER TABLE obras ADD COLUMN {name} {sql}")

    # Migraciones
    add_col("presupuesto", "INTEGER")
    add_col("calle", "TEXT")
    add_col("altura", "INTEGER")
    add_col("esquina", "TEXT")
    add_col("elemento", "TEXT")
    add_col("id_elemento", "TEXT")
    add_col("estado", "TEXT DEFAULT 'Pendiente'")
    add_col("descripcion_estado", "TEXT")

    conn.commit()
    cur.close()
    conn.close()

# ---------------- STATES ----------------
(
    PRESUPUESTO,
    CALLE,
    ALTURA,
    ESQUINA,
    ELEMENTO,
    ID_ELEMENTO,
    CONFIRMAR,
) = range(7)

# ---------------- HELPERS ----------------
def menu_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("📋 Ver obras", callback_data="VER")],
    ])

def safe_int(text):
    try:
        return int(text)
    except:
        return None

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Menú principal:", reply_markup=menu_principal())

# ---------------- AGREGAR ----------------
async def agregar_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["obra"] = {}

    await query.message.reply_text("Ingresá número de presupuesto:")
    return PRESUPUESTO

async def set_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = safe_int(update.message.text)
    if val is None:
        await update.message.reply_text("❌ Debe ser número")
        return PRESUPUESTO

    context.user_data["obra"]["presupuesto"] = val
    await update.message.reply_text("Calle:")
    return CALLE

async def set_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["obra"]["calle"] = update.message.text.strip()
    await update.message.reply_text("Altura:")
    return ALTURA

async def set_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = safe_int(update.message.text)
    if val is None:
        await update.message.reply_text("❌ Debe ser número")
        return ALTURA

    context.user_data["obra"]["altura"] = val
    await update.message.reply_text("Esquina (o escribir '-' para omitir):")
    return ESQUINA

async def set_esquina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    context.user_data["obra"]["esquina"] = None if txt == "-" else txt

    await update.message.reply_text("Elemento (ej: Sumidero, B.R., C.I., etc):")
    return ELEMENTO

async def set_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["obra"]["elemento"] = update.message.text.strip()
    await update.message.reply_text("ID del elemento:")
    return ID_ELEMENTO

async def set_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["obra"]["id_elemento"] = update.message.text.strip()

    obra = context.user_data["obra"]

    texto = (
        "🧾 CONFIRMAR OBRA\n\n"
        f"Presupuesto: {obra.get('presupuesto')}\n"
        f"Calle: {obra.get('calle')}\n"
        f"Altura: {obra.get('altura')}\n"
        f"Esquina: {obra.get('esquina')}\n"
        f"Elemento: {obra.get('elemento')} {obra.get('id_elemento')}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar", callback_data="OK")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="CANCEL")]
    ])

    await update.message.reply_text(texto, reply_markup=keyboard)
    return CONFIRMAR

# ---------------- GUARDAR ----------------
async def guardar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    obra = context.user_data.get("obra", {})
    logger.info(f"💾 Guardando: {obra}")

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO obras (
            presupuesto, calle, altura, esquina, elemento, id_elemento
        ) VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            obra.get("presupuesto"),
            obra.get("calle"),
            obra.get("altura"),
            obra.get("esquina"),
            obra.get("elemento"),
            obra.get("id_elemento"),
        ))

        conn.commit()

        await query.edit_message_text("✅ Obra guardada correctamente")

    except Exception as e:
        logger.error(f"❌ ERROR DB: {e}")
        await query.edit_message_text(f"❌ Error al guardar:\n{e}")
        return ConversationHandler.END

    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

    return ConversationHandler.END

# ---------------- VER ----------------
async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
        SELECT presupuesto, calle, altura, elemento, id_elemento
        FROM obras
        ORDER BY id DESC
        """)

        rows = cur.fetchall()

        if not rows:
            texto = "📭 No hay obras cargadas"
        else:
            texto = "📋 OBRAS:\n\n"
            for r in rows:
                texto += f"#{r[0]} - {r[1]} {r[2]} ({r[3]} {r[4]})\n"

        await query.edit_message_text(texto)

    except Exception as e:
        await query.edit_message_text(f"❌ Error:\n{e}")

    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

# ---------------- CANCEL ----------------
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Operación cancelada")
    return ConversationHandler.END

# ---------------- MAIN ----------------
def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(agregar_inicio, pattern="AGREGAR")],
        states={
            PRESUPUESTO: [MessageHandler(filters.TEXT, set_presupuesto)],
            CALLE: [MessageHandler(filters.TEXT, set_calle)],
            ALTURA: [MessageHandler(filters.TEXT, set_altura)],
            ESQUINA: [MessageHandler(filters.TEXT, set_esquina)],
            ELEMENTO: [MessageHandler(filters.TEXT, set_elemento)],
            ID_ELEMENTO: [MessageHandler(filters.TEXT, set_id)],
            CONFIRMAR: [
                CallbackQueryHandler(guardar, pattern="OK"),
                CallbackQueryHandler(cancelar, pattern="CANCEL"),
            ],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(ver, pattern="VER"))

    logger.info("🚀 Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
