import os
import tempfile
import requests

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def descargar_archivo(url, extension):
    if not url:
        raise RuntimeError("No existe una URL para este archivo.")
    respuesta = requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, allow_redirects=True, timeout=(10, 300))
    respuesta.raise_for_status()
    temporal = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    try:
        for bloque in respuesta.iter_content(chunk_size=1024 * 1024):
            if bloque:
                temporal.write(bloque)
        temporal.close()
        if os.path.getsize(temporal.name) == 0:
            raise RuntimeError("El archivo descargado está vacío.")
        return temporal.name
    except Exception:
        temporal.close()
        borrar_archivo(temporal.name)
        raise

def borrar_archivo(ruta):
    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except OSError:
            pass
