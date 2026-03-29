import os
import sqlite3
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
import logging # Importar el módulo de logging

# ==========================
# CONFIGURACIÓN DE LOGGING
# ==========================
# Configurar logging básico para ver mensajes en consola (útil para depuración)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================
# BASE DE DATOS - CONFIGURACION
# ==========================
DATABASE_NAME = 'obras.db'

def get_db_connection():
    """Establece y retorna una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Para acceder a las columnas por nombre (como si fuera un diccionario)
    return conn

def init_db():
    """
    Inicializa la base de datos, creando la tabla 'obras' si no existe.
    Si ya existe y faltan columnas, las añade (útil para actualizaciones).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Creamos la tabla principal si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS obras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Verificamos si las columnas 'estado' y 'descripcion_estado' existen
    # Esto es para que no tengas que borrar obras.db si ya lo tenías creado
    cursor.execute("PRAGMA table_info(obras);")
    columns = [info[1] for info in cursor.fetchall()]

    if 'estado' not in columns:
        cursor.execute("ALTER TABLE obras ADD COLUMN estado TEXT DEFAULT 'Pendiente';")
        logger.info("Columna 'estado' añadida a la tabla 'obras'.")
    if 'descripcion_estado' not in columns:
        cursor.execute("ALTER TABLE obras ADD COLUMN descripcion_estado TEXT;")
        logger.info("Columna 'descripcion_estado' añadida a la tabla 'obras'.")

    conn.commit()
    conn.close()
    logger.info("Base de datos inicializada correctamente.")

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

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO obras (presupuesto, calle, altura, esquina, elemento, id_elemento, estado, descripcion_estado) VALUES (?,?,?,?,?,?,?,?)",
                (
                    obra_a_guardar.get("presupuesto"), # Usar.get para evitar KeyError si falta
                    obra_a_guardar.get("calle"),
                    obra_a_guardar.get("altura"),
                    obra_a_guardar.get("esquina"),
                    obra_a_guardar.get("elemento"),
                    obra_a_guardar.get("id_elemento"),
                    obra_a_guardar.get("estado", "Pendiente"), # Usa 'Pendiente' si no se definió estado
                    obra_a_guardar.get("descripcion_estado"), # Será None si no se definió
                ),
            )
            conn.commit()
            await query.edit_message_text("Obra agregada correctamente a la base de datos.")
            logger.info("Obra guardada con éxito.")
        except Exception as e:
            conn.rollback() # Deshace la operación en caso de error
            await query.edit_message_text(f"Hubo un error al guardar la obra: {e}")
            logger.error(f"Error al guardar obra: {e}")
        finally:
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
    """Muestra un listado de todas las obras registradas."""
    query = update.callback_query
    await query.answer()
    logger.info("Mostrando obras.")

    conn = get_db_connection()
    cursor = conn.cursor()
    # Seleccionamos todas las columnas, incluyendo las nuevas de estado
    cursor.execute("SELECT id, presupuesto, calle, altura, esquina, elemento, id_elemento, estado, descripcion_estado FROM obras ORDER BY id DESC")
    obras_db = cursor.fetchall()
    conn.close()

    if not obras_db:
        mensaje = "No hay obras registradas aún."
    else:
        mensaje = "**Listado de Obras:**\n\n"
        for obra in obras_db: # Iteramos sobre cada obra
            mensaje += f"**Obra ID: {obra['id']}**\n"
            mensaje += f" Presupuesto: {obra['presupuesto']}\n"
            mensaje += f" Calle: {obra['calle']}\n"
            mensaje += f" Altura: {obra['altura']}\n"
            mensaje += f" Esquina: {obra['esquina'] if obra['esquina'] else 'N/A'}\n" # Manejo de esquina None
            mensaje += f" Elemento: {obra['elemento']}\n"
            mensaje += f" ID Elemento: {obra['id_elemento']}\n"
            mensaje += f" Estado: {obra['estado']}\n"
            if obra['descripcion_estado']: # Solo muestra la descripción si no es NULL
                mensaje += f" Descripción Estado: {obra['descripcion_estado']}\n"
            mensaje += "\n" # Un espacio entre obras

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
    init_db() # Asegura que la base de datos y la tabla 'obras' estén configuradas

    # Intenta obtener el token del bot de las variables de entorno (como en Railway)
    TOKEN = os.environ.get("BOT_TOKEN")

    # Si el token no está configurado, imprime un error y termina el programa
    if not TOKEN:
        logger.error("Error: La variable de entorno 'BOT_TOKEN' no está configurada.")
        logger.error("Por favor, configura 'BOT_TOKEN' con el token de tu bot de Telegram en Railway o en tu entorno local.")
        exit(1) # Termina la ejecución si no hay token

    app = ApplicationBuilder().token(TOKEN).build()
    logger.info("ApplicationBuilder creado.")

    # --- REGISTRO DE MANEJADORES ---

    # Manejador para el comando /start
    app.add_handler(CommandHandler("start", start))

    # Manejador para el botón "Volver al Menú Principal"
    app.add_handler(CallbackQueryHandler(menu_principal, pattern="^PRINCIPAL$"))

    # Manejador de conversación para la secuencia de "Agregar obra"
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
        fallbacks=[CallbackQueryHandler(cancelar, pattern="^CANCEL$")], # Maneja la cancelación en cualquier estado
    )
    app.add_handler(conv_agregar)
    logger.info("ConversationHandler 'agregar_obra' registrado.")

    # Manejadores para el resto de las opciones del menú principal
    app.add_handler(CallbackQueryHandler(ver_obras, pattern="^VER$"))
    app.add_handler(CallbackQueryHandler(editar_start, pattern="^EDITAR$"))
    app.add_handler(CallbackQueryHandler(eliminar_start, pattern="^ELIMINAR$"))
    app.add_handler(CallbackQueryHandler(modificar_start, pattern="^MODIFICAR$"))
    logger.info("Manejadores de menú principal registrados.")

    logger.info("Bot iniciado y esperando mensajes...")
    app.run_polling(poll_interval=1.0) # Inicia el bot para escuchar actualizaciones de Telegram, con un intervalo de sondeo
