from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

# Tomamos el token de las variables de Railway
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    raise ValueError("No se encontró la variable TOKEN")

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot funcionando correctamente ✅")

# Construimos la app
app = ApplicationBuilder().token(TOKEN).build()

# Agregamos el handler
app.add_handler(CommandHandler("start", start))

# Ejecutamos el bot
if __name__ == "__main__":
    print("Bot iniciado")
    app.run_polling()
