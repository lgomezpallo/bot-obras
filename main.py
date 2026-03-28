import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# --- Configuración de la DB ---
DATABASE_URL = "postgresql://postgres:ZRLJVotAbsNxThTetXDcKOpHeXwCLgDZ@postgres.railway.internal:5432/railway"

def get_connection():
    return psycopg2.connect(DATABASE_URL)

# --- Estados ConversationHandler ---
(
    AGREGAR_PRESUPUESTO, AGREGAR_CALLE, AGREGAR_ALTURA, AGREGAR_ESQUINA, AGREGAR_ELEMENTO,
    EDITAR_ID, EDITAR_CAMPO,
    ELIMINAR_ID,
    MODIFICAR_ID, MODIFICAR_ESTADO, MODIFICAR_MOTIVO
) = range(11)

# --- Funciones auxiliares ---
def generar_botones_presupuestos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, presupuesto, calle, altura FROM presupuestos ORDER BY id;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    botones = []
    for r in rows:
        texto = f"P-{r[1]} - {r[2]} {r[3]}"
        botones.append([InlineKeyboardButton(texto, callback_data=str(r[0]))])
    return InlineKeyboardMarkup(botones)

def botones_omitidos(botones_existentes):
    botones_existentes.append([InlineKeyboardButton("Omitir", callback_data="OMITIR")])
    return InlineKeyboardMarkup(botones_existentes)

# --- Comando start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Agregar", callback_data="AGREGAR"),
         InlineKeyboardButton("Ver", callback_data="VER")],
        [InlineKeyboardButton("Editar", callback_data="EDITAR"),
         InlineKeyboardButton("Eliminar", callback_data="ELIMINAR"),
         InlineKeyboardButton("Modificar Estado", callback_data="MODIFICAR")]
    ]
    await update.message.reply_text(
        "Bienvenido! Elegí una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Agregar obra ---
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    await update.effective_message.reply_text("Ingrese número de Presupuesto:")
    return AGREGAR_PRESUPUESTO

async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['presupuesto'] = update.message.text
    await update.message.reply_text("Ingrese la Calle (o Omitir):")
    return AGREGAR_CALLE

async def agregar_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "omitir":
        context.user_data['calle'] = None
    else:
        context.user_data['calle'] = update.message.text
    await update.message.reply_text("Ingrese la Altura (o Omitir):")
    return AGREGAR_ALTURA

async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "omitir":
        context.user_data['altura'] = None
    else:
        context.user_data['altura'] = update.message.text
    await update.message.reply_text("Ingrese la Esquina (o Omitir):")
    return AGREGAR_ESQUINA

async def agregar_esquina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "omitir":
        context.user_data['esquina'] = None
    else:
        context.user_data['esquina'] = update.message.text
    # Botones para Elemento
    elementos = [["Sumidero"], ["Pozo"], ["Tapa"], ["Otro"]]
    botones = [ [InlineKeyboardButton(el[0], callback_data=el[0])] for el in elementos]
    botones_markup = botones_omitidos(botones)
    await update.message.reply_text("Seleccione Elemento:", reply_markup=botones_markup)
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        if query.data == "OMITIR":
            context.user_data['elemento'] = None
        else:
            context.user_data['elemento'] = query.data
    # Guardar en DB
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
    await update.effective_message.reply_text("✅ Obra agregada correctamente!")
    return ConversationHandler.END

# --- Ver obras ---
async def ver_obras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        estado_filtro = query.data
    else:
        estado_filtro = None

    conn = get_connection()
    cur = conn.cursor()
    if estado_filtro and estado_filtro != "Todos":
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos WHERE estado=%s ORDER BY id;", (estado_filtro,))
    else:
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos ORDER BY id;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        await update.effective_message.reply_text("No hay presupuestos cargados aún.")
        return

    msg = ""
    for r in rows:
        msg += f"P-{r[0]} - {r[1]} {r[2]} [{r[3]}]\n"
    await update.effective_message.reply_text(msg)
    return

# --- Editar obra ---
async def editar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = generar_botones_presupuestos()
    if not reply_markup.inline_keyboard:
        await update.effective_message.reply_text("No hay obras para editar ❌")
        return ConversationHandler.END
    await update.effective_message.reply_text("Elegí la obra que querés editar:", reply_markup=reply_markup)
    return EDITAR_ID

async def editar_id_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['editar_id'] = query.data
    keyboard = [
        [InlineKeyboardButton("Pendiente", callback_data="Pendiente"),
         InlineKeyboardButton("En ejecución", callback_data="En ejecución")],
        [InlineKeyboardButton("Finalizada", callback_data="Finalizada")]
    ]
    await query.edit_message_text("Elegí el nuevo estado:", reply_markup=InlineKeyboardMarkup(keyboard))
    return EDITAR_CAMPO

async def editar_estado_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nueva = query.data
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE presupuestos SET estado=%s WHERE id=%s", (nueva, context.user_data['editar_id']))
    conn.commit()
    cur.close()
    conn.close()
    await query.edit_message_text(f"✅ Estado actualizado a {nueva}")
    return ConversationHandler.END

# --- Eliminar obra ---
async def eliminar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = generar_botones_presupuestos()
    if not reply_markup.inline_keyboard:
        await update.effective_message.reply_text("No hay obras para eliminar ❌")
        return ConversationHandler.END
    await update.effective_message.reply_text("Elegí la obra que querés eliminar:", reply_markup=reply_markup)
    return ELIMINAR_ID

async def eliminar_id_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    obra_id = query.data
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM presupuestos WHERE id=%s", (obra_id,))
    conn.commit()
    cur.close()
    conn.close()
    await query.edit_message_text("❌ Obra eliminada correctamente")
    return ConversationHandler.END

# --- Modificar Estado ---
async def modificar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = generar_botones_presupuestos()
    if not reply_markup.inline_keyboard:
        await update.effective_message.reply_text("No hay obras para modificar ❌")
        return ConversationHandler.END
    await update.effective_message.reply_text("Elegí la obra a modificar:", reply_markup=reply_markup)
    return MODIFICAR_ID

async def modificar_id_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['modificar_id'] = query.data
    keyboard = [
        [InlineKeyboardButton("Pendiente", callback_data="Pendiente"),
         InlineKeyboardButton("En ejecución", callback_data="En ejecución")],
        [InlineKeyboardButton("Finalizada", callback_data="Finalizada"),
         InlineKeyboardButton("Pausada", callback_data="Pausada")]
    ]
    await query.edit_message_text("Elegí el nuevo estado:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MODIFICAR_ESTADO

async def modificar_estado_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estado_nuevo = query.data
    context.user_data['nuevo_estado'] = estado_nuevo
    if estado_nuevo == "Pausada":
        await query.edit_message_text("Ingrese el motivo de la pausa:")
        return MODIFICAR_MOTIVO
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE presupuestos SET estado=%s WHERE id=%s",
                    (estado_nuevo, context.user_data['modificar_id']))
        conn.commit()
        cur.close()
        conn.close()
        await query.edit_message_text(f"✅ Estado actualizado a {estado_nuevo}")
        return ConversationHandler.END

async def modificar_motivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    motivo = update.message.text
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE presupuestos SET estado='Pausada', motivo_pausa=%s WHERE id=%s",
                (motivo, context.user_data['modificar_id']))
    conn.commit()
    cur.close()
    conn.close()
    await update.message.reply_text(f"✅ Estado actualizado a Pausada\nMotivo: {motivo}")
    return ConversationHandler.END

