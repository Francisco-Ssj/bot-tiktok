import threading
import telebot
from flask import Flask
from config import PORT, TELEGRAM_TOKEN
from handlers import registrar_handlers

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)
registrar_handlers(bot)

@app.route("/")
def index():
    return {"status": "online", "bot": "TikTok Limpio"}

@app.route("/health")
def health():
    return {"status": "ok"}

def ejecutar_flask():
    app.run(host="0.0.0.0", port=PORT, use_reloader=False)

if __name__ == "__main__":
    print("==============================")
    print(" TikTok Limpio")
    print("==============================")
    threading.Thread(target=ejecutar_flask, daemon=True).start()
    print("[OK] Servidor web")
    print("[OK] Telegram Bot")
    print("[OK] Esperando mensajes...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
