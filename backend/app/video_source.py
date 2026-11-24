"""Fuente de vídeo: el único punto de la app que habla con YouTube (vía yt-dlp).

No sabe nada de Opciones de calidad ni de Descargas: solo consulta y obtiene Vídeos.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class VideoInfo:
    """Lo que la Fuente de vídeo sabe de un Vídeo tras consultarlo."""

    title: str
    thumbnail_url: str
    duration_seconds: int


class LiveVideoError(Exception):
    """El Vídeo es un directo en curso (o un estreno que aún no ha empezado)."""


class VideoUnavailableError(Exception):
    """No se puede acceder al Vídeo: privado, eliminado, con restricción de edad,
    bloqueado en la región o que requiere iniciar sesión."""


class VideoSourceError(Exception):
    """Fallo inesperado al consultar YouTube que no dice nada del Vídeo: sin conexión,
    YouTube bloqueando peticiones automáticas, o yt-dlp desactualizado (ver ADR 0003)."""


class VideoSource(Protocol):
    def get_video_info(self, video_id: str) -> VideoInfo:
        """Lanza LiveVideoError o VideoUnavailableError si el Vídeo no se puede descargar,
        y VideoSourceError si falla la consulta por cualquier otro motivo."""
        ...


# Valores de "live_status" de yt-dlp que no se pueden descargar como archivo:
# directo en curso y estreno que todavía no ha empezado.
LIVE_STATUSES = {"is_live", "is_upcoming"}


# Fragmentos de los mensajes de error de yt-dlp/YouTube que indican que el Vídeo
# no es accesible. Cualquier otro error se trata como fallo inesperado (VideoSourceError).
# Ojo: "sign in to confirm you're not a bot" NO está: es un bloqueo de YouTube, no del Vídeo.
ACCESS_ERROR_MARKERS = (
    "video unavailable",
    "this video is not available",
    "this video has been removed",
    "private video",
    "sign in to confirm your age",
    "age-restricted",
    "not available in your country",
    "blocked it in your country",
    "members-only",
    "join this channel",
    "requires payment",
    "recording is not available",
)


class YtDlpVideoSource:
    """Fuente de vídeo real, usando yt-dlp como librería."""

    def get_video_info(self, video_id: str) -> VideoInfo:
        import yt_dlp

        options = {"quiet": True, "no_warnings": True, "skip_download": True}
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                # Diccionario tal cual lo devuelve yt-dlp; aquí lo traducimos a VideoInfo.
                raw_info: dict[str, Any] = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}", download=False
                )
        except yt_dlp.utils.DownloadError as error:
            # yt-dlp usa el mismo error para todo: lo distinguimos por el mensaje.
            message = str(error).lower()
            if any(marker in message for marker in ACCESS_ERROR_MARKERS):
                raise VideoUnavailableError(str(error)) from error
            raise VideoSourceError(str(error)) from error

        if raw_info.get("is_live") or raw_info.get("live_status") in LIVE_STATUSES:
            raise LiveVideoError(video_id)
        if raw_info.get("duration") is None:
            # Sin duración no es un Vídeo normal descargable como archivo.
            raise VideoUnavailableError(video_id)

        return VideoInfo(
            title=raw_info["title"],
            thumbnail_url=raw_info["thumbnail"],
            duration_seconds=int(raw_info["duration"]),
        )
