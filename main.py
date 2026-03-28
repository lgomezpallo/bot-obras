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
    MODIFICAR_SELECCION, MODIFICAR_ESTADO, MODIFICAR_MOTIVO
) = range(12)

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
    return InlineKeyboardMarkup(botones)

def botones_omitidos(botones_existentes):
    botones_existentes.append([InlineKeyboardButton("Omitir", callback_data="OMITIR")])
    return InlineKeyboardMarkup(botones_existentes)

# --- Inicio ---
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
    if query: await query.answer()
    await update.effective_message.reply_text("Ingrese número de Presupuesto:")
    return AGREGAR_PRESUPUESTO

async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['presupuesto'] = update.message.text
    await update.message.reply_text("Ingrese la Calle (o Omitir):")
    return AGREGAR_CALLE

async def agregar_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['calle'] = None if update.message.text.lower() == "omitir" else update.message.text
    await update.message.reply_text("Ingrese la Altura (o Omitir):")
    return AGREGAR_ALTURA

async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['altura'] = None if update.message.text.lower() == "omitir" else update.message.text
    await update.message.reply_text("Ingrese la Esquina (o Omitir):")
    return AGREGAR_ESQUINA

async def agregar_esquina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['esquina'] = None if update.message.text.lower() == "omitir" else update.message.text
    elementos = [["Sumidero"], ["Pozo"], ["Tapa"], ["Otro"]]
    botones = [ [InlineKeyboardButton(el[0], callback_data=el[0])] for el in elementos]
    botones_markup = botones_omitidos(botones)
    await update.message.reply_text("Seleccione Elemento:", reply_markup=botones_markup)
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
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
        [InlineKeyboardButton("Pausada", callback_data="Pausada")]
    ]
    await update.effective_message.reply_text("Seleccione estado a mostrar:", reply_markup=InlineKeyboardMarkup(keyboard))
    return VER_FILTRO

async def ver_obras_filtro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estado = query.data
    conn = get_connection()
    cur = conn.cursor()
    if estado == "Todos":
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos ORDER BY presupuesto ASC;")
    else:
        cur.execute("SELECT presupuesto, calle, altura, estado FROM presupuestos WHERE estado=%s ORDER BY presupuesto ASC;", (estado,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        await query.edit_message_text("No hay presupuestos para este filtro.")
        return ConversationHandler.END
    msg = "\n".join([f"P-{r[0]} - {r[1]} {r[2]} [{r[3]}]" for r in rows])
    await query.edit_message_text(msg)
    return ConversationHandler.END

# --- Editar ---
async def editar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    await update.effective_message.reply_text("Seleccione la obra a editar:", reply_markup=generar_botones_presupuestos())
    return EDITAR_SELECCION

async def editar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['editar_id'] = query.data
    campos = ["Presupuesto","Calle","Altura","Esquina","Elemento"]
    botones = [[InlineKeyboardButton(c, callback_data=c)] for c in campos]
    await query.edit_message_text("Seleccione campo a modificar:", reply_markup=InlineKeyboardMarkup(botones))
    return EDITAR_CAMPO

async def editar_campo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    campo = query.data
    context.user_data['campo'] = campo
    await query.edit_message_text(f"Ingrese nuevo valor para {campo} (o Omitir):")
    return EDITAR_CAMPO

# --- Eliminar ---
async def eliminar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    await update.effective_message.reply_text("Seleccione la obra a eliminar:", reply_markup=generar_botones_presupuestos())
    return ELIMINAR_SELECCION

async def eliminar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM presupuestos WHERE id=%s;", (query.data,))
    conn.commit()
    cur.close()
    conn.close()
    await query.edit_message_text("✅ Obra eliminada correctamente!")
    return ConversationHandler.END

# --- Modificar estado ---
async def modificar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    await update.effective_message.reply_text("Seleccione obra a modificar:", reply_markup=generar_botones_presupuestos())
    return MODIFICAR_SELECCION

async def modificar_seleccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['modificar_id'] = query.data
    estados = ["Pendiente","En Ejecución","Finalizada","Pausada"]
    botones = [[InlineKeyboardButton(e, callback_data=e)] for e in estados]
    await query.edit_message_text("Seleccione nuevo estado:", reply_markup=InlineKeyboardMarkup(botones))
    return MODIFICAR_ESTADO

async def modificar_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['nuevo_estado'] = query.data
    if query.data == "Pausada":
        await query.edit_message_text("Ingrese motivo de la pausa:")
        return MODIFICAR_MOTIVO
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE presupuestos SET estado=%s WHERE id=%s;", (query.data, context.user_data['modificar_id']))
        conn.commit()
        cur.close()
        conn.close()
        await query.edit_message_text(f"✅ Estado actualizado a {query.data}")
        return ConversationHandler.END

async def modificar_motivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    motivo = update.message.text
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE presupuestos SET estado='Pausada', motivo_pausa=%s WHERE id=%s;", (motivo, context.user_data['modificar_id']))
    conn.commit()
    cur.close()
    conn.close()
    await update.message.reply_text(f"✅ Estado actualizado a Pausada. Motivo: {motivo}")
    return ConversationHandler.END

# --- Main ---
if __name__ == "__main__":
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    # Conversational handlers
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

    conv_ver = ConversationHandler(
        entry_points=[CallbackQueryHandler(ver_obras_start, pattern="^VER$")],
        states={
            VER_FILTRO: [CallbackQueryHandler(ver_obras_filtro)]
        },
        fallbacks=[]
    )

    conv_editar = ConversationHandler(
        entry_points=[CallbackQueryHandler(editar_start, pattern="^EDITAR$")],
        states={
            EDITAR_SELECCION: [CallbackQueryHandler(editar_seleccion)],
            EDITAR_CAMPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_campo)]
        },
        fallbacks=[]
    )

    conv_eliminar = ConversationHandler(
        entry_points=[CallbackQueryHandler(eliminar_start, pattern="^ELIMINAR$")],
        states={ELIMINAR_SELECCION: [CallbackQueryHandler(eliminar_seleccion)]},
        fallbacks=[]
    )

    conv_modificar = ConversationHandler(
        entry_points=[CallbackQueryHandler(modificar_start, pattern="^MODIFICAR$")],
        states={
            MODIFICAR_SELECCION: [CallbackQueryHandler(modificar_seleccion)],
            MODIFICAR_ESTADO: [CallbackQueryHandler(modificar_estado)],
            MODIFICAR_MOTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, modificar_motivo)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_agregar)
    app.add_handler(conv_ver)
    app.add_handler(conv_editar)
    app.add_handler(conv_eliminar)
    app.add_handler(conv_modificar)

    print("Bot Presupuestos iniciado")
    app.run_polling()
