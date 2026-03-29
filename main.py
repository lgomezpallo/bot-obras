import os
import psycopg2
from psycopg2 import sql
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import logging

# ==========================
# CONFIGURACIÓN DE LOGGING
# ==========================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================
# BASE DE DATOS - CONFIGURACION
# ==========================
# URL de conexión a Supabase (PostgreSQL) obtenida de Railway
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    """
    Establece y retorna una conexión a la base de datos PostgreSQL de Supabase
    utilizando la URL de conexión proporcionada en la variable de entorno.
    """
    if not DATABASE_URL:
        logger.error("Error: La variable de entorno 'DATABASE_URL' no está configurada.")
        raise ValueError("DATABASE_URL no configurada.")
    try:
        # psycopg2.connect() ya maneja los parámetros de la URL, incluyendo sslmode.
        # Por ejemplo, la URL de Supabase ya suele incluir?sslmode=require
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos PostgreSQL de Supabase: {e}")
        raise

def init_db():
    """
    Inicializa la base de datos, creando la tabla 'obras' si no existe.
    Si ya existe y faltan columnas, las añade (útil para actualizaciones).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Creamos la tabla principal si no existe.
        # SERIAL PRIMARY KEY es el equivalente de AUTOINCREMENT en PostgreSQL.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS obras (
                id SERIAL PRIMARY KEY,
                presupuesto INTEGER NOT NULL,
                calle TEXT NOT NULL,
                altura INTEGER NOT NULL,
                esquina TEXT,
                elemento TEXT NOT NULL,
                id_elemento TEXT NOT NULL,
                estado TEXT DEFAULT 'Pendiente',
                descripcion_estado TEXT
            )
        ''')

        # Verificamos si las columnas 'estado' y 'descripcion_estado' existen.
        # Usamos information_schema para PostgreSQL.
        cursor.execute(sql.SQL("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'obras'
        """))
        existing_columns = [row[0] for row in cursor.fetchall()]

        if 'estado' not in existing_columns:
            cursor.execute("ALTER TABLE obras ADD COLUMN estado TEXT DEFAULT 'Pendiente';")
            logger.info("Columna 'estado' añadida a la tabla 'obras'.")
        if 'descripcion_estado' not in existing_columns:
            cursor.execute("ALTER TABLE obras ADD COLUMN descripcion_estado TEXT;")
            logger.info("Columna 'descripcion_estado' añadida a la tabla 'obras'.")

        conn.commit()
        logger.info("Base de datos inicializada correctamente.")

    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
        if conn:
            conn.rollback() # Deshace en caso de error
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ==========================
# ESTADOS GLOBALES DE LA CONVERSACIÓN
# ==========================
AGREGAR_PRESUPUESTO = "AGREGAR_PRESUPUESTO"
AGREGAR_CALLE = "AGREGAR_CALLE"
AGREGAR_ALTURA = "AGREGAR_ALTURA"
AGREGAR_ESQUINA = "AGREGAR_ESQUINA"
AGREGAR_ELEMENTO = "AGREGAR_ELEMENTO"
AGREGAR_OTRO_ELEMENTO = "AGREGAR_OTRO_ELEMENTO" # Para el nombre del elemento de texto libre
AGREGAR_ID_ELEMENTO = "AGREGAR_ID_ELEMENTO"
AGREGAR_ESTADO = "AGREGAR_ESTADO" # Para seleccionar el estado de la obra (botón)
AGREGAR_OTRO_ESTADO = "AGREGAR_OTRO_ESTADO" # Para el nombre del estado de texto libre (si se elige 'Otro')
AGREGAR_DESCRIPCION_ESTADO = "AGREGAR_DESCRIPCION_ESTADO" # Para la descripción del estado (si se elige 'Pausada')
AGREGAR_CONFIRMAR = "AGREGAR_CONFIRMAR"

# ==========================
# MANEJADORES DEL MENÚ PRINCIPAL
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú principal al iniciar el bot con /start."""
    logger.info("Comando /start recibido.")
    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("¡Hola! ¿Qué quieres hacer hoy?", reply_markup=reply_markup)
    else: # En caso de que se llame desde otro contexto sin update.message
        logger.warning("start() llamado sin update.message. Posiblemente un caso de uso no previsto.")
        # Podrías querer enviar un mensaje a un chat predefinido o hacer algo diferente
        await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Hola! ¿Qué quieres hacer hoy?", reply_markup=reply_markup)

async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vuelve al menú principal desde cualquier otro punto de la conversación."""
    query = update.callback_query
    await query.answer() # Siempre responder a la callback_query
    logger.info(f"Volviendo al menú principal por {query.data}.")

    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Menú Principal", reply_markup=reply_markup)

