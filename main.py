import os
import re
import tempfile
import threading

import requests
import telebot
from flask import Flask
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


# ============================================================
# CONFIGURACIÓN
# ============================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

RAPIDAPI_HOST = "tiktok-video-no-watermark2.p.rapidapi.com"
RAPIDAPI_URL = f"https://{RAPIDAPI_HOST}/"

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "Falta la variable de entorno TELEGRAM_TOKEN"
    )

if not RAPIDAPI_KEY:
    raise RuntimeError(
        "Falta la variable de entorno RAPIDAPI_KEY"
    )


# ============================================================
# INICIALIZACIÓN
# ============================================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# Guarda temporalmente la información de cada TikTok.
# Por ahora usamos memoria. Más adelante lo mejoraremos.
cache_enlaces = {}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def extraer_url_tiktok(texto):
    """
    Busca una URL de TikTok dentro del mensaje.
    """

    if not texto:
        return None

    patron = r"https?://[^\s]+tiktok\.com/[^\s]+"

    coincidencia = re.search(
        patron,
        texto,
        flags=re.IGNORECASE
    )

    if coincidencia:
        return coincidencia.group(0)

    return None


def obtener_datos_tiktok(url_tiktok):
    """
    Consulta RapidAPI y devuelve la información
    necesaria para descargar el TikTok.
    """

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    parametros = {
        "url": url_tiktok,
        "hd": "1"
    }

    respuesta = requests.get(
        RAPIDAPI_URL,
        headers=headers,
        params=parametros,
        timeout=30
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    if datos.get("code") != 0:
        mensaje = datos.get(
            "msg",
            "RapidAPI no pudo procesar el enlace."
        )

        raise RuntimeError(mensaje)

    video_data = datos.get("data")

    if not video_data:
        raise RuntimeError(
            "RapidAPI no devolvió información del TikTok."
        )

    # Algunas respuestas pueden incluir una lista de videos.
    if isinstance(video_data, dict) and "videos" in video_data:
        videos = video_data.get("videos")

        if videos and isinstance(videos, list):
            video_data = videos[0]

    video_url = video_data.get("play")
    audio_url = video_data.get("music")

    if not video_url:
        raise RuntimeError(
            "No se encontró una URL válida para el video."
        )

    return {
        "video": video_url,
        "audio": audio_url
    }


def descargar_archivo(url, extension):
    """
    Descarga un archivo desde una URL y devuelve
    la ruta temporal.
    """

    if not url:
        raise RuntimeError(
            "No existe una URL válida para descargar."
        )

    respuesta = requests.get(
        url,
        stream=True,
        timeout=120,
        allow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36"
            )
        }
    )

    respuesta.raise_for_status()

    archivo_temporal = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=extension
    )

    try:
        for bloque in respuesta.iter_content(
            chunk_size=1024 * 1024
        ):
            if bloque:
                archivo_temporal.write(bloque)

        archivo_temporal.close()

        return archivo_temporal.name

    except Exception:
        archivo_temporal.close()

        if os.path.exists(archivo_temporal.name):
            os.remove(archivo_temporal.name)

        raise


def eliminar_archivo(ruta):
    """
    Elimina un archivo temporal si existe.
    """

    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except OSError:
            pass


# ============================================================
# COMANDOS
# ============================================================

@bot.message_handler(commands=["start"])
def comando_start(message):

    texto = (
        "👋 ¡Hola!\n\n"
        "Envíame un enlace de TikTok y podré descargarlo "
        "sin marca de agua.\n\n"
        "Puedes elegir entre:\n"
        "🎬 Video\n"
        "🎵 Audio"
    )

    bot.reply_to(message, texto)


@bot.message_handler(commands=["help"])
def comando_help(message):

    texto = (
        "📖 ¿Cómo usar el bot?\n\n"
        "1. Copia un enlace de TikTok.\n"
        "2. Envíalo a este chat.\n"
        "3. Espera a que el bot lo procese.\n"
        "4. Elige Video o Audio."
    )

    bot.reply_to(message, texto)


# ============================================================
# RECEPCIÓN DE ENLACES
# ============================================================

