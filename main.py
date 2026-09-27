import os
import re
import time
import uuid
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
    raise RuntimeError("Falta TELEGRAM_TOKEN")

if not RAPIDAPI_KEY:
    raise RuntimeError("Falta RAPIDAPI_KEY")


bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)


# ============================================================
# MEMORIA TEMPORAL
# ============================================================

# {
#   "abc123": {
#       "video": "...",
#       "audio": "...",
#       "chat_id": 123,
#       "created": 123456789,
#       "processing": False
#   }
# }

descargas = {}

descargas_lock = threading.Lock()

SESION_DURACION = 30 * 60  # 30 minutos


# ============================================================
# UTILIDADES
# ============================================================

def extraer_url_tiktok(texto):
    if not texto:
        return None

    patron = r"https?://[^\s]*tiktok\.com/[^\s]+"

    resultado = re.search(
        patron,
        texto,
        flags=re.IGNORECASE
    )

    return resultado.group(0) if resultado else None


def limpiar_sesiones():
    ahora = time.time()

    with descargas_lock:
        expiradas = [
            identificador
            for identificador, datos in descargas.items()
            if ahora - datos["created"] > SESION_DURACION
        ]

        for identificador in expiradas:
            descargas.pop(identificador, None)


def crear_sesion(chat_id, video_url, audio_url):
    limpiar_sesiones()

    identificador = uuid.uuid4().hex[:12]

    with descargas_lock:
        descargas[identificador] = {
            "chat_id": chat_id,
            "video": video_url,
            "audio": audio_url,
            "created": time.time(),
            "processing": False
        }

    return identificador


def obtener_sesion(identificador):
    limpiar_sesiones()

    with descargas_lock:
        return descargas.get(identificador)


def bloquear_sesion(identificador):
    with descargas_lock:
        sesion = descargas.get(identificador)

        if not sesion:
            return False

        if sesion["processing"]:
            return False

        sesion["processing"] = True
        return True


def desbloquear_sesion(identificador):
    with descargas_lock:
        sesion = descargas.get(identificador)

        if sesion:
            sesion["processing"] = False


# ============================================================
# RAPIDAPI
# ============================================================

def obtener_tiktok(url):
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    parametros = {
        "url": url,
        "hd": "1"
    }

    respuesta = requests.get(
        RAPIDAPI_URL,
        headers=headers,
        params=parametros,
        timeout=(10, 45)
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    if datos.get("code") != 0:
        raise RuntimeError(
            datos.get("msg", "RapidAPI rechazó el enlace.")
        )

    contenido = datos.get("data")

    if not contenido:
        raise RuntimeError(
            "RapidAPI no devolvió información."
        )

    if isinstance(contenido, dict) and "videos" in contenido:
        videos = contenido.get("videos")

        if isinstance(videos, list) and videos:
            contenido = videos[0]

    video_url = contenido.get("play")
    audio_url = contenido.get("music")

    if not video_url:
        raise RuntimeError(
            "No se encontró el video."
        )

    return video_url, audio_url


# ============================================================
# DESCARGA DE ARCHIVOS
# ============================================================

def descargar_archivo(url, extension):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36"
        )
    }

    # 10 segundos para conectar.
    # Hasta 5 minutos esperando datos.
    respuesta = requests.get(
        url,
        headers=headers,
        stream=True,
        allow_redirects=True,
        timeout=(10, 300)
    )

    respuesta.raise_for_status()

    temporal = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=extension
    )

    try:
        for bloque in respuesta.iter_content(
            chunk_size=1024 * 1024
        ):
            if bloque:
                temporal.write(bloque)

        temporal.close()

        tamaño = os.path.getsize(temporal.name)

        if tamaño == 0:
            raise RuntimeError(
                "El archivo descargado está vacío."
            )

        return temporal.name

    except Exception:
        temporal.close()

        if os.path.exists(temporal.name):
            os.remove(temporal.name)

        raise


def borrar_archivo(ruta):
    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except OSError:
            pass


# ============================================================
# COMANDOS
# ============================================================

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "👋 ¡Hola!\n\n"
        "Envíame un enlace de TikTok y podrás descargar:\n\n"
        "🎬 Video sin marca de agua\n"
        "🎵 Audio"
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.reply_to(
        message,
        "📖 Cómo usar el bot\n\n"
        "1. Copia un enlace de TikTok.\n"
        "2. Envíalo aquí.\n"
        "3. Elige Video o Audio.\n"
        "4. Espera a que termine la descarga."
    )


# ============================================================
# MENSAJES
# ============================================================

@bot.message_handler(
    content_types=["text"],
    func=lambda message: True
)
def recibir_mensaje(message):
    url = extraer_url_tiktok(message.text)

    if not url:
        bot.reply_to(
            message,
            "❌ Envíame un enlace válido de TikTok."
        )
        return

    estado = bot.reply_to(
        message,
        "🔎 Buscando TikTok..."
    )

    try:
        video_url, audio_url = obtener_tiktok(url)

        identificador = crear_sesion(
            message.chat.id,
            video_url,
            audio_url
        )

        teclado = InlineKeyboardMarkup()

        teclado.row(
            InlineKeyboardButton(
                "🎬 Video",
                callback_data=f"video:{identificador}"
            )
        )

        if audio_url:
            teclado.row(
                InlineKeyboardButton(
                    "🎵 Audio",
                    callback_data=f"audio:{identificador}"
                )
            )

        bot.edit_message_text(
            "✅ TikTok encontrado.\n\n"
            "¿Qué deseas descargar?",
            chat_id=message.chat.id,
            message_id=estado.message_id,
            reply_markup=teclado
        )

    except requests.Timeout:
        bot.edit_message_text(
            "⏱️ TikTok tardó demasiado en responder.\n"
            "Intenta nuevamente.",
            chat_id=message.chat.id,
            message_id=estado.message_id
        )

    except Exception as error:
        print(
            "[ERROR TIKTOK]",
            type(error).__name__,
            str(error)
        )

        bot.edit_message_text(
            "❌ No pude procesar ese TikTok.",
            chat_id=message.chat.id,
            message_id=estado.message_id
        )


