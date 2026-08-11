import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from flask import Flask
import threading
import os

# Buscamos el token en las variables de entorno de Render
# Si lo pruebas en tu PC, reemplaza 'TU_TOKEN_AQUI' por tu token real
TOKEN = os.environ.get('TELEGRAM_TOKEN', '8514532683:AAHjkB8o0IKo2WqgZZNB7awFdtS50WW1VQ8')
bot = telebot.TeleBot(TOKEN)
cache_enlaces = {}

# --- 1. LÓGICA DEL BOT DE TELEGRAM ---

@bot.message_handler(commands=['start', 'help'])
def enviar_bienvenida(message):
    texto = ("¡Hola! 👋 Soy un bot diseñado para descargar de TikTok.\n\n"
             "Envíame un enlace y te daré opciones para descargar el video o solo el audio.")
    bot.reply_to(message, texto)

@bot.message_handler(func=lambda message: True)
def manejar_mensajes(message):
    texto = message.text
    if 'tiktok.com' in texto:
        palabras = texto.split()
        url_tiktok = next((palabra for palabra in palabras if 'tiktok.com' in palabra), None)
        bot.reply_to(message, "Procesando enlace con RapidAPI... 🚀")
        
        # --- NUEVA CONFIGURACIÓN DE RAPIDAPI ---
        api_url = "https://tiktok-video-no-watermark2.p.rapidapi.com/user/search"
        
        # Parámetros que la API exige
        querystring = {"keywords": url_tiktok, "count": "10", "cursor": "0", "follower_count": "0", "profile_type": "0", "other_pref": "0"}
        
        # Encabezados de seguridad con tu Clave
        headers = {
            "x-rapidapi-key": "2e44da8e00msh72608e7d6c4d5b5p1cd6d1jsn4f446aab5c8e", 
            "x-rapidapi-host": "tiktok-video-no-watermark2.p.rapidapi.com"
        }
        
        try:
            # Hacemos la petición a la nueva API
            respuesta = requests.get(api_url, headers=headers, params=querystring)
            datos = respuesta.json()

            # Verificamos si la respuesta es exitosa
            # (Nota: La estructura de respuesta depende de la API específica, 
            # esta es una aproximación común, habría que ver el JSON exacto que devuelve)
            if 'data' in datos or 'videos' in datos: 
                chat_id = message.chat.id
                
                # ¡Atención aquí! Necesitaremos ver cómo esta API específica 
                # nombra sus enlaces de video y audio para guardarlos en caché.
                # Por ahora, usamos un marcador de posición.
                video_url = "URL_DEL_VIDEO" 
                audio_url = "URL_DEL_AUDIO"
                
                cache_enlaces[chat_id] = {'video': video_url, 'audio': audio_url}
                
                botones = InlineKeyboardMarkup()
                btn_video = InlineKeyboardButton("🎬 Video", callback_data="dl_video")
                btn_audio = InlineKeyboardButton("🎵 Audio", callback_data="dl_audio")
                botones.row(btn_video, btn_audio)
                
                bot.send_message(chat_id, "¿Qué deseas descargar?", reply_markup=botones)
            else:
                bot.reply_to(message, "No pude extraer el video. La API de RapidAPI devolvió un error.")
                
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


# --- 2. EL TRUCO DEL SERVIDOR WEB (FLASK) ---
app = Flask(__name__)

@app.route('/')
def index():
    return "¡El Bot de TikTok está encendido y escuchando a Telegram!"

def run_flask():
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=puerto)

# --- 3. INICIO DE AMBOS SERVICIOS ---
if __name__ == "__main__":
    # Arrancamos el servidor web en un hilo paralelo
    hilo_web = threading.Thread(target=run_flask)
    hilo_web.start()
    
    # Arrancamos el bot de Telegram
    print("Bot y Servidor Web iniciados... 🚀")
    bot.infinity_polling()
