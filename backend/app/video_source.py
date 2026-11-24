"""Fuente de vídeo: el único punto de la app que habla con YouTube (vía yt-dlp).

No sabe nada de Opciones de calidad ni de Descargas: solo consulta y obtiene Vídeos.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class VideoInfo:
    """Lo que la Fuente de vídeo sabe de un Vídeo tras consultarlo."""

    title: str
    thumbnail_url: str
    duration_seconds: int


@dataclass(frozen=True)
class Mp3Format:
    """Formato de archivo final: MP3 al bitrate indicado (solo se baja la pista de audio)."""

    bitrate_kbps: int


# Formatos que la Fuente de vídeo sabe producir (el MP4 llegará en el #5).
MediaFormat = Mp3Format


# Fase en la que está la obtención de un archivo y, si se conoce, su porcentaje.
FetchPhase = Literal["downloading", "converting"]
ProgressCallback = Callable[[FetchPhase, float | None], None]


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

    def fetch(
        self,
        video_id: str,
        media_format: MediaFormat,
        destination_dir: Path,
        on_progress: ProgressCallback,
    ) -> Path:
        """Obtiene el archivo final del Vídeo en ``destination_dir`` y devuelve su ruta.

        Informa del avance con ``on_progress``. El nombre del archivo es el título del
        Vídeo, saneado para el sistema de archivos.
        """
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

    def fetch(
        self,
        video_id: str,
        media_format: MediaFormat,
        destination_dir: Path,
        on_progress: ProgressCallback,
    ) -> Path:
        import yt_dlp

        download_finished = False

        def progress_hook(event: dict[str, Any]) -> None:
            nonlocal download_finished
            if event["status"] == "downloading":
                total = event.get("total_bytes") or event.get("total_bytes_estimate")
                done = event.get("downloaded_bytes")
                percent = round(done / total * 100, 1) if total and done is not None else None
                on_progress("downloading", percent)
            elif event["status"] == "finished":
                download_finished = True

        def postprocessor_hook(event: dict[str, Any]) -> None:
            # La conversión de la miniatura corre antes de descargar: no es "Convirtiendo".
            if event["status"] == "started" and download_finished:
                on_progress("converting", None)

        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            # Solo la pista de audio: luego ffmpeg la convierte a MP3.
            "format": "bestaudio/best",
            "outtmpl": str(destination_dir / "%(title)s.%(ext)s"),
            # Nombres válidos también en Windows (sin : ? * " < > |).
            "windowsfilenames": True,
            "writethumbnail": True,
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [postprocessor_hook],
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": str(media_format.bitrate_kbps),
                },
                # Las miniaturas de YouTube suelen ser .webp; el MP3 necesita JPG para la carátula.
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"},
                # Título y artista: usa los datos de canción de YouTube si existen,
                # si no, el título del Vídeo y el nombre del canal.
                {"key": "FFmpegMetadata", "add_metadata": True},
                {"key": "EmbedThumbnail"},
            ],
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                raw_info: dict[str, Any] = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}", download=True
                )
        except yt_dlp.utils.DownloadError as error:
            raise VideoSourceError(str(error)) from error

        # Ruta final, ya convertida a MP3.
        return Path(raw_info["requested_downloads"][0]["filepath"])
