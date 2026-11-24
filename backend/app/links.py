"""Interpretación de los enlaces que pega el usuario."""

import re
from urllib.parse import parse_qs, urlparse

# Dominios de YouTube aceptados. Se comparan exactos, para no aceptar cosas como
# "youtube.com.evil.example" o "notyoutube.com".
WATCH_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
SHORT_HOST = "youtu.be"

# Los identificadores de Vídeo de YouTube tienen 11 caracteres de este alfabeto.
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


class UnsupportedLinkError(Exception):
    """El enlace no apunta a un Vídeo de YouTube."""


class PlaylistLinkError(Exception):
    """El enlace es de una lista de reproducción sin un Vídeo concreto."""


def video_id_from_link(url: str) -> str:
    """Extrae el identificador del Vídeo de un enlace de YouTube.

    Se ignoran el resto de parámetros (p. ej. ``list``): solo interesa el Vídeo.
    """
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if parsed.hostname == SHORT_HOST:
        candidate = parsed.path.lstrip("/")
    elif parsed.hostname in WATCH_HOSTS:
        candidate = query.get("v", [""])[0]
        if not candidate and "list" in query:
            raise PlaylistLinkError(url)
    else:
        raise UnsupportedLinkError(url)

    if not VIDEO_ID.fullmatch(candidate):
        raise UnsupportedLinkError(url)
    return candidate
