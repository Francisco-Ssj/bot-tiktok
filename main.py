import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from flask import Flask
import threading
import os

# Tu Token de Telegram
TOKEN = os.environ.get('TELEGRAM_TOKEN', '8514532683:AAGBc0230C-VoXM-iPN5QbmGQcIlOkfP864')
bot = telebot.TeleBot(TOKEN)
cache_enlaces = {}

@bot.message_handler(commands=['start', 'help'])
def enviar_bienvenida(message):
    bot.reply_to(message, "¡Hola! 👋 Soy un bot diseñado para descargar de TikTok sin marca de agua.\n\nEnvíame un enlace para empezar.")

@bot.message_handler(func=lambda message: True)
def manejar_mensajes(message):
    texto = message.text
    if 'tiktok.com' in texto:
        palabras = texto.split()
        url_tiktok = next((palabra for palabra in palabras if 'tiktok.com' in palabra), None)
        bot.reply_to(message, "Procesando enlace con RapidAPI... 🚀")
        
        # --- CONFIGURACIÓN DE RAPIDAPI ---
        api_url = "https://tiktok-video-no-watermark2.p.rapidapi.com/"
        querystring = {"url": url_tiktok, "hd": "1"}
        
        # Tu llave secreta de RapidAPI
        headers = {
            "x-rapidapi-key": "2e44da8e00msh72608e7d6c4d5b5p1cd6d1jsn4f446aab5c8e",
            "x-rapidapi-host": "tiktok-video-no-watermark2.p.rapidapi.com"
        }
        
        try:
            respuesta = requests.get(api_url, headers=headers, params=querystring)
            datos = respuesta.json()
            
            if datos.get('code') == 0 and 'data' in datos:
                video_data = datos['data']
                if 'videos' in video_data:
                    video_data = video_data['videos'][0]
                
                chat_id = message.chat.id
                video_url = video_data.get('play') 
                audio_url = video_data.get('music')
                
                cache_enlaces[chat_id] = {'video': video_url, 'audio': audio_url}
                
                botones = InlineKeyboardMarkup()
                botones.row(InlineKeyboardButton("🎬 Video", callback_data="dl_video"))
                if audio_url:
                    botones.row(InlineKeyboardButton("🎵 Audio", callback_data="dl_audio"))
                
                bot.send_message(chat_id, "¿Qué deseas descargar?", reply_markup=botones)
            else:
                bot.reply_to(message, "La API no pudo extraer el video. Revisa el enlace o intenta de nuevo.")
                
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
    return "¡El Bot de TikTok está encendido y usando RapidAPI!"

def run_flask():
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=puerto)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
