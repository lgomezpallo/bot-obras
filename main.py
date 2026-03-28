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
    EDITAR_SELECCION, EDITAR_CAMPO,
    ELIMINAR_SELECCION, CONFIRMAR_ELIMINAR,
    MODIFICAR_ESTADO_SELECCION, SELECCION_ESTADO, INGRESAR_MOTIVO
) = range(13)

ELEMENTOS = ["Sumidero", "B.R.", "C.I.", "Conducto", "Canaleta"]
ESTADOS = ["Pendiente", "En Ejecución", "Finalizada", "Pausada"]
CAMPOS_EDITABLES = ["calle","altura","esquina","elemento","id_elemento"]

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

# ---------------- AGREGAR OBRA ----------------
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Ingrese número de Presupuesto (o Cancelar):")
    return AGREGAR_PRESUPUESTO

# (Agregar pasos iguales a la versión anterior, no repetidos aquí por brevedad)
# Usar agregar_presupuesto, agregar_calle, agregar_altura, agregar_esquina,
# agregar_elemento, agregar_id_elemento, finalizar_obra del main anterior

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
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos ORDER BY presupuesto ASC")
    else:
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos WHERE estado=%s ORDER BY presupuesto ASC",(filtro,))
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows:
        await query.edit_message_text(f"No hay obras con estado {filtro}.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]]))
        return
    texto = "\n".join([f"P-{r[0]} - {r[1]} {r[2]}" for r in rows])
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]]))

# ---------------- EDITAR OBRA ----------------
async def editar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT presupuesto, calle, altura FROM presupuestos ORDER BY presupuesto ASC")
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows:
        await query.edit_message_text("No hay obras para editar.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]]))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f"P-{r[0]} - {r[1]} {r[2]}", callback_data=str(r[0]))] for r in rows]
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione la obra a editar:", reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITAR_SELECCION

async def editar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data=="CANCEL": return await cancelar(update, context)
    context.user_data['editar_presupuesto'] = query.data
    keyboard = [[InlineKeyboardButton(c, callback_data=c)] for c in CAMPOS_EDITABLES]
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione campo a editar:", reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITAR_CAMPO

async def editar_campo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data=="CANCEL": return await cancelar(update, context)
    campo = query.data
    context.user_data['campo_editar'] = campo
    await query.edit_message_text(f"Ingrese nuevo valor para {campo}:")
    return EDITAR_CAMPO + 100  # valor temporal para recibir texto

async def editar_guardar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valor = update.message.text.strip()
    campo = context.user_data['campo_editar']
    presu = context.user_data['editar_presupuesto']
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"UPDATE presupuestos SET {campo}=%s WHERE presupuesto=%s",(valor,presu))
    conn.commit(); cur.close(); conn.close()
    await update.message.reply_text("✅ Campo actualizado correctamente.")
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END

# ---------------- ELIMINAR OBRA ----------------
async def eliminar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT presupuesto, calle, altura FROM presupuestos ORDER BY presupuesto ASC")
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows:
        await query.edit_message_text("No hay obras para eliminar.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]]))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f"P-{r[0]} - {r[1]} {r[2]}", callback_data=str(r[0]))] for r in rows]
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione obra a eliminar:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ELIMINAR_SELECCION

async def eliminar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data=="CANCEL": return await cancelar(update, context)
    context.user_data['eliminar_presupuesto'] = query.data
    keyboard = [[InlineKeyboardButton("Confirmar Eliminación", callback_data="CONFIRM")],
                [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]]
    await query.edit_message_text("⚠️ Confirme eliminar la obra:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRMAR_ELIMINAR

async def eliminar_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data=="CANCEL": return await cancelar(update, context)
    presu = context.user_data['eliminar_presupuesto']
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM presupuestos WHERE presupuesto=%s",(presu,))
    conn.commit(); cur.close(); conn.close()
    await query.edit_message_text("✅ Obra eliminada correctamente.")
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END

# ---------------- MODIFICAR ESTADO ----------------
async def modificar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT presupuesto, calle, altura FROM presupuestos ORDER BY presupuesto ASC")
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows:
        await query.edit_message_text("No hay obras para modificar estado.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]]))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f"P-{r[0]} - {r[1]} {r[2]}", callback_data=str(r[0]))] for r in rows]
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione obra para modificar estado:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MODIFICAR_ESTADO_SELECCION

async def seleccionar_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data=="CANCEL": return await cancelar(update, context)
    context.user_data['estado_presupuesto'] = query.data
    keyboard = [[InlineKeyboardButton(e, callback_data=e)] for e in ESTADOS]
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione nuevo estado:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECCION_ESTADO

async def ingresar_motivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data=="CANCEL": return await cancelar(update, context)
    context.user_data['nuevo_estado'] = query.data
    if query.data=="Pausada":
        await query.edit_message_text("Ingrese motivo de pausa (opcional, puede omitir):")
        return INGRESAR_MOTIVO
    else:
        return await actualizar_estado(query, context, motivo="")

async def actualizar_estado(update_or_query, context: ContextTypes.DEFAULT_TYPE, motivo=None):
    conn = get_connection(); cur = conn.cursor()
    presu = context.user_data['estado_presupuesto']
    estado = context.user_data['nuevo_estado']
    cur.execute("UPDATE presupuestos SET estado=%s WHERE presupuesto=%s",(estado,presu))
    conn.commit(); cur.close(); conn.close()
    texto = f"✅ Estado actualizado a {estado}"
    if estado=="Pausada" and motivo:
        texto += f"\nMotivo: {motivo}"
    if hasattr(update_or_query,"callback_query"):
        await update_or_query.callback_query.edit_message_text(texto)
    else:
        await update_or_query.message.reply_text(texto)
    context.user_data.clear()
    await start(update_or_query, context)
    return ConversationHandler.END

async def guardar_motivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    motivo = update.message.text.strip()
    return await actualizar_estado(update, context, motivo=motivo)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ["TOKEN"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern="^PRINCIPAL$"))

    # Agregar obra
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

    # Ver obras
    app.add_handler(CallbackQueryHandler(ver_obras, pattern="^VER$"))
    app.add_handler(CallbackQueryHandler(filtrar_estado, pattern="^FILTRAR_"))

    # Editar obra
    conv_editar = ConversationHandler(
        entry_points=[CallbackQueryHandler(editar_start, pattern="^EDITAR$")],
        states={
            EDITAR_SELECCION: [CallbackQueryHandler(editar_seleccion)],
            EDITAR_CAMPO: [CallbackQueryHandler(editar_campo)],
            EDITAR_CAMPO + 100: [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_guardar)]
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )
    app.add_handler(conv_editar)

    # Eliminar obra
    conv_eliminar = ConversationHandler(
        entry_points=[CallbackQueryHandler(eliminar_start, pattern="^ELIMINAR$")],
        states={
            ELIMINAR_SELECCION: [CallbackQueryHandler(eliminar_seleccion)],
            CONFIRMAR_ELIMINAR: [CallbackQueryHandler(eliminar_confirmar)]
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )
    app.add_handler(conv_eliminar)

    # Modificar estado
    conv_estado = ConversationHandler(
        entry_points=[CallbackQueryHandler(modificar_start, pattern="^MODIFICAR$")],
        states={
            MODIFICAR_ESTADO_SELECCION: [CallbackQueryHandler(seleccionar_estado)],
            SELECCION_ESTADO: [CallbackQueryHandler(ingresar_motivo)],
            INGRESAR_MOTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_motivo)]
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="CANCEL")]
    )
    app.add_handler(conv_estado)

    app.run_polling()
