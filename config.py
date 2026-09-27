import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = "tiktok-video-no-watermark2.p.rapidapi.com"
RAPIDAPI_URL = f"https://{RAPIDAPI_HOST}/"
PORT = int(os.environ.get("PORT", 10000))
SESSION_TTL_SECONDS = 30 * 60

if not TELEGRAM_TOKEN:
    raise RuntimeError("Falta TELEGRAM_TOKEN")
if not RAPIDAPI_KEY:
    raise RuntimeError("Falta RAPIDAPI_KEY")
