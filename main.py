import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from flask import Flask
import threading
import os

# Buscamos el token en Render. Si quieres pegarlo manual, ponlo entre las segundas comillas.
TOKEN = os.environ.get('TELEGRAM_TOKEN', '8514532683:AAGBc0230C-VoXM-iPN5QbmGQcIlOkfP864')
bot = telebot.TeleBot(TOKEN)
cache_enlaces = {}

@bot.message_handler(commands=['start', 'help'])
def enviar_bienvenida(message):
    bot.reply_to(message, "¡Hola! 👋 Soy un bot diseñado para descargar de TikTok.\n\nEnvíame un enlace y te daré opciones para descargar el video o solo el audio.")

@bot.message_handler(func=lambda message: True)
def manejar_mensajes(message):
    texto = message.text
    if 'tiktok.com' in texto:
        palabras = texto.split()
        url_tiktok = next((palabra for palabra in palabras if 'tiktok.com' in palabra), None)
        bot.reply_to(message, "Procesando enlace con Cobalt API... 🚀")
        
        api_url = "https://api.cobalt.tools/api/json"
        
        # Simulamos ser Google Chrome para que la API no detecte que somos un bot
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        payload_video = {"url": url_tiktok}
        payload_audio = {"url": url_tiktok, "isAudioOnly": True}
        
        try:
            res_video = requests.post(api_url, headers=headers, json=payload_video).json()
            res_audio = requests.post(api_url, headers=headers, json=payload_audio).json()
            
            print(f"Respuesta Cobalt: {res_video}")
            
            if res_video.get('status') in ['stream', 'redirect', 'picker']:
                chat_id = message.chat.id
                video_url = res_video.get('url')
                audio_url = res_audio.get('url') if res_audio.get('status') in ['stream', 'redirect'] else None
                
                cache_enlaces[chat_id] = {'video': video_url, 'audio': audio_url}
                
                botones = InlineKeyboardMarkup()
                botones.row(InlineKeyboardButton("🎬 Video", callback_data="dl_video"))
                if audio_url:
                    botones.row(InlineKeyboardButton("🎵 Audio", callback_data="dl_audio"))
                
                bot.send_message(chat_id, "¿Qué deseas descargar?", reply_markup=botones)
            else:
                bot.reply_to(message, f"La API no pudo extraer el video. Motivo: {res_video.get('text', 'Error desconocido')}")
                
        except Exception as e:
            bot.reply_to(message, f"Error general de conexión: {e}")
    else:
        bot.reply_to(message, "Ese no parece un enlace válido de TikTok. 😅 Envíame uno para empezar.")

@bot.callback_query_handler(func=lambda call: True)
def procesar_boton(call):
    chat_id = call.message.chat.id
    opcion = call.data
    if chat_id not in cache_enlaces:
        bot.answer_callback_query(call.id, "La sesión expiró. Vuelve a enviar el enlace.", show_alert=True)
        return
    
    enlaces = cache_enlaces[chat_id]
    bot.answer_callback_query(call.id, "Enviando archivo... 🚀")
    try:
        if opcion == "dl_video":
            bot.send_video(chat_id, enlaces['video'])
        elif opcion == "dl_audio":
            bot.send_audio(chat_id, enlaces['audio'])
    except Exception as e:
        bot.send_message(chat_id, f"Error al enviar el archivo: {e}")

# --- SERVIDOR WEB ---
app = Flask(__name__)

@app.route('/')
def index():
    return "¡El Bot de TikTok está encendido!"

def run_flask():
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=puerto)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    print("Iniciando conexión con Telegram... 🚀")
    bot.infinity_polling()
