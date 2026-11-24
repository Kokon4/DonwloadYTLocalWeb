"""Fuente de vídeo: el único punto de la app que habla con YouTube (vía yt-dlp).

No sabe nada de Opciones de calidad ni de Descargas: solo consulta y obtiene Vídeos.
"""

import re
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
    # Resoluciones (el número de "1080p", "720p"…) en las que el Vídeo existe en H.264 con
    # audio AAC, la combinación compatible con cualquier reproductor. Es la etiqueta de
    # calidad de YouTube, no la altura en píxeles: un vídeo con bandas negras de 1920×804
    # es "1080p". La Fuente solo informa; qué se ofrece lo decide el Análisis.
    h264_resolutions: tuple[int, ...] = ()


@dataclass(frozen=True)
class Mp3Format:
    """Formato de archivo final: MP3 al bitrate indicado (solo se baja la pista de audio)."""

    bitrate_kbps: int


@dataclass(frozen=True)
class Mp4Format:
    """Formato de archivo final: MP4 con vídeo H.264 de la resolución indicada y audio AAC."""

    resolution: int


# Formatos que la Fuente de vídeo sabe producir.
MediaFormat = Mp3Format | Mp4Format


# Fase en la que está la obtención de un archivo y, si se conoce, su porcentaje.
FetchPhase = Literal["downloading", "converting"]
ProgressCallback = Callable[[FetchPhase, float | None], None]


class LiveVideoError(Exception):
    """El Vídeo es un directo en curso (o un estreno que aún no ha empezado)."""


class VideoUnavailableError(Exception):
    """No se puede acceder al Vídeo: privado, eliminado, con restricción de edad,
    bloqueado en la región o que requiere iniciar sesión."""