# --- Main ---
if __name__ == "__main__":
    app = ApplicationBuilder().token("TU_TELEGRAM_TOKEN_AQUI").build()

    conv_agregar = ConversationHandler(
        entry_points=[CallbackQueryHandler(agregar_start, pattern="^AGREGAR$")],
        states={
            AGREGAR_PRESUPUESTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_presupuesto)],
            AGREGAR_CALLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_calle)],
            AGREGAR_ALTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_altura)],
            AGREGAR_ESQUINA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_esquina)],
            AGREGAR_ELEMENTO: [CallbackQueryHandler(agregar_elemento)]
        },
        fallbacks=[]
    )

    conv_editar = ConversationHandler(
        entry_points=[CallbackQueryHandler(editar_start, pattern="^EDITAR$")],
        states={
            EDITAR_ID: [CallbackQueryHandler(editar_id_callback)],
            EDITAR_CAMPO: [CallbackQueryHandler(editar_estado_callback)]
        },
        fallbacks=[]
    )

    conv_eliminar = ConversationHandler(
        entry_points=[CallbackQueryHandler(eliminar_start, pattern="^ELIMINAR$")],
        states={
            ELIMINAR_ID: [CallbackQueryHandler(eliminar_id_callback)]
        },
        fallbacks=[]
    )

    conv_modificar = ConversationHandler(
        entry_points=[CallbackQueryHandler(modificar_start, pattern="^MODIFICAR$")],
        states={
            MODIFICAR_ID: [CallbackQueryHandler(modificar_id_callback)],
            MODIFICAR_ESTADO: [CallbackQueryHandler(modificar_estado_callback)],
            MODIFICAR_MOTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, modificar_motivo)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_agregar)
    app.add_handler(conv_editar)
    app.add_handler(conv_eliminar)
    app.add_handler(conv_modificar)
    app.add_handler(CallbackQueryHandler(ver_obras, pattern="^VER$"))
    
    print("Bot Presupuestos iniciado")
    app.run_polling()
