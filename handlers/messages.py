import requests
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.tiktok import extraer_url_tiktok, obtener_tiktok
from utils.sessions import crear_sesion

def registrar_mensajes(bot):
    @bot.message_handler(commands=["start"])
    def start(message):
        bot.reply_to(message, "👋 ¡Hola!\n\nEnvíame un enlace de TikTok y podrás descargar:\n\n🎬 Video sin marca de agua\n🎵 Audio")

    @bot.message_handler(commands=["help"])
    def help_command(message):
        bot.reply_to(message, "📖 Cómo usar el bot\n\n1. Copia un enlace de TikTok.\n2. Envíalo aquí.\n3. Elige Video o Audio.\n4. Espera a que termine la descarga.")

    @bot.message_handler(content_types=["text"], func=lambda message: True)
    def recibir_mensaje(message):
        url = extraer_url_tiktok(message.text)
        if not url:
            bot.reply_to(message, "❌ Envíame un enlace válido de TikTok.")
            return
        estado = bot.reply_to(message, "🔎 Buscando TikTok...")
        try:
            video_url, audio_url = obtener_tiktok(url)
            identificador = crear_sesion(message.chat.id, video_url, audio_url)
            teclado = InlineKeyboardMarkup()
            teclado.row(InlineKeyboardButton("🎬 Video", callback_data=f"video:{identificador}"))
            if audio_url:
                teclado.row(InlineKeyboardButton("🎵 Audio", callback_data=f"audio:{identificador}"))
            bot.edit_message_text("✅ TikTok encontrado.\n\n¿Qué deseas descargar?", chat_id=message.chat.id, message_id=estado.message_id, reply_markup=teclado)
        except requests.Timeout:
            bot.edit_message_text("⏱️ TikTok tardó demasiado en responder.\nIntenta nuevamente.", chat_id=message.chat.id, message_id=estado.message_id)
        except Exception as error:
            print("[ERROR TIKTOK]", type(error).__name__, str(error))
            bot.edit_message_text("❌ No pude procesar ese TikTok.", chat_id=message.chat.id, message_id=estado.message_id)