class FetchCancelledError(Exception):
    """La obtención se abortó porque se activó la señal de cancelación."""


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
        is_cancelled: Callable[[], bool],
    ) -> Path:
        """Obtiene el archivo final del Vídeo en ``destination_dir`` y devuelve su ruta.

        Informa del avance con ``on_progress``. El nombre del archivo es el título del
        Vídeo, saneado para el sistema de archivos. Si ``is_cancelled()`` pasa a ser
        cierto, aborta en cuanto puede con FetchCancelledError (puede dejar archivos
        parciales). Un paso de ffmpeg en marcha no se corta: se aborta al terminar.
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
            raise _classify(error) from error

        if raw_info.get("is_live") or raw_info.get("live_status") in LIVE_STATUSES:
            raise LiveVideoError(video_id)
        if raw_info.get("duration") is None:
            # Sin duración no es un Vídeo normal descargable como archivo.
            raise VideoUnavailableError(video_id)

        return VideoInfo(
            title=raw_info["title"],
            thumbnail_url=raw_info["thumbnail"],
            duration_seconds=int(raw_info["duration"]),
            h264_resolutions=_h264_resolutions(raw_info.get("formats") or []),
        )

    def fetch(
        self,
        video_id: str,
        media_format: MediaFormat,
        destination_dir: Path,
        on_progress: ProgressCallback,
        is_cancelled: Callable[[], bool],
    ) -> Path:
        import yt_dlp

        plan = _plan_for(media_format)
        finished_parts = 0

        def progress_hook(event: dict[str, Any]) -> None:
            nonlocal finished_parts
            # yt-dlp llama a este aviso muy a menudo: es el punto para abortar la descarga.
            if is_cancelled():
                raise FetchCancelledError()
            if event["status"] == "downloading":
                total = event.get("total_bytes") or event.get("total_bytes_estimate")
                done = event.get("downloaded_bytes")
                if total and done is not None:
                    # Progreso global sumando las partes, para que no vuelva a 0 entre ellas.
                    percent = (finished_parts + done / total) / plan.parts * 100
                    on_progress("downloading", round(min(percent, 100.0), 1))
                else:
                    on_progress("downloading", None)
            elif event["status"] == "finished":
                finished_parts += 1

        def postprocessor_hook(event: dict[str, Any]) -> None:
            # ffmpeg no se puede interrumpir a medias: se aborta entre un paso y el siguiente.
            if is_cancelled():
                raise FetchCancelledError()
            # La conversión de la miniatura corre antes de descargar: no es "Convirtiendo".
            if event["status"] == "started" and finished_parts >= plan.parts:
                on_progress("converting", None)

        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "format": plan.selector,
            "outtmpl": str(destination_dir / "%(title)s.%(ext)s"),
            # Nombres válidos también en Windows (sin : ? * " < > |).
            "windowsfilenames": True,
            "writethumbnail": True,
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [postprocessor_hook],
            "postprocessors": [
                *plan.postprocessors,
                # Las miniaturas de YouTube suelen ser .webp; para la carátula hace falta JPG.
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"},
                # Título y artista: usa los datos de canción de YouTube si existen,
                # si no, el título del Vídeo y el nombre del canal. Sin capítulos: añaden una
                # pista de datos que descoloca la carátula del MP4 (deja de marcarse como portada).
                {"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": False},
                {"key": "EmbedThumbnail"},
            ],
            **plan.extra_options,
        }
        # Antes de empezar: consultar YouTube ya tarda un par de segundos.
        if is_cancelled():
            raise FetchCancelledError()
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                raw_info: dict[str, Any] = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}", download=True
                )
        except Exception as error:
            # yt-dlp puede envolver la excepción lanzada desde los avisos en la suya propia.
            if is_cancelled():
                raise FetchCancelledError() from error
            if isinstance(error, yt_dlp.utils.DownloadError):
                raise _classify(error) from error
            raise
        # Cancelada durante el último paso de ffmpeg: el resultado sobra.
        if is_cancelled():
            raise FetchCancelledError()

        # Ruta del archivo final (ya convertido o unido).
        return Path(raw_info["requested_downloads"][0]["filepath"])


def _classify(error: Exception) -> VideoUnavailableError | VideoSourceError:
    """yt-dlp usa el mismo error para todo: lo distinguimos por el mensaje."""
    message = str(error).lower()
    if any(marker in message for marker in ACCESS_ERROR_MARKERS):
        return VideoUnavailableError(str(error))
    return VideoSourceError(str(error))


@dataclass(frozen=True)
class _FormatPlan:
    """Cómo pedirle a yt-dlp un formato final concreto."""

    # Selector de formatos de yt-dlp.
    selector: str
    # Cuántas partes se descargan (para calcular el progreso global).
    parts: int
    # Postprocesadores propios del formato (los comunes los añade ``fetch``).
    postprocessors: list[dict[str, Any]]
    extra_options: dict[str, Any]


def _plan_for(media_format: MediaFormat) -> _FormatPlan:
    if isinstance(media_format, Mp3Format):
        return _FormatPlan(
            # Solo la pista de audio: luego ffmpeg la convierte a MP3.
            selector="bestaudio/best",
            parts=1,
            postprocessors=[
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": str(media_format.bitrate_kbps),
                }
            ],
            extra_options={},
        )
    return _FormatPlan(
        # Vídeo H.264 con esa etiqueta de calidad ("720p", "720p60"…) + audio AAC (m4a).
        selector=f"bv*[vcodec^=avc1][format_note^={media_format.resolution}p]+ba[ext=m4a]",
        # Vídeo y audio se bajan por separado y ffmpeg los une en un MP4 sin recomprimir.
        parts=2,
        postprocessors=[],
        extra_options={"merge_output_format": "mp4"},
    )


# Etiqueta de calidad de YouTube: "1080p", "720p60", "1080p HDR"…
_QUALITY_LABEL = re.compile(r"(\d+)p")


def _h264_resolutions(formats: list[dict[str, Any]]) -> tuple[int, ...]:
    """Resoluciones en las que YouTube ofrece el vídeo en H.264 ("avc1") con audio AAC."""
    has_aac_audio = any(
        f.get("ext") == "m4a" and f.get("vcodec") == "none" for f in formats
    )
    if not has_aac_audio:
        return ()
    resolutions = set()
    for f in formats:
        if not str(f.get("vcodec") or "").startswith("avc1"):
            continue
        label = _QUALITY_LABEL.match(str(f.get("format_note") or ""))
        if label:
            resolutions.add(int(label.group(1)))
    return tuple(sorted(resolutions, reverse=True))
