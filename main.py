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
    VER_FILTRO,
    ELIMINAR_SELECCION, ELIMINAR_CONFIRMAR,
    EDITAR_SELECCION, EDITAR_CAMPO, EDITAR_VALOR,
) = range(12)

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
# (mismos handlers que en el main anterior, no se repiten aquí por brevedad)
# agregar_start, agregar_presupuesto, agregar_calle, agregar_altura, agregar_esquina,
# agregar_elemento, agregar_id_elemento

# --- VER OBRAS ---
# (ver_start y ver_filtro igual que antes, con filtrado por estados activos)

# --- ELIMINAR OBRA ---
# (eliminar_start, eliminar_seleccion, eliminar_confirmar igual que antes)

# --- EDITAR OBRA ---
async def editar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT presupuesto, calle, altura FROM presupuestos ORDER BY presupuesto ASC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        await query.edit_message_text("No hay obras para editar.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
        return ConversationHandler.END

    botones = [[InlineKeyboardButton(f"P-{r[0]} - {r[1]} {r[2]}", callback_data=r[0])] for r in rows]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione obra a editar:", reply_markup=InlineKeyboardMarkup(botones))
    return EDITAR_SELECCION

async def editar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": return await cancelar(update, context)
    context.user_data['editar_id'] = query.data

    campos = ["Calle", "Altura", "Esquina", "Elemento", "ID Elemento"]
    botones = [[InlineKeyboardButton(c, callback_data=c)] for c in campos]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione campo a editar:", reply_markup=InlineKeyboardMarkup(botones))
    return EDITAR_CAMPO

async def editar_campo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": return await cancelar(update, context)
    context.user_data['editar_campo'] = query.data

    # Para Elemento, damos botones de selección
    if query.data == "Elemento":
        elementos = ["Sumidero", "B.R.", "C.I.", "Conducto", "Canaleta"]
        botones = [[InlineKeyboardButton(el, callback_data=el)] for el in elementos]
        botones.append([InlineKeyboardButton("Omitir", callback_data="OMITIR")])
        botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
        await query.edit_message_text("Seleccione nuevo Elemento:", reply_markup=InlineKeyboardMarkup(botones))
        return EDITAR_VALOR
    else:
        await query.edit_message_text(f"Ingrese nuevo valor para {query.data} (o Omitir / Cancelar):")
        return EDITAR_VALOR

async def editar_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Determinar si viene de mensaje o botón
    if update.message:
        text = update.message.text
        if text.lower() == "cancelar": return await cancelar(update, context)
        valor = None if text.lower() == "omitir" else text
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "CANCEL": return await cancelar(update, context)
        valor = None if query.data == "OMITIR" else query.data

    campo_map = {
        "Calle": "calle",
        "Altura": "altura",
        "Esquina": "esquina",
        "Elemento": "elemento",
        "ID Elemento": "id_elemento"
    }
    campo_db = campo_map.get(context.user_data['editar_campo'])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE presupuestos SET {campo_db}=%s WHERE presupuesto=%s", (valor, context.user_data['editar_id']))
    conn.commit()
    cur.close()
    conn.close()

    if update.message:
        await update.message.reply_text(f"✅ Campo {context.user_data['editar_campo']} actualizado.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
    else:
        await update.callback_query.edit_message_text(f"✅ Campo {context.user_data['editar_campo']} actualizado.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))

    return ConversationHandler.END

# --- MAIN ---
if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    # Conversaciones
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

    conv_editar = ConversationHandler(
        entry_points=[CallbackQueryHandler(editar_start, pattern="^EDITAR$")],
        states={
            EDITAR_SELECCION: [CallbackQueryHandler(editar_seleccion)],
            EDITAR_CAMPO: [CallbackQueryHandler(editar_campo)],
            EDITAR_VALOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, editar_valor),
                CallbackQueryHandler(editar_valor)
            ]
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )

    app.add_handler(conv_agregar)
    app.add_handler(conv_ver)
    app.add_handler(conv_eliminar)
    app.add_handler(conv_editar)
    app.add_handler(CallbackQueryHandler(menu_principal, pattern="^PRINCIPAL$"))
    app.add_handler(CommandHandler("start", start))

    print("Bot corriendo...")
    app.run_polling()
