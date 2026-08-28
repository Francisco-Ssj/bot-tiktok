@bot.message_handler(func=lambda message: True)
def manejar_mensajes(message):
    texto = message.text
    if 'tiktok.com' in texto:
        palabras = texto.split()
        url_tiktok = next((palabra for palabra in palabras if 'tiktok.com' in palabra), None)
        bot.reply_to(message, "Procesando enlace con Cobalt API... 🚀")
        
        # --- CONFIGURACIÓN DE COBALT API (Sin llaves, sin límites) ---
        api_url = "https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Preparamos las solicitudes para video y audio
        payload_video = {"url": url_tiktok}
        payload_audio = {"url": url_tiktok, "isAudioOnly": True}
        
        try:
            # Solicitamos los enlaces de descarga directamente
            res_video = requests.post(api_url, headers=headers, json=payload_video).json()
            res_audio = requests.post(api_url, headers=headers, json=payload_audio).json()

            # Verificamos si Cobalt pudo procesar el enlace
            if res_video.get('status') in ['stream', 'redirect', 'picker']:
                chat_id = message.chat.id
                
                # Extraemos las rutas limpias
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
                bot.reply_to(message, "La API no pudo extraer el video. Intenta con otro enlace.")
                
        except Exception as e:
            bot.reply_to(message, f"Error general de conexión: {e}")
    else:
        bot.reply_to(message, "Ese no parece un enlace válido de TikTok. 😅 Envíame uno para empezar.")
