import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from flask import Flask
import threading
import os

# Configuración del Token
TOKEN = os.environ.get('TELEGRAM_TOKEN', '8514532683:AAFzZbsWs8-dDIMl01ROjjuo5TnyUL6dgL0')
bot = telebot.TeleBot(TOKEN)
cache_enlaces = {}

@bot.message_handler(func=lambda message: True)
def manejar_mensajes(message):
    texto = message.text
    if 'tiktok.com' in texto:
        palabras = texto.split()
        url_tiktok = next((palabra for palabra in palabras if 'tiktok.com' in palabra), None)
        bot.reply_to(message, "Procesando enlace con Cobalt API... 🚀")
        
        # --- CONFIGURACIÓN DE COBALT API ---
        api_url = "https://api.cobalt.tools/api/json"
        
        # Inyectamos un User-Agent para simular ser un humano usando Google Chrome
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

            # Imprimimos la respuesta en Render para diagnosticar cualquier fallo interno
            print(f"Respuesta Cobalt Video: {res_video}")
            
            if res_video.get('status') in ['stream', 'redirect', 'picker']:
                chat_id = message.chat.id
                video_url = res_video.get('url')
                audio_url = res_audio.get('url') if res_audio.get('status') in ['stream', 'redirect'] else None
                
                cache_enlaces[chat_id] = {'video': video_url, 'audio': audio_url}
                
                botones = InlineKeyboardMarkup()
                btn_video = InlineKeyboardButton("🎬 Video", callback_data="dl_video")
                botones.row(btn_video)
                
                if audio_url:
                    btn_audio = InlineKeyboardButton("🎵 Audio", callback_data="dl_audio")
                    botones.row(btn_audio)
                
                bot.send_message(chat_id, "¿Qué deseas descargar?", reply_markup=botones)
            else:
                # Extraemos el mensaje de error que arroje Cobalt
                error_msg = res_video.get('text', 'Error desconocido')
                bot.reply_to(message, f"La API no pudo extraer el video. Motivo: {error_msg}")
                
        except Exception as e:
            bot.reply_to(message, f"Error general de conexión: {e}")
    else:
        bot.reply_to(message, "Ese no parece un enlace válido de TikTok. 😅 Envíame uno para empezar.")
