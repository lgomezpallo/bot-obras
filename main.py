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
    AGREGAR_ID_ELEMENTO,
    VER_FILTRO, VER_LISTADO,
    ELIMINAR_SELECCION, ELIMINAR_CONFIRMAR,
    MOD_ESTADO_SELEC, MOD_ESTADO_NUEVO, MOD_ESTADO_PAUSA
) = range(13)

# --- Cancelar ---
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    await update.effective_message.reply_text("❌ Acción cancelada. Volviendo al menú principal.")
    await start(update, context)
    return ConversationHandler.END

# --- Menú Principal ---
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

async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)

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
    if text.lower() == "cancelar": return await cancelar(update, context)
    context.user_data['calle'] = None if text.lower() == "omitir" else text
    await update.message.reply_text("Ingrese la Altura (o Omitir / Cancelar):")
    return AGREGAR_ALTURA

async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar": return await cancelar(update, context)
    context.user_data['altura'] = None if text.lower() == "omitir" else text
    await update.message.reply_text("Ingrese la Esquina (o Omitir / Cancelar):")
    return AGREGAR_ESQUINA

async def agregar_esquina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar": return await cancelar(update, context)
    context.user_data['esquina'] = None if text.lower() == "omitir" else text

    elementos = ["Sumidero", "B.R.", "C.I.", "Conducto", "Canaleta"]
    botones = [[InlineKeyboardButton(el, callback_data=el)] for el in elementos]
    botones.append([InlineKeyboardButton("Omitir", callback_data="OMITIR")])
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])

    await update.message.reply_text("Seleccione Elemento:", reply_markup=InlineKeyboardMarkup(botones))
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": 
        return await cancelar(update, context)
    context.user_data['elemento'] = None if query.data == "OMITIR" else query.data

    await query.edit_message_text("Ingrese un identificador para este elemento (o Omitir / Cancelar):")
    return AGREGAR_ID_ELEMENTO

async def agregar_id_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar": return await cancelar(update, context)
    context.user_data['id_elemento'] = None if text.lower() == "omitir" else text

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO presupuestos (presupuesto, calle, altura, esquina, elemento, id_elemento, estado) VALUES (%s,%s,%s,%s,%s,%s,'Pendiente')",
        (
            context.user_data.get('presupuesto'),
            context.user_data.get('calle'),
            context.user_data.get('altura'),
            context.user_data.get('esquina'),
            context.user_data.get('elemento'),
            context.user_data.get('id_elemento')
        )
    )
    conn.commit()
    cur.close()
    conn.close()

    await update.message.reply_text("✅ Obra agregada correctamente!", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")],
        [InlineKeyboardButton("Menú Anterior", callback_data="PRINCIPAL")]
    ]))
    return ConversationHandler.END

# --- VER OBRAS ---
async def ver_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estados = ["Pendiente", "En Ejecución", "Finalizada", "Pausada", "Todos"]
    botones = [[InlineKeyboardButton(e, callback_data=e)] for e in estados]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione estado a ver:", reply_markup=InlineKeyboardMarkup(botones))
    return VER_FILTRO

async def ver_filtro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estado_sel = query.data
    if estado_sel == "CANCEL": return await cancelar(update, context)

    conn = get_connection()
    cur = conn.cursor()
    if estado_sel == "Todos":
        cur.execute("SELECT presupuesto, calle, altura FROM presupuestos ORDER BY presupuesto ASC")
    else:
        cur.execute("SELECT presupuesto, calle, altura FROM presupuestos WHERE estado=%s ORDER BY presupuesto ASC", (estado_sel,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        await query.edit_message_text(f"No hay obras para el estado {estado_sel}")
    else:
        msg = f"Obras ({estado_sel}):\n" + "\n".join([f"P-{r[0]} - {r[1]} {r[2]}" for r in rows])
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")],
            [InlineKeyboardButton("Menú Anterior", callback_data="PRINCIPAL")]
        ]))
    return ConversationHandler.END

# --- ELIMINAR OBRA ---
async def eliminar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT presupuesto, calle, altura FROM presupuestos ORDER BY presupuesto ASC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        await query.edit_message_text("No hay obras para eliminar.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
        return ConversationHandler.END

    botones = [[InlineKeyboardButton(f"P-{r[0]} - {r[1]} {r[2]}", callback_data=r[0])] for r in rows]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione obra a eliminar:", reply_markup=InlineKeyboardMarkup(botones))
    return ELIMINAR_SELECCION

async def eliminar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": return await cancelar(update, context)
    context.user_data['eliminar_id'] = query.data

    botones = [
        [InlineKeyboardButton("Confirmar Eliminación", callback_data="CONFIRM")],
        [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]
    ]
    await query.edit_message_text(f"Confirma eliminar la obra P-{query.data}?", reply_markup=InlineKeyboardMarkup(botones))
    return ELIMINAR_CONFIRMAR

async def eliminar_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": return await cancelar(update, context)
    eliminar_id = context.user_data.get('eliminar_id')

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM presupuestos WHERE presupuesto=%s", (eliminar_id,))
    conn.commit()
    cur.close()
    conn.close()

    await query.edit_message_text("✅ Obra eliminada correctamente.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
    ]))
    return ConversationHandler.END

# --- MODIFICAR ESTADO ---
async def mod_estado_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT estado FROM presupuestos ORDER BY estado ASC")
    estados = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()

    botones = [[InlineKeyboardButton(e, callback_data=e)] for e in estados]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione obra a modificar:", reply_markup=InlineKeyboardMarkup(botones))
    return MOD_ESTADO_SELEC

# --- MAIN ---
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
            AGREGAR_ELEMENTO: [CallbackQueryHandler(agregar_elemento)],
            AGREGAR_ID_ELEMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_id_elemento)]
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )

    conv_ver = ConversationHandler(
        entry_points=[CallbackQueryHandler(ver_start, pattern="^VER$")],
        states={VER_FILTRO: [CallbackQueryHandler(ver_filtro)]},
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )

    conv_eliminar = ConversationHandler(
        entry_points=[CallbackQueryHandler(eliminar_start, pattern="^ELIMINAR$")],
        states={
            ELIMINAR_SELECCION: [CallbackQueryHandler(eliminar_seleccion)],
            ELIMINAR_CONFIRMAR: [CallbackQueryHandler(eliminar_confirmar)]
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )

    # Aquí se integrarían conv_mod_estado y conv_editar igual que los anteriores
    app.add_handler(conv_agregar)
    app.add_handler(conv_ver)
    app.add_handler(conv_eliminar)
    app.add_handler(CallbackQueryHandler(menu_principal, pattern="^PRINCIPAL$"))
    app.add_handler(CommandHandler("start", start))

    print("Bot corriendo...")
    app.run_polling()
