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

# --- Estados ---
(
    AGREGAR_PRESUPUESTO, AGREGAR_CALLE, AGREGAR_ALTURA, AGREGAR_ESQUINA, AGREGAR_ELEMENTO,
    AGREGAR_ID_ELEMENTO,
    VER_FILTRO,
    ELIMINAR_SELECCION, ELIMINAR_CONFIRMAR,
    EDITAR_SELECCION, EDITAR_CAMPO, EDITAR_VALOR,
    MOD_ESTADO_SELEC, MOD_ESTADO_NUEVO, MOD_ESTADO_PAUSA
) = range(15)

# --- Cancelar ---
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
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
    if update.callback_query:
        await update.callback_query.answer()
    await start(update, context)

# ------------------ AGREGAR OBRA ------------------
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
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
    if query.data == "CANCEL": return await cancelar(update, context)
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
        [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
    ]))
    return ConversationHandler.END

# ------------------ VER OBRAS ------------------
async def ver_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT estado FROM presupuestos ORDER BY estado ASC")
    estados = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    if not estados:
        await query.edit_message_text("No hay obras cargadas.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
        return ConversationHandler.END
    estados.append("Todos")
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
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos ORDER BY presupuesto ASC")
    else:
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos WHERE estado=%s ORDER BY presupuesto ASC", (estado_sel,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        await query.edit_message_text(f"No hay obras para el estado {estado_sel}", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
    else:
        estados_dict = {}
        for r in rows:
            estados_dict.setdefault(r[3], []).append(f"P-{r[0]} - {r[1]} {r[2]}")
        msg = ""
        for e, obras in estados_dict.items():
            msg += f"{e}:\n" + "\n".join(obras) + "\n\n"
        await query.edit_message_text(msg.strip(), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")],
            [InlineKeyboardButton("Menú Anterior", callback_data="VER")]
        ]))
    return ConversationHandler.END

# ------------------ EDITAR OBRA ------------------
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
        await query.edit_message_text("No hay obras cargadas.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
        return ConversationHandler.END
    botones = [[InlineKeyboardButton(f"P-{r[0]} - {r[1]} {r[2]}", callback_data=str(r[0]))] for r in rows]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione la obra a editar:", reply_markup=InlineKeyboardMarkup(botones))
    return EDITAR_SELECCION

async def editar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": return await cancelar(update, context)
    context.user_data['editar_presupuesto'] = query.data
    campos = ["Calle", "Altura", "Esquina", "Elemento", "ID Elemento"]
    botones = [[InlineKeyboardButton(c, callback_data=c)] for c in campos]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione el campo a editar:", reply_markup=InlineKeyboardMarkup(botones))
    return EDITAR_CAMPO

async def editar_campo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": return await cancelar(update, context)
    context.user_data['campo'] = query.data.lower().replace(" ", "_")
    await query.edit_message_text(f"Ingrese el nuevo valor para {query.data} (o Omitir / Cancelar):")
    return EDITAR_VALOR

async def editar_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar": return await cancelar(update, context)
    valor = None if text.lower() == "omitir" else text
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE presupuestos SET {context.user_data['campo']}=%s WHERE presupuesto=%s", 
                (valor, context.user_data['editar_presupuesto']))
    conn.commit()
    cur.close()
    conn.close()
    await update.message.reply_text("✅ Obra editada correctamente.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
    ]))
    return ConversationHandler.END

# ------------------ ELIMINAR OBRA ------------------
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
        await query.edit_message_text("No hay obras cargadas.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
        return ConversationHandler.END
    botones = [[InlineKeyboardButton(f"P-{r[0]} - {r[1]} {r[2]}", callback_data=str(r[0]))] for r in rows]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione la obra a eliminar:", reply_markup=InlineKeyboardMarkup(botones))
    return ELIMINAR_SELECCION

async def eliminar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": return await cancelar(update, context)
    context.user_data['eliminar_presupuesto'] = query.data
    botones = [[InlineKeyboardButton("Confirmar Eliminación", callback_data="CONFIRM")],
               [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]]
    await query.edit_message_text("⚠️ ¿Desea eliminar esta obra?", reply_markup=InlineKeyboardMarkup(botones))
    return ELIMINAR_CONFIRMAR

async def eliminar_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": return await cancelar(update, context)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM presupuestos WHERE presupuesto=%s", (context.user_data['eliminar_presupuesto'],))
    conn.commit()
    cur.close()
    conn.close()
    await query.edit_message_text("✅ Obra eliminada correctamente.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
    ]))
    return ConversationHandler.END

# ------------------ MODIFICAR ESTADO ------------------
async def mod_estado_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT presupuesto, calle, altura FROM presupuestos ORDER BY presupuesto ASC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        await query.edit_message_text("No hay obras cargadas.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
        ]))
        return ConversationHandler.END
    botones = [[InlineKeyboardButton(f"P-{r[0]} - {r[1]} {r[2]}", callback_data=str(r[0]))] for r in rows]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione la obra a modificar estado:", reply_markup=InlineKeyboardMarkup(botones))
    return MOD_ESTADO_SELEC

async def mod_estado_selec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": return await cancelar(update, context)
    context.user_data['estado_presupuesto'] = query.data
    estados = ["Pendiente", "En Ejecución", "Finalizada", "Pausada"]
    botones = [[InlineKeyboardButton(e, callback_data=e)] for e in estados]
    botones.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    await query.edit_message_text("Seleccione nuevo estado:", reply_markup=InlineKeyboardMarkup(botones))
    return MOD_ESTADO_NUEVO

async def mod_estado_nuevo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "CANCEL": return await cancelar(update, context)
    nuevo_estado = query.data
    context.user_data['nuevo_estado'] = nuevo_estado
    if nuevo_estado == "Pausada":
        await query.edit_message_text("Ingrese motivo de pausa (opcional, Omitir / Cancelar):")
        return MOD_ESTADO_PAUSA
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE presupuestos SET estado=%s WHERE presupuesto=%s", (nuevo_estado, context.user_data['estado_presupuesto']))
    conn.commit()
    cur.close()
    conn.close()
    await query.edit_message_text(f"✅ Estado actualizado a {nuevo_estado}.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
    ]))
    return ConversationHandler.END

async def mod_estado_pausa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "cancelar": return await cancelar(update, context)
    motivo = None if text.lower() == "omitir" else text
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE presupuestos SET estado=%s WHERE presupuesto=%s", ("Pausada", context.user_data['estado_presupuesto']))
    # Podemos guardar motivo en otro campo si existe
    conn.commit()
    cur.close()
    conn.close()
    await update.message.reply_text("✅ Estado actualizado a Pausada.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Menú Principal", callback_data="PRINCIPAL")]
    ]))
    return ConversationHandler.END

# ------------------ RUN ------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(os.environ["TOKEN"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern="^PRINCIPAL$"))

    # ConversationHandlers
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

    conv_ver = ConversationHandler(
        entry_points=[CallbackQueryHandler(ver_start, pattern="^VER$
