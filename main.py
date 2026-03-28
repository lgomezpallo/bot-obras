import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# ---------------- CONFIG DB ----------------
DATABASE_URL = os.environ.get("DATABASE_URL")
def get_connection():
    return psycopg2.connect(DATABASE_URL)

# ---------------- ESTADOS ----------------
(
    AGREGAR_PRESUPUESTO, AGREGAR_CALLE, AGREGAR_ALTURA,
    AGREGAR_ESQUINA, AGREGAR_ELEMENTO, AGREGAR_ID_ELEMENTO,
    EDITAR_SELECCION, ELIMINAR_SELECCION, CONFIRMAR_ELIMINAR,
    MODIFICAR_ESTADO_SELECCION, INGRESAR_MOTIVO
) = range(11)

ELEMENTOS = ["Sumidero", "B.R.", "C.I.", "Conducto", "Canaleta"]

# ---------------- CANCELAR ----------------
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    await update.effective_message.reply_text("❌ Acción cancelada. Volviendo al menú principal.")
    await start(update, context)
    return ConversationHandler.END

# ---------------- START / MENÚ ----------------
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
    if update.callback_query: await update.callback_query.answer()
    await start(update, context)

# ---------------- AGREGAR OBRA COMPLETO ----------------
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Ingrese número de Presupuesto (o Cancelar):")
    return AGREGAR_PRESUPUESTO

async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto.lower() == "cancelar": return await cancelar(update, context)
    context.user_data['presupuesto'] = texto
    keyboard = [
        [InlineKeyboardButton("Omitir", callback_data="OMITIR")],
        [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]
    ]
    await update.message.reply_text("Ingrese calle (o Omitir):", reply_markup=InlineKeyboardMarkup(keyboard))
    return AGREGAR_CALLE

async def agregar_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto.lower() == "cancelar": return await cancelar(update, context)
    context.user_data['calle'] = "" if texto.lower() == "omitir" else texto
    keyboard = [
        [InlineKeyboardButton("Omitir", callback_data="OMITIR")],
        [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]
    ]
    await update.message.reply_text("Ingrese altura (o Omitir):", reply_markup=InlineKeyboardMarkup(keyboard))
    return AGREGAR_ALTURA

async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto.lower() == "cancelar": return await cancelar(update, context)
    context.user_data['altura'] = "" if texto.lower() == "omitir" else texto
    keyboard = [
        [InlineKeyboardButton("Omitir", callback_data="OMITIR")],
        [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]
    ]
    await update.message.reply_text("Ingrese esquina (o Omitir):", reply_markup=InlineKeyboardMarkup(keyboard))
    return AGREGAR_ESQUINA

async def agregar_esquina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto.lower() == "cancelar": return await cancelar(update, context)
    context.user_data['esquina'] = "" if texto.lower() == "omitir" else texto
    keyboard = [[InlineKeyboardButton(e, callback_data=e)] for e in ELEMENTOS]
    keyboard.append([InlineKeyboardButton("Omitir", callback_data="OMITIR")])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await update.message.reply_text("Seleccione elemento:", reply_markup=InlineKeyboardMarkup(keyboard))
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data
    if data=="CANCEL": return await cancelar(update, context)
    context.user_data['elemento'] = "" if data=="OMITIR" else data
    if data!="OMITIR":
        await query.edit_message_text("Ingrese número o texto identificador del elemento (o Omitir):",
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("Omitir", callback_data="OMITIR")],
                                          [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]
                                      ]))
        return AGREGAR_ID_ELEMENTO
    else:
        return await finalizar_obra(query, context)

async def agregar_id_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if texto.lower()=="cancelar": return await cancelar(update, context)
    context.user_data['id_elemento'] = "" if texto.lower()=="omitir" else texto
    return await finalizar_obra(update, context)

async def finalizar_obra(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO presupuestos (presupuesto, calle, altura, esquina, elemento, id_elemento, estado) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (
            context.user_data.get('presupuesto',''),
            context.user_data.get('calle',''),
            context.user_data.get('altura',''),
            context.user_data.get('esquina',''),
            context.user_data.get('elemento',''),
            context.user_data.get('id_elemento',''),
            "Pendiente"
        )
    )
    conn.commit(); cur.close(); conn.close()
    texto = f"✅ Obra cargada:\nP-{context.user_data.get('presupuesto','')}"
    if hasattr(update_or_query, "callback_query"):
        await update_or_query.callback_query.edit_message_text(texto)
    else:
        await update_or_query.message.reply_text(texto)
    context.user_data.clear()
    await start(update_or_query, context)
    return ConversationHandler.END

# ---------------- VER OBRAS ----------------
async def ver_obras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos ORDER BY presupuesto ASC")
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows:
        await update.callback_query.edit_message_text("No hay obras registradas.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]]))
        return
    estados = sorted(set([r[3] for r in rows]))
    botones = [[InlineKeyboardButton(e, callback_data=f"FILTRAR_{e}")] for e in estados]
    botones.append([InlineKeyboardButton("Todos", callback_data="FILTRAR_TODOS")])
    botones.append([InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")])
    await update.callback_query.edit_message_text("Seleccione estado para filtrar:", reply_markup=InlineKeyboardMarkup(botones))

async def filtrar_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    filtro = query.data.replace("FILTRAR_", "")
    conn = get_connection(); cur = conn.cursor()
    if filtro=="TODOS":
        cur.execute("SELECT presupuesto, calle, altura FROM presupuestos ORDER BY presupuesto ASC")
    else:
        cur.execute("SELECT presupuesto, calle, altura FROM presupuestos WHERE estado=%s ORDER BY presupuesto ASC",(filtro,))
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows:
        await query.edit_message_text(f"No hay obras con estado {filtro}.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]]))
        return
    texto = "\n".join([f"P-{r[0]} - {r[1]} {r[2]}" for r in rows])
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]]))

# ---------------- EDITAR, ELIMINAR, MODIFICAR ESTADO ----------------
# Implementar igual que antes con botones de validación, confirmación y motivo opcional

# ---------------- RUN ----------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ["TOKEN"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern="^PRINCIPAL$"))

    # Agregar
    conv_agregar = ConversationHandler(
        entry_points=[CallbackQueryHandler(agregar_start, pattern="^AGREGAR$")],
        states={
            AGREGAR_PRESUPUESTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_presupuesto)],
            AGREGAR_CALLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_calle)],
            AGREGAR_ALTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_altura)],
            AGREGAR_ESQUINA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_esquina)],
            AGREGAR_ELEMENTO: [CallbackQueryHandler(agregar_elemento)],
            AGREGAR_ID_ELEMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_id_elemento)],
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )
    app.add_handler(conv_agregar)

    # Ver
    app.add_handler(CallbackQueryHandler(ver_obras, pattern="^VER$"))
    app.add_handler(CallbackQueryHandler(filtrar_estado, pattern="^FILTRAR_"))

    # Editar, Eliminar, Modificar Estado se agregan aquí como ConversationHandlers

    app.run_polling()