# ============================================================
# CALLBACKS
# ============================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data.startswith("video:")
        or call.data.startswith("audio:")
)
def callback_descarga(call):
    try:
        tipo, identificador = call.data.split(":", 1)
    except ValueError:
        bot.answer_callback_query(
            call.id,
            "Solicitud inválida.",
            show_alert=True
        )
        return

    sesion = obtener_sesion(identificador)

    if not sesion:
        bot.answer_callback_query(
            call.id,
            "Esta descarga expiró. Envía el TikTok nuevamente.",
            show_alert=True
        )
        return

    if sesion["chat_id"] != call.message.chat.id:
        bot.answer_callback_query(
            call.id,
            "Esta descarga no pertenece a este chat.",
            show_alert=True
        )
        return

    if not bloquear_sesion(identificador):
        bot.answer_callback_query(
            call.id,
            "Ya estoy procesando esta descarga.",
            show_alert=True
        )
        return

    bot.answer_callback_query(
        call.id,
        "Descarga iniciada 🚀"
    )

    # Quitamos los botones inmediatamente.
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )
    except Exception:
        pass

    hilo = threading.Thread(
        target=procesar_descarga,
        args=(
            call.message.chat.id,
            identificador,
            tipo
        ),
        daemon=True
    )

    hilo.start()


# ============================================================
# PROCESAMIENTO EN SEGUNDO PLANO
# ============================================================

def procesar_descarga(
    chat_id,
    identificador,
    tipo
):
    ruta = None
    mensaje_estado = None

    try:
        sesion = obtener_sesion(identificador)

        if not sesion:
            bot.send_message(
                chat_id,
                "❌ La descarga expiró."
            )
            return

        if tipo == "video":
            url = sesion.get("video")
            extension = ".mp4"

            mensaje_estado = bot.send_message(
                chat_id,
                "⬇️ Descargando video..."
            )

        else:
            url = sesion.get("audio")
            extension = ".mp3"

            mensaje_estado = bot.send_message(
                chat_id,
                "⬇️ Descargando audio..."
            )

        if not url:
            raise RuntimeError(
                "No existe una URL para este archivo."
            )

        inicio = time.time()

        ruta = descargar_archivo(
            url,
            extension
        )

        tiempo_descarga = round(
            time.time() - inicio,
            2
        )

        tamaño_mb = round(
            os.path.getsize(ruta)
            / 1024
            / 1024,
            2
        )

        print(
            f"[DESCARGA OK] "
            f"{tipo} | "
            f"{tamaño_mb} MB | "
            f"{tiempo_descarga}s"
        )

        bot.edit_message_text(
            f"📤 Enviando {tipo}...",
            chat_id=chat_id,
            message_id=mensaje_estado.message_id
        )

        inicio_envio = time.time()

        if tipo == "video":
            with open(ruta, "rb") as archivo:
                bot.send_video(
                    chat_id,
                    archivo,
                    supports_streaming=True,
                    timeout=600
                )

        else:
            with open(ruta, "rb") as archivo:
                bot.send_audio(
                    chat_id,
                    archivo,
                    title="Audio de TikTok",
                    performer="TikTok",
                    timeout=600
                )

        tiempo_envio = round(
            time.time() - inicio_envio,
            2
        )

        print(
            f"[TELEGRAM OK] "
            f"{tipo} enviado en "
            f"{tiempo_envio}s"
        )

        try:
            bot.delete_message(
                chat_id,
                mensaje_estado.message_id
            )
        except Exception:
            pass

    except requests.Timeout as error:
        print(
            "[TIMEOUT DESCARGA]",
            type(error).__name__,
            str(error)
        )

        bot.send_message(
            chat_id,
            "⏱️ El servidor de TikTok tardó demasiado "
            "en entregar el archivo.\n\n"
            "Intenta nuevamente."
        )

    except Exception as error:
        print(
            "[ERROR DESCARGA]",
            type(error).__name__,
            str(error)
        )

        bot.send_message(
            chat_id,
            "❌ No pude completar la descarga.\n"
            "Intenta nuevamente."
        )

    finally:
        borrar_archivo(ruta)
        desbloquear_sesion(identificador)


# ============================================================
# RENDER / FLASK
# ============================================================

@app.route("/")
def index():
    return {
        "status": "online",
        "bot": "TikTok Limpio"
    }


@app.route("/health")
def health():
    return {
        "status": "ok"
    }


def ejecutar_flask():
    puerto = int(
        os.environ.get("PORT", 10000)
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
    print("==============================")
    print(" TikTok Limpio")
    print("==============================")

    servidor = threading.Thread(
        target=ejecutar_flask,
        daemon=True
    )

    servidor.start()

    print("[OK] Servidor web")
    print("[OK] Telegram Bot")
    print("[OK] Esperando mensajes...")

    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60,
        skip_pending=True
    )
