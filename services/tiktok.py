import re
import requests
from config import RAPIDAPI_HOST, RAPIDAPI_KEY, RAPIDAPI_URL

def extraer_url_tiktok(texto):
    if not texto:
        return None
    resultado = re.search(r"https?://[^\s]*tiktok\.com/[^\s]+", texto, flags=re.IGNORECASE)
    return resultado.group(0) if resultado else None

def obtener_tiktok(url):
    respuesta = requests.get(
        RAPIDAPI_URL,
        headers={"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST},
        params={"url": url, "hd": "1"},
        timeout=(10, 45),
    )
    respuesta.raise_for_status()
    datos = respuesta.json()
    if datos.get("code") != 0:
        raise RuntimeError(datos.get("msg", "RapidAPI rechazó el enlace."))
    contenido = datos.get("data")
    if not contenido:
        raise RuntimeError("RapidAPI no devolvió información.")
    if isinstance(contenido, dict) and "videos" in contenido:
        videos = contenido.get("videos")
        if isinstance(videos, list) and videos:
            contenido = videos[0]
    video_url = contenido.get("play")
    audio_url = contenido.get("music")
    if not video_url:
        raise RuntimeError("No se encontró el video.")
    return video_url, audio_url
