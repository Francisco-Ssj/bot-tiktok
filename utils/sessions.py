import threading
import time
import uuid
from config import SESSION_TTL_SECONDS

_descargas = {}
_lock = threading.Lock()

def limpiar_sesiones():
    ahora = time.time()
    with _lock:
        expiradas = [i for i, datos in _descargas.items() if ahora - datos["created"] > SESSION_TTL_SECONDS]
        for identificador in expiradas:
            _descargas.pop(identificador, None)

def crear_sesion(chat_id, video_url, audio_url):
    limpiar_sesiones()
    identificador = uuid.uuid4().hex[:12]
    with _lock:
        _descargas[identificador] = {"chat_id": chat_id, "video": video_url, "audio": audio_url, "created": time.time(), "processing": False}
    return identificador

def obtener_sesion(identificador):
    limpiar_sesiones()
    with _lock:
        sesion = _descargas.get(identificador)
        return dict(sesion) if sesion else None

def bloquear_sesion(identificador):
    with _lock:
        sesion = _descargas.get(identificador)
        if not sesion or sesion["processing"]:
            return False
        sesion["processing"] = True
        return True

def desbloquear_sesion(identificador):
    with _lock:
        sesion = _descargas.get(identificador)
        if sesion:
            sesion["processing"] = False
