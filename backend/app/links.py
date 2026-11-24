"""Interpretación de los enlaces que pega el usuario."""

from urllib.parse import parse_qs, urlparse


def video_id_from_link(url: str) -> str:
    """Extrae el identificador del Vídeo de un enlace de YouTube.

    Se ignoran el resto de parámetros (p. ej. ``list``): solo interesa el Vídeo.
    """
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")
    return parse_qs(parsed.query)["v"][0]
