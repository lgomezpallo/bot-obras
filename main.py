from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters, CallbackQueryHandler
)
import os
import psycopg2

# ---------- VARIABLES DE ENTORNO ----------
TOKEN = os.environ.get("TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not TOKEN or not DATABASE_URL:
    raise ValueError("No se encontró TOKEN o DATABASE_URL")

# ---------- CONEXIÓN A LA DB ----------
def get_connection():
    return psycopg2.connect(DATABASE_URL)

# ---------- CREAR TABLA PRESUPUESTOS ----------
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
            elemento_id TEXT,
            estado TEXT DEFAULT 'Pendiente'
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ---------- ESTADOS CONVERSATION HANDLERS ----------
PRESUPUESTO, CALLE, ALTURA, ESQUINA, ELEMENTO, ELEMENTO_OTRO, ELEMENTO_ID = range(7)
EDITAR_ID, EDITAR_CAMPO = range(7, 9)
ELIMINAR_ID = 9

# ---------- MENÚ INICIAL ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Agregar", "Ver"],
        ["Editar", "Eliminar"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Bot Presupuestos ✅ Elegí una opción:", reply_markup=reply_markup)

async def menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "Agregar":
        return await agregar_obra_start(update, context)
    elif choice == "Ver":
        return await ver_obras(update, context)
    elif choice == "Editar":
        return await editar_obra_start(update, context)
    elif choice == "Eliminar":
        return await eliminar_obra_start(update, context)
    else:
        await update.message.reply_text("Opción no válida ❌")
        return ConversationHandler.END

# ---------- AGREGAR OBRA ----------
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
    keyboard = [
        [InlineKeyboardButton("Sumidero", callback_data="Sumidero"),
         InlineKeyboardButton("BR", callback_data="BR")],
        [InlineKeyboardButton("C.I.", callback_data="CI"),
         InlineKeyboardButton("Otro", callback_data="Otro")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Seleccioná el Elemento:", reply_markup=reply_markup)
    return ELEMENTO

async def agregar_obra_elemento_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    elemento = query.data
    if elemento == "Otro":
        await query.edit_message_text("Escribí el elemento manualmente:")
        return ELEMENTO_OTRO
    context.user_data['elemento'] = elemento
    await query.edit_message_text(f"Elemento seleccionado: {elemento}\nEscribí un identificador o número para este elemento:")
    return ELEMENTO_ID

async def agregar_obra_elemento_otro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['elemento'] = update.message.text
    await update.message.reply_text("Escribí un identificador o número para este elemento:")
    return ELEMENTO_ID

async def agregar_obra_elemento_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['elemento_id'] = update.message.text
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO presupuestos (presupuesto, calle, altura, esquina, elemento, elemento_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        context.user_data['presupuesto'],
        context.user_data['calle'],
        context.user_data['altura'],
        context.user_data['esquina'],
        context.user_data['elemento'],
        context.user_data['elemento_id']
    ))
    conn.commit()
    cur.close()
    conn.close()
    await update.message.reply_text(f"Presupuesto agregado ✅ Elemento: {context.user_data['elemento']} ({context.user_data['elemento_id']}) Estado: Pendiente")
    return ConversationHandler.END

# ---------- VER OBRAS ----------
async def ver_obras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, presupuesto, calle, altura, esquina, elemento, elemento_id, estado FROM presupuestos ORDER BY id;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        await update.message.reply_text("No hay presupuestos cargados aún.")
        return ConversationHandler.END
    msg = ""
    for r in rows:
        msg += f"ID:{r[0]} | Presupuesto:{r[1]} | {r[2]} {r[3]} / {r[4]} | {r[5]} ({r[6]}) | Estado:{r[7]}\n"
    await update.message.reply_text(msg)
    return ConversationHandler.END

# ---------- EDITAR OBRA ----------
async def editar_obra_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escribí el ID de la obra que querés editar:")
    return EDITAR_ID

async def editar_obra_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['editar_id'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("Pendiente", callback_data="Pendiente"),
         InlineKeyboardButton("En ejecución", callback_data="En ejecución")],
        [InlineKeyboardButton("Finalizada", callback_data="Finalizada")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Elegí el nuevo estado:", reply_markup=reply_markup)
    return EDITAR_CAMPO

async def editar_obra_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nuevo_estado = query.data
    obra_id = context.user_data['editar_id']
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE presupuestos SET estado=%s WHERE id=%s", (nuevo_estado, obra_id))
    conn.commit()
    cur.close()
    conn.close()
    await query.edit_message_text(f"Obra ID {obra_id} actualizada ✅ Nuevo estado: {nuevo_estado}")
    return ConversationHandler.END

# ---------- ELIMINAR OBRA ----------
async def eliminar_obra_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escribí el ID de la obra que querés eliminar:")
    return ELIMINAR_ID

async def eliminar_obra_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    obra_id = update.message.text
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM presupuestos WHERE id=%s", (obra_id,))
    conn.commit()
    cur.close()
    conn.close()
    await update.message.reply_text(f"Obra ID {obra_id} eliminada ✅")
    return ConversationHandler.END

# ---------- CANCEL ----------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada ❌")
    return ConversationHandler.END

# ---------- APP ----------
app = ApplicationBuilder().token(TOKEN).build()

# ConversationHandlers separados para cada flujo
conv_agregar = ConversationHandler(
    entry_points=[CommandHandler('agregar_obra', agregar_obra_start)],
    states={
        PRESUPUESTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_presupuesto)],
        CALLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_calle)],
        ALTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_altura)],
        ESQUINA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_esquina)],
        ELEMENTO_OTRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_elemento_otro)],
        ELEMENTO_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_obra_elemento_id)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

conv_editar = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Editar$"), editar_obra_start)],
    states={
        EDITAR_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_obra_id)],
        EDITAR_CAMPO: [CallbackQueryHandler(editar_obra_callback)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

conv_eliminar = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Eliminar$"), eliminar_obra_start)],
    states={
        ELIMINAR_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, eliminar_obra_id)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

# Handlers generales
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("^(Agregar|Ver)$"), menu_choice))
app.add_handler(conv_agregar)
app.add_handler(conv_editar)
app.add_handler(conv_eliminar)
app.add_handler(CallbackQueryHandler(agregar_obra_elemento_callback, pattern="^(Sumidero|BR|CI|Otro)$"))

if __name__ == "__main__":
    print("Bot Presupuestos iniciado")
    app.run_polling()
