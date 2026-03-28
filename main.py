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
    EDITAR_SELECCION, EDITAR_CAMPO,
    ELIMINAR_SELECCION,
    MODIFICAR_SELECCION, MODIFICAR_ESTADO, MODIFICAR_MOTIVO,
    CANCEL
) = range(13)

# --- Funciones auxiliares ---
def generar_botones_presupuestos(filtro_estado=None):
    conn = get_connection()
    cur = conn.cursor()
    if filtro_estado and filtro_estado != "Todos":
        cur.execute("SELECT id, presupuesto, calle, altura FROM presupuestos WHERE estado=%s ORDER BY presupuesto ASC;", (filtro_estado,))
    else:
        cur.execute("SELECT id, presupuesto, calle, altura FROM presupuestos ORDER BY presupuesto ASC;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    botones = [[InlineKeyboardButton(f"P-{r[1]} - {r[2]} {r[3]}", callback_data=str(r[0]))] for r in rows]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    return InlineKeyboardMarkup(botones)

def botones_omitidos(botones_existentes):
    botones_existentes.append([InlineKeyboardButton("Omitir", callback_data="OMITIR")])
    botones_existentes.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    return InlineKeyboardMarkup(botones_existentes)

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
         InlineKeyboardButton("Eliminar", callback_data="ELIMINAR"),
         InlineKeyboardButton("Modificar Estado", callback_data="MODIFICAR")]
    ]
    await update.effective_message.reply_text(
        "Bienvenido! Elegí una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Agregar obra ---
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    await update.effective_message.reply_text("Ingrese número de Presupuesto (o Cancelar):")
    return AGREGAR_PRESUPUESTO

async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar":
        return await cancelar(update, context)
    context.user_data['presupuesto'] = text
    await update.message.reply_text("Ingrese la Calle (o Omitir / Cancelar):")
    return AGREGAR_CALLE

async def agregar_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar":
        return await cancelar(update, context)
    context.user_data['calle'] = None if text.lower() == "omitir" else text
    await update.message.reply_text("Ingrese la Altura (o Omitir / Cancelar):")
    return AGREGAR_ALTURA

async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar":
        return await cancelar(update, context)
    context.user_data['altura'] = None if text.lower() == "omitir" else text
    await update.message.reply_text("Ingrese la Esquina (o Omitir / Cancelar):")
    return AGREGAR_ESQUINA

async def agregar_esquina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar":
        return await cancelar(update, context)
    context.user_data['esquina'] = None if text.lower() == "omitir" else text
    elementos = [["Sumidero"], ["Pozo"], ["Tapa"], ["Otro"]]
    botones = [ [InlineKeyboardButton(el[0], callback_data=el[0])] for el in elementos]
    botones_markup = botones_omitidos(botones)
    await update.message.reply_text("Seleccione Elemento:", reply_markup=botones_markup)
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL":
        return await cancelar(update, context)
    context.user_data['elemento'] = None if query.data=="OMITIR" else query.data
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO presupuestos (presupuesto, calle, altura, esquina, elemento, estado) VALUES (%s,%s,%s,%s,%s,'Pendiente')",
        (context.user_data.get('presupuesto'),
         context.user_data.get('calle'),
         context.user_data.get('altura'),
         context.user_data.get('esquina'),
         context.user_data.get('elemento'))
    )
    conn.commit()
    cur.close()
    conn.close()
    await query.edit_message_text("✅ Obra agregada correctamente!")
    return ConversationHandler.END

# --- Ver obras ---
async def ver_obras_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    keyboard = [
        [InlineKeyboardButton("Todos", callback_data="Todos"),
         InlineKeyboardButton("Pendiente", callback_data="Pendiente")],
        [InlineKeyboardButton("En Ejecución", callback_data="En Ejecución"),
         InlineKeyboardButton("Finalizada", callback_data="Finalizada")],
        [InlineKeyboardButton("Pausada", callback_data="Pausada")],
        [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]
    ]
    await update.effective_message.reply_text("Seleccione estado a mostrar:", reply_markup=InlineKeyboardMarkup(keyboard))
    return VER_FILTRO

async def ver_obras_filtro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "CANCEL":
        return await cancelar(update, context)

    estado = query.data
    conn = get_connection()
    cur = conn.cursor()

    if estado == "Todos":
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos ORDER BY estado ASC, presupuesto ASC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            await query.edit_message_text("❌ No hay obras en la base de datos.")
            return ConversationHandler.END

        # Agrupar por estado
        grupos = {}
        for r in rows:
            grupos.setdefault(r[3], []).append(r)

        msg = ""
        for est, obras in grupos.items():
            msg += f"🏷 Estado: {est}\n"
            for obra in obras:
                msg += f"P-{obra[0]} - {obra[1]} {obra[2]}\n"
            msg += "\n"

        await query.edit_message_text(msg.strip())
        return ConversationHandler.END

    else:
        cur.execute("SELECT presupuesto, calle, altura FROM presupuestos WHERE estado=%s ORDER BY presupuesto ASC;", (estado,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            await query.edit_message_text(f"❌ No tienes obras en estado {estado}.")
            return ConversationHandler.END

        msg = f"🏷 Estado: {estado}\n\n"
        for r in rows:
            msg += f"P-{r[0]} - {r[1]} {r[2]}\n"

        await query.edit_message_text(msg)
        return ConversationHandler.END

# --- Main ---
if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    conv_agregar = ConversationHandler(
        entry_points=[CallbackQueryHandler(agregar_start, pattern="^AGREGAR$")],
        states={
            AGREGAR_PRESUPUESTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_presupuesto)],
            AGREGAR_CALLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_calle)],
            AGREGAR_ALTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_altura)],
            AGREGAR_ESQUINA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_esquina)],
            AGREGAR_ELEMENTO: [CallbackQueryHandler(agregar_elemento)]
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )

    conv_ver = ConversationHandler(
        entry_points=[CallbackQueryHandler(ver_obras_start, pattern="^VER$")],
        states={VER_FILTRO: [CallbackQueryHandler(ver_obras_filtro)]},
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_agregar)
    app.add_handler(conv_ver)

    print("Bot Presupuestos iniciado con botones Cancelar y listados por estado")
    app.run_polling()
