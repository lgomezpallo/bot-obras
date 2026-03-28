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
        await update.callback_query.edit_message_text("Bienvenido! Elegí una opción:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.effective_message.reply_text("Bienvenido! Elegí una opción:", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    await start(update, context)

# ---------------- AGREGAR OBRA ----------------
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Ingrese número de Presupuesto (o Cancelar):")
    return AGREGAR_PRESUPUESTO

# Aquí irían los pasos AGREGAR_PRESUPUESTO, AGREGAR_CALLE, etc., igual que tu main anterior,
# con botones de Omitir y Cancelar en cada paso, y Elementos: Sumidero, B.R., C.I., Conducto, Canaleta

# ---------------- VER OBRAS ----------------
async def ver_obras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos ORDER BY presupuesto ASC")
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows:
        await update.callback_query.edit_message_text("No hay obras registradas.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
        return

    # Obtener estados activos
    estados = sorted(set([r[3] for r in rows]))
    botones = [[InlineKeyboardButton(e, callback_data=f"FILTRAR_{e}")] for e in estados]
    botones.append([InlineKeyboardButton("Todos", callback_data="FILTRAR_TODOS")])
    botones.append([InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")])
    await update.callback_query.edit_message_text("Seleccione estado para filtrar:", reply_markup=InlineKeyboardMarkup(botones))

async def filtrar_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    filtro = query.data.replace("FILTRAR_", "")
    conn = get_connection(); cur = conn.cursor()
    if filtro == "TODOS":
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos ORDER BY presupuesto ASC")
    else:
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos WHERE estado=%s ORDER BY presupuesto ASC", (filtro,))
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows:
        await query.edit_message_text(f"No hay obras con estado {filtro}.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
        return
    texto = "\n".join([f"P-{r[0]} - {r[1]} {r[2]}" for r in rows])
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
    ]))

# ---------------- EDITAR OBRA ----------------
async def editar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: await update.callback_query.answer()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT presupuesto, calle, altura FROM presupuestos ORDER BY presupuesto ASC")
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows:
        await update.callback_query.edit_message_text("No hay obras para editar.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
        return ConversationHandler.END
    botones = [[InlineKeyboardButton(f"P-{r[0]} - {r[1]} {r[2]}", callback_data=str(r[0]))] for r in rows]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await update.callback_query.edit_message_text("Seleccione obra para editar:", reply_markup=InlineKeyboardMarkup(botones))
    return EDITAR_SELECCION

async def editar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data=="CANCEL": return await cancelar(update, context)
    context.user_data['editar_presupuesto'] = query.data
    await query.edit_message_text("Función de edición aún no implementada. ✅ Aquí podrías modificar los campos.")
    return ConversationHandler.END

# ---------------- ELIMINAR OBRA ----------------
# Igual que antes, con confirmación final

# ---------------- MODIFICAR ESTADO ----------------
# Igual que antes, con motivo opcional para Pausada

# ---------------- RUN ----------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ["TOKEN"]).build()

    # Start / Menú
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

    # Editar
    conv_editar = ConversationHandler(
        entry_points=[CallbackQueryHandler(editar_start, pattern="^EDITAR$")],
        states={EDITAR_SELECCION: [CallbackQueryHandler(editar_seleccion)]},
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )
    app.add_handler(conv_editar)

    # Eliminar y Modificar Estado iguales que antes

    app.run_polling()