# ==========================
# MANEJADORES PARA AGREGAR OBRA
# ==========================
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el proceso de agregar una nueva obra."""
    query = update.callback_query
    await query.answer()
    logger.info("Iniciando flujo de agregar obra.")

    context.user_data["nueva_obra"] = {} # Inicializa un diccionario vacío para la nueva obra
    await query.edit_message_text("Ingresá el presupuesto (solo números enteros):")
    return AGREGAR_PRESUPUESTO

async def agregar_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y valida el presupuesto de la obra."""
    texto = update.message.text.strip()
    logger.info(f"Recibido presupuesto: {texto}")
    try:
        presupuesto = int(texto)
        context.user_data["nueva_obra"]["presupuesto"] = presupuesto
        await update.message.reply_text("Ingresá la calle:")
        return AGREGAR_CALLE
    except ValueError:
        await update.message.reply_text("¡Eso no parece un número entero! Por favor, ingresa el presupuesto solo con números enteros:")
        return AGREGAR_PRESUPUESTO

async def agregar_calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la calle de la obra."""
    context.user_data["nueva_obra"]["calle"] = update.message.text.strip()
    logger.info(f"Recibido calle: {context.user_data['nueva_obra']['calle']}")
    await update.message.reply_text("Ingresá la altura (solo números enteros):")
    return AGREGAR_ALTURA

async def agregar_altura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y valida la altura de la obra."""
    texto = update.message.text.strip()
    logger.info(f"Recibido altura: {texto}")
    try:
        altura = int(texto)
        context.user_data["nueva_obra"]["altura"] = altura
        await update.message.reply_text("Ingresá la esquina:")
        return AGREGAR_ESQUINA
    except ValueError:
        await update.message.reply_text("¡Eso no parece un número entero! Por favor, ingresa la altura solo con números enteros:")
        return AGREGAR_ALTURA

async def agregar_esquina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la esquina de la obra y pide la selección del elemento."""
    context.user_data["nueva_obra"]["esquina"] = update.message.text.strip()
    logger.info(f"Recibido esquina: {context.user_data['nueva_obra']['esquina']}")

    keyboard = [
        [InlineKeyboardButton("Sumidero", callback_data="ELEM_Sumidero")],
        [InlineKeyboardButton("Cámara intermedia", callback_data="ELEM_Cámara intermedia")],
        [InlineKeyboardButton("Canaleta", callback_data="ELEM_Canaleta")],
        [InlineKeyboardButton("Boca de registro", callback_data="ELEM_Boca de registro")],
        [InlineKeyboardButton("Conducto", callback_data="ELEM_Conducto")],
        [InlineKeyboardButton("Otro", callback_data="ELEM_OTRO")], # Opción para texto libre
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Seleccioná el elemento:", reply_markup=reply_markup)
    return AGREGAR_ELEMENTO

async def agregar_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la selección del tipo de elemento de la obra."""
    query = update.callback_query
    await query.answer()
    elemento_seleccionado = query.data.replace("ELEM_", "")
    logger.info(f"Elemento seleccionado: {elemento_seleccionado}")

    if elemento_seleccionado == "OTRO":
        await query.edit_message_text("Ingresá el nombre del elemento (texto libre):")
        return AGREGAR_OTRO_ELEMENTO # Pasa a un estado para recibir el texto libre
    else:
        context.user_data["nueva_obra"]["elemento"] = elemento_seleccionado
        await query.edit_message_text("Ingresá el ID del elemento:")
        return AGREGAR_ID_ELEMENTO

