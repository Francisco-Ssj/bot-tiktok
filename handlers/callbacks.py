import os
import threading
import time
import requests
from services.downloader import borrar_archivo, descargar_archivo
from utils.sessions import bloquear_sesion, desbloquear_sesion, obtener_sesion

def registrar_callbacks(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith("video:") or call.data.startswith("audio:"))
    def callback_descarga(call):
        try:
            tipo, identificador = call.data.split(":", 1)
        except ValueError:
            bot.answer_callback_query(call.id, "Solicitud inválida.", show_alert=True)
            return
        sesion = obtener_sesion(identificador)
        if not sesion:
            bot.answer_callback_query(call.id, "Esta descarga expiró. Envía el TikTok nuevamente.", show_alert=True)
            return
        if sesion["chat_id"] != call.message.chat.id:
            bot.answer_callback_query(call.id, "Esta descarga no pertenece a este chat.", show_alert=True)
            return
        if not bloquear_sesion(identificador):
            bot.answer_callback_query(call.id, "Ya estoy procesando esta descarga.", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Descarga iniciada 🚀")
        try:
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        except Exception:
            pass
        threading.Thread(target=_procesar_descarga, args=(bot, call.message.chat.id, identificador, tipo), daemon=True).start()

def _procesar_descarga(bot, chat_id, identificador, tipo):
    ruta = None
    mensaje_estado = None
    try:
        sesion = obtener_sesion(identificador)
        if not sesion:
            bot.send_message(chat_id, "❌ La descarga expiró.")
            return
        if tipo == "video":
            url, extension = sesion.get("video"), ".mp4"
            mensaje_estado = bot.send_message(chat_id, "⬇️ Descargando video...")
        else:
            url, extension = sesion.get("audio"), ".mp3"
            mensaje_estado = bot.send_message(chat_id, "⬇️ Descargando audio...")
        inicio = time.time()
        ruta = descargar_archivo(url, extension)
        print(f"[DESCARGA OK] {tipo} | {round(os.path.getsize(ruta)/1024/1024, 2)} MB | {round(time.time()-inicio, 2)}s")
        bot.edit_message_text(f"📤 Enviando {tipo}...", chat_id=chat_id, message_id=mensaje_estado.message_id)
        inicio_envio = time.time()
        if tipo == "video":
            with open(ruta, "rb") as archivo:
                bot.send_video(chat_id, archivo, supports_streaming=True, timeout=600)
        else:
            with open(ruta, "rb") as archivo:
                bot.send_audio(chat_id, archivo, title="Audio de TikTok", performer="TikTok", timeout=600)
        print(f"[TELEGRAM OK] {tipo} enviado en {round(time.time()-inicio_envio, 2)}s")
        try:
            bot.delete_message(chat_id, mensaje_estado.message_id)
        except Exception:
            pass
    except requests.Timeout as error:
        print("[TIMEOUT DESCARGA]", type(error).__name__, str(error))
        bot.send_message(chat_id, "⏱️ El servidor de TikTok tardó demasiado en entregar el archivo.\n\nIntenta nuevamente.")
    except Exception as error:
        print("[ERROR DESCARGA]", type(error).__name__, str(error))
        bot.send_message(chat_id, "❌ No pude completar la descarga.\nIntenta nuevamente.")
    finally:
        borrar_archivo(ruta)
        desbloquear_sesion(identificador)
