from .callbacks import registrar_callbacks
from .messages import registrar_mensajes

def registrar_handlers(bot):
    registrar_mensajes(bot)
    registrar_callbacks(bot)