async def agregar_otro_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre de un elemento personalizado (texto libre)."""
    texto_libre_elemento = update.message.text.strip()
    if not texto_libre_elemento:
        await update.message.reply_text("No ingresaste ningún nombre para el elemento. Por favor, intentá de nuevo:")
        return AGREGAR_OTRO_ELEMENTO # Se queda en este estado si la entrada es vacía

    context.user_data["nueva_obra"]["elemento"] = texto_libre_elemento
    logger.info(f"Elemento personalizado: {context.user_data['nueva_obra']['elemento']}")
    await update.message.reply_text("Ingresá el ID del elemento:")
    return AGREGAR_ID_ELEMENTO

async def agregar_id_elemento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el ID del elemento y pide la selección del estado de la obra."""
    context.user_data["nueva_obra"]["id_elemento"] = update.message.text.strip()
    logger.info(f"ID de elemento: {context.user_data['nueva_obra']['id_elemento']}")

    keyboard = [
        [InlineKeyboardButton("Pendiente", callback_data="ESTADO_Pendiente")],
        [InlineKeyboardButton("En Ejecución", callback_data="ESTADO_En Ejecucion")],
        [InlineKeyboardButton("Finalizada", callback_data="ESTADO_Finalizada")],
        [InlineKeyboardButton("Pausada", callback_data="ESTADO_Pausada")],
        [InlineKeyboardButton("Otro", callback_data="ESTADO_OTRO")], # Opción para estado libre
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Seleccioná el estado de la obra:", reply_markup=reply_markup)
    return AGREGAR_ESTADO

async def agregar_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la selección del estado de la obra."""
    query = update.callback_query
    await query.answer()
    estado_seleccionado = query.data.replace("ESTADO_", "")
    logger.info(f"Estado seleccionado: {estado_seleccionado}")

    if estado_seleccionado == "OTRO":
        await query.edit_message_text("Ingresá el nombre del estado (texto libre):")
        return AGREGAR_OTRO_ESTADO # Pasa a un estado para recibir el nombre del estado libre
    elif estado_seleccionado == "Pausada":
        context.user_data["nueva_obra"]["estado"] = estado_seleccionado
        await query.edit_message_text(f"Ingresá una descripción para el motivo de '{estado_seleccionado}':")
        return AGREGAR_DESCRIPCION_ESTADO # Pasa a un estado para recibir la descripción de la pausa
    else: # Para Pendiente, En Ejecución, Finalizada
        context.user_data["nueva_obra"]["estado"] = estado_seleccionado
        context.user_data["nueva_obra"]["descripcion_estado"] = None # No hay descripción para estos estados
        return await _confirmar_obra_message(update, context, query)

async def agregar_otro_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre de un estado personalizado (texto libre)."""
    texto_libre_estado = update.message.text.strip()
    if not texto_libre_estado:
        await update.message.reply_text("No ingresaste ningún nombre para el estado. Por favor, intentá de nuevo:")
        return AGREGAR_OTRO_ESTADO # Se queda en este estado si la entrada es vacía

    context.user_data["nueva_obra"]["estado"] = texto_libre_estado
    context.user_data["nueva_obra"]["descripcion_estado"] = None # Los estados personalizados no tienen descripción adicional en este flujo
    logger.info(f"Estado personalizado: {context.user_data['nueva_obra']['estado']}")
    return await _confirmar_obra_message(update, context)

async def agregar_descripcion_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la descripción para el estado 'Pausada'."""
    descripcion_estado = update.message.text.strip()
    if not descripcion_estado:
        await update.message.reply_text("No ingresaste una descripción. Por favor, intentá de nuevo:")
        return AGREGAR_DESCRIPCION_ESTADO # Se queda en este estado si la entrada es vacía

    context.user_data["nueva_obra"]["descripcion_estado"] = descripcion_estado
    logger.info(f"Descripción de estado 'Pausada': {context.user_data['nueva_obra']['descripcion_estado']}")
    return await _confirmar_obra_message(update, context)

async def _confirmar_obra_message(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    """Función auxiliar para construir y enviar el mensaje de confirmación de la obra."""
    obra = context.user_data["nueva_obra"]
    logger.info("Mostrando mensaje de confirmación de obra.")

    texto = (
        f"**CONFIRMAR OBRA**\n\n"
        f"Presupuesto: {obra.get('presupuesto', 'N/A')}\n"
        f"Calle: {obra.get('calle', 'N/A')}\n"
        f"Altura: {obra.get('altura', 'N/A')}\n"
        f"Esquina: {obra.get('esquina', 'N/A')}\n"
        f"Elemento: {obra.get('elemento', 'N/A')}\n"
        f"ID Elemento: {obra.get('id_elemento', 'N/A')}\n"
        f"Estado: {obra.get('estado', 'No definido')}\n"
    )
    if obra.get('descripcion_estado'): # Solo agrega la descripción si existe
        texto += f"Descripción Estado: {obra['descripcion_estado']}\n"

    keyboard = [
        [InlineKeyboardButton("Confirmar", callback_data="CONFIRMAR_OBRA")],
        [InlineKeyboardButton("Cancelar", callback_data="CANCEL")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Decide si editar el mensaje existente o enviar uno nuevo
    if query: # Si venimos de un callback_query, editamos el mensaje
        await query.edit_message_text(texto, reply_markup=reply_markup, parse_mode="Markdown")
    else: # Si venimos de un MessageHandler (texto libre), respondemos con un nuevo mensaje
        await update.message.reply_text(texto, reply_markup=reply_markup, parse_mode="Markdown")
    return AGREGAR_CONFIRMAR

async def agregar_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda la obra confirmada en la base de datos y finaliza la conversación."""
    query = update.callback_query
    await query.answer()

    if query.data == "CONFIRMAR_OBRA":
        obra_a_guardar = context.user_data["nueva_obra"]
        logger.info(f"Confirmando y guardando obra: {obra_a_guardar}")

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO obras (presupuesto, calle, altura, esquina, elemento, id_elemento, estado, descripcion_estado) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    obra_a_guardar.get("presupuesto"),
                    obra_a_guardar.get("calle"),
                    obra_a_guardar.get("altura"),
                    obra_a_guardar.get("esquina"),
                    obra_a_guardar.get("elemento"),
                    obra_a_guardar.get("id_elemento"),
                    obra_a_guardar.get("estado", "Pendiente"),
                    obra_a_guardar.get("descripcion_estado"),
                ),
            )
            conn.commit()
            await query.edit_message_text("Obra agregada correctamente a la base de datos.")
            logger.info("Obra guardada con éxito.")
        except Exception as e:
            if conn:
                conn.rollback() # Deshace la operación en caso de error
            await query.edit_message_text(f"Hubo un error al guardar la obra: {e}")
            logger.error(f"Error al guardar obra: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    context.user_data["nueva_obra"] = {} # Limpia los datos temporales del usuario

    # Vuelve al menú principal
    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Menú Principal", reply_markup=reply_markup)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela la operación actual y regresa al menú principal."""
    query = update.callback_query
    await query.answer()
    logger.info("Operación cancelada.")
    await query.edit_message_text("Operación cancelada. Volviendo al menú principal.")

    context.user_data.pop("nueva_obra", None) # Limpia los datos temporales del usuario de forma segura

    keyboard = [
        [InlineKeyboardButton("Agregar obra", callback_data="AGREGAR")],
        [InlineKeyboardButton("Ver obras", callback_data="VER")],
        [InlineKeyboardButton("Editar obra", callback_data="EDITAR")],
        [InlineKeyboardButton("Modificar estado", callback_data="MODIFICAR")],
        [InlineKeyboardButton("Eliminar obra", callback_data="ELIMINAR")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup) # Edita solo el reply_markup
    return ConversationHandler.END # Finaliza la conversación actual

# ==========================
# MANEJADORES PARA OTRAS OPCIONES (PLACEHOLDERS)
# ==========================
async def ver_obras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra un listado de todas las obras registradas con el formato deseado."""
    query = update.callback_query
    await query.answer()
    logger.info("Mostrando obras.")

    conn = None
    cursor = None
    obras_db = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Para PostgreSQL, `cursor.fetchall()` devuelve tuplas.
        # Las mapeamos a diccionarios para poder acceder por nombre de columna
        # como 'obra['presupuesto']' en el mensaje final.
        cursor.execute("SELECT id, presupuesto, calle, altura, esquina, elemento, id_elemento, estado, descripcion_estado FROM obras ORDER BY id DESC")
        raw_obras = cursor.fetchall()

        for row in raw_obras:
            obras_db.append({
                'id': row[0],
                'presupuesto': row[1],
                'calle': row[2],
                'altura': row[3],
                'esquina': row[4],
                'elemento': row[5],
                'id_elemento': row[6],
                'estado': row[7],
                'descripcion_estado': row[8],
            })

    except Exception as e:
        logger.error(f"Error al obtener obras de la base de datos: {e}")
        await query.edit_message_text(f"Hubo un error al cargar las obras: {e}", parse_mode="Markdown")
        obras_db = [] # Aseguramos que la lista esté vacía para no mostrar nada incompleto
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not obras_db:
        mensaje = "No hay obras registradas aún."
    else:
        mensaje = "**Listado de Obras:**\n\n"
        for obra in obras_db:
            mensaje += f"**Presupuesto: {obra['presupuesto']}**\n"
            mensaje += f" Calle: {obra['calle']}\n"
            mensaje += f" Altura: {obra['altura']}\n"
            mensaje += f" Esquina: {obra['esquina'] if obra['esquina'] else 'N/A'}\n"
            mensaje += f" Elemento: {obra['elemento']} {obra['id_elemento']}\n"
            mensaje += f" Estado: {obra['estado']}\n"
            if obra['descripcion_estado']:
                mensaje += f" Descripción Estado: {obra['descripcion_estado']}\n"
            mensaje += "\n"

    await query.edit_message_text(mensaje, parse_mode="Markdown")
    keyboard = [[InlineKeyboardButton("Volver al Menú Principal", callback_data="PRINCIPAL")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup)

async def editar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder para la función de editar obra."""
    query = update.callback_query
    await query.answer()
    logger.info("Placeholder: Editar obra.")
    await query.edit_message_text("Editar obra (funcionalidad pendiente).")
    keyboard = [[InlineKeyboardButton("Volver al Menú Principal", callback_data="PRINCIPAL")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup)

async def eliminar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder para la función de eliminar obra."""
    query = update.callback_query
    await query.answer()
    logger.info("Placeholder: Eliminar obra.")
    await query.edit_message_text("Eliminar obra (funcionalidad pendiente).")
    keyboard = [[InlineKeyboardButton("Volver al Menú Principal", callback_data="PRINCIPAL")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup)

async def modificar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder para la función de modificar estado."""
    query = update.callback_query
    await query.answer()
    logger.info("Placeholder: Modificar estado.")
    await query.edit_message_text("Modificar estado (funcionalidad pendiente).")
    keyboard = [[InlineKeyboardButton("Volver al Menú Principal", callback_data="PRINCIPAL")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup)

# ==========================
# INICIO DEL BOT
# ==========================
if __name__ == "__main__":
    init_db() # La inicialización de la DB se hace al inicio.

    TOKEN = os.environ.get("BOT_TOKEN")

    if not TOKEN:
        logger.error("Error: La variable de entorno 'BOT_TOKEN' no está configurada.")
        logger.error("Por favor, configura 'BOT_TOKEN' con el token de tu bot de Telegram en Railway o en tu entorno local.")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    logger.info("ApplicationBuilder creado.")

    # --- REGISTRO DE MANEJADORES ---

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern="^PRINCIPAL$"))

    conv_agregar = ConversationHandler(
        entry_points=[CallbackQueryHandler(agregar_start, pattern="^AGREGAR$")],
        states={
            AGREGAR_PRESUPUESTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_presupuesto)],
            AGREGAR_CALLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_calle)],
            AGREGAR_ALTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_altura)],
            AGREGAR_ESQUINA: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_esquina)],
            AGREGAR_ELEMENTO: [CallbackQueryHandler(agregar_elemento)],
            AGREGAR_OTRO_ELEMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_otro_elemento)],
            AGREGAR_ID_ELEMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_id_elemento)],
            AGREGAR_ESTADO: [CallbackQueryHandler(agregar_estado)],
            AGREGAR_OTRO_ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_otro_estado)],
            AGREGAR_DESCRIPCION_ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_descripcion_estado)],
            AGREGAR_CONFIRMAR: [CallbackQueryHandler(agregar_confirmar, pattern="^CONFIRMAR_OBRA$")],
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="^CANCEL$")],
    )
    app.add_handler(conv_agregar)
    logger.info("ConversationHandler 'agregar_obra' registrado.")

    app.add_handler(CallbackQueryHandler(ver_obras, pattern="^VER$"))
    app.add_handler(CallbackQueryHandler(editar_start, pattern="^EDITAR$"))
    app.add_handler(CallbackQueryHandler(eliminar_start, pattern="^ELIMINAR$"))
    app.add_handler(CallbackQueryHandler(modificar_start, pattern="^MODIFICAR$"))
    logger.info("Manejadores de menú principal registrados.")

    logger.info("Bot iniciado y esperando mensajes...")
    app.run_polling(poll_interval=1.0)