@bot.message_handler(
    content_types=["text"],
    func=lambda message: True
)
def manejar_mensaje(message):

    url_tiktok = extraer_url_tiktok(message.text)

    if not url_tiktok:
        bot.reply_to(
            message,
            "❌ No encontré un enlace válido de TikTok."
        )
        return

    mensaje_estado = bot.reply_to(
        message,
        "🔎 Procesando enlace..."
    )

    try:

        datos = obtener_datos_tiktok(url_tiktok)

        chat_id = message.chat.id

        cache_enlaces[chat_id] = datos

        botones = InlineKeyboardMarkup()

        botones.row(
            InlineKeyboardButton(
                "🎬 Video",
                callback_data="dl_video"
            )
        )

        if datos.get("audio"):
            botones.row(
                InlineKeyboardButton(
                    "🎵 Audio",
                    callback_data="dl_audio"
                )
            )

        bot.edit_message_text(
            "✅ TikTok encontrado.\n\n"
            "¿Qué deseas descargar?",
            chat_id=chat_id,
            message_id=mensaje_estado.message_id,
            reply_markup=botones
        )

    except requests.Timeout:

        bot.edit_message_text(
            "⏱️ La solicitud tardó demasiado.\n"
            "Intenta nuevamente.",
            chat_id=message.chat.id,
            message_id=mensaje_estado.message_id
        )

    except requests.RequestException as error:

        print(
            f"[ERROR RAPIDAPI] {type(error).__name__}: {error}"
        )

        bot.edit_message_text(
            "❌ No pude comunicarme con el servicio "
            "de descarga.\n\n"
            "Intenta nuevamente en unos segundos.",
            chat_id=message.chat.id,
            message_id=mensaje_estado.message_id
        )

    except Exception as error:

        print(
            f"[ERROR PROCESANDO TIKTOK] "
            f"{type(error).__name__}: {error}"
        )

        bot.edit_message_text(
            "❌ No pude procesar ese TikTok.\n\n"
            "Comprueba que el enlace sea válido "
            "e intenta nuevamente.",
            chat_id=message.chat.id,
            message_id=mensaje_estado.message_id
        )


# ============================================================
# BOTONES
# ============================================================

@bot.callback_query_handler(
    func=lambda call: call.data in ["dl_video", "dl_audio"]
)
def procesar_boton(call):

    chat_id = call.message.chat.id

    if chat_id not in cache_enlaces:

        bot.answer_callback_query(
            call.id,
            "La descarga expiró. Envía nuevamente el enlace.",
            show_alert=True
        )

        return

    enlaces = cache_enlaces[chat_id]

    # Respondemos inmediatamente al callback para que
    # Telegram no deje el botón cargando.
    bot.answer_callback_query(
        call.id,
        "Preparando descarga..."
    )

    ruta_archivo = None

    try:

        # ----------------------------------------------------
        # VIDEO
        # ----------------------------------------------------

        if call.data == "dl_video":

            video_url = enlaces.get("video")

            if not video_url:
                bot.send_message(
                    chat_id,
                    "❌ No encontré el video."
                )
                return

            mensaje_estado = bot.send_message(
                chat_id,
                "⬇️ Descargando video..."
            )

            ruta_archivo = descargar_archivo(
                video_url,
                ".mp4"
            )

            bot.edit_message_text(
                "📤 Enviando video...",
                chat_id=chat_id,
                message_id=mensaje_estado.message_id
            )

            with open(ruta_archivo, "rb") as video:

                bot.send_video(
                    chat_id,
                    video,
                    supports_streaming=True,
                    timeout=120
                )

            bot.delete_message(
                chat_id,
                mensaje_estado.message_id
            )

        # ----------------------------------------------------
        # AUDIO
        # ----------------------------------------------------

        elif call.data == "dl_audio":

            audio_url = enlaces.get("audio")

            if not audio_url:
                bot.send_message(
                    chat_id,
                    "❌ Este TikTok no tiene audio disponible."
                )
                return

            mensaje_estado = bot.send_message(
                chat_id,
                "⬇️ Descargando audio..."
            )

            ruta_archivo = descargar_archivo(
                audio_url,
                ".mp3"
            )

            bot.edit_message_text(
                "📤 Enviando audio...",
                chat_id=chat_id,
                message_id=mensaje_estado.message_id
            )

            with open(ruta_archivo, "rb") as audio:

                bot.send_audio(
                    chat_id,
                    audio,
                    timeout=120
                )

            bot.delete_message(
                chat_id,
                mensaje_estado.message_id
            )

    except requests.Timeout:

        bot.send_message(
            chat_id,
            "⏱️ La descarga tardó demasiado.\n"
            "Intenta nuevamente."
        )

    except requests.RequestException as error:

        print(
            f"[ERROR DESCARGA] "
            f"{type(error).__name__}: {error}"
        )

        bot.send_message(
            chat_id,
            "❌ No pude descargar el archivo desde TikTok."
        )

    except Exception as error:

        print(
            f"[ERROR ENVÍO TELEGRAM] "
            f"{type(error).__name__}: {error}"
        )

        bot.send_message(
            chat_id,
            "❌ Ocurrió un error al preparar el archivo."
        )

    finally:

        eliminar_archivo(ruta_archivo)


# ============================================================
# SERVIDOR WEB PARA RENDER
# ============================================================

@app.route("/")
def inicio():
    return {
        "status": "online",
        "service": "TikTok Telegram Bot"
    }


@app.route("/health")
def health():
    return {
        "status": "ok"
    }


def ejecutar_servidor():

    puerto = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=puerto,
        use_reloader=False
    )


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":

    print("====================================")
    print(" TikTok Telegram Bot")
    print(" Iniciando...")
    print("====================================")

    servidor = threading.Thread(
        target=ejecutar_servidor,
        daemon=True
    )

    servidor.start()

    print("[OK] Servidor web iniciado")
    print("[OK] Iniciando Telegram Bot")

    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60,
        skip_pending=True
    )
