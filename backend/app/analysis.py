"""Análisis: a partir del enlace que pega el usuario, qué Vídeo es y qué Opciones de calidad ofrece.

Es lógica de la app, no de YouTube: interpreta el enlace, pide los datos del Vídeo
a la Fuente de vídeo y decide las Opciones de calidad.
"""

from dataclasses import dataclass
from typing import Literal

from app.links import PlaylistLinkError, UnsupportedLinkError, video_id_from_link
from app.video_source import (
    LiveVideoError,
    MediaFormat,
    Mp3Format,
    Mp4Format,
    VideoSource,
    VideoSourceError,
    VideoUnavailableError,
)

# Debe coincidir con AnalysisErrorCode en frontend/src/api.ts (y sus mensajes en App.vue).
AnalysisErrorCode = Literal[
    "unsupported_link",
    "playlist_not_supported",
    "live_not_supported",
    "video_unavailable",
    "source_failed",
]


class AnalysisError(Exception):
    """El Análisis no puede continuar. El código lo usa la interfaz para elegir el mensaje."""

    def __init__(self, code: AnalysisErrorCode) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class QualityOption:
    """Una Opción de calidad que el usuario puede elegir para un Vídeo."""

    id: str
    kind: Literal["mp4", "mp3"]
    label: str
    # Qué archivo debe producir la Fuente de vídeo al elegir esta Opción.
    media_format: MediaFormat
    default: bool = False


@dataclass(frozen=True)
class Analysis:
    video_id: str
    title: str
    thumbnail_url: str
    duration_seconds: int
    quality_options: list[QualityOption]

    def find_option(self, option_id: str) -> QualityOption | None:
        return next((o for o in self.quality_options if o.id == option_id), None)


# El MP3 se genera al convertir, así que sus Opciones no dependen del Vídeo.
# MP3 Alta es la Opción por defecto porque la app está pensada sobre todo para música.
MP3_OPTIONS = [
    QualityOption(
        id="mp3-192",
        kind="mp3",
        label="MP3 · Alta (192 kbps)",
        media_format=Mp3Format(bitrate_kbps=192),
        default=True,
    ),
    QualityOption(
        id="mp3-128",
        kind="mp3",
        label="MP3 · Ligera (128 kbps)",
        media_format=Mp3Format(bitrate_kbps=128),
    ),
]


# Resoluciones MP4 que se ofrecen si el Vídeo las tiene en H.264 + AAC. Las menores (144p,
# 240p) no tienen sentido para música o entretenimiento; las mayores (1440p, 4K) no existen
# en H.264 en YouTube. Decisión del ticket #5, recogida en la spec (issue #1).
MP4_RESOLUTIONS = (1080, 720, 480, 360)


def mp4_options(h264_resolutions: tuple[int, ...]) -> list[QualityOption]:
    return [
        QualityOption(
            id=f"mp4-{resolution}",
            kind="mp4",
            label=f"MP4 · {resolution}p",
            media_format=Mp4Format(resolution=resolution),
        )
        for resolution in MP4_RESOLUTIONS
        if resolution in h264_resolutions
    ]


def analyze_link(url: str, video_source: VideoSource) -> Analysis:
    try:
        video_id = video_id_from_link(url)
    except UnsupportedLinkError:
        raise AnalysisError("unsupported_link") from None
    except PlaylistLinkError:
        raise AnalysisError("playlist_not_supported") from None
    return analyze_video(video_id, video_source)


# Códigos para los errores que puede dar la Fuente de vídeo; los usan tanto el Análisis
# como el Gestor de Descargas (para explicar por qué falló una Descarga).
SourceErrorCode = Literal["live_not_supported", "video_unavailable", "source_failed"]


def source_error_code(error: Exception) -> SourceErrorCode | None:
    """Código del error de la Fuente de vídeo, o None si no es un error de la Fuente."""
    if isinstance(error, LiveVideoError):
        return "live_not_supported"
    if isinstance(error, VideoUnavailableError):
        return "video_unavailable"
    if isinstance(error, VideoSourceError):
        return "source_failed"
    return None


def analyze_video(video_id: str, video_source: VideoSource) -> Analysis:
    try:
        info = video_source.get_video_info(video_id)
    except Exception as error:
        code = source_error_code(error)
        if code is None:
            raise
        raise AnalysisError(code) from None
    return Analysis(
        video_id=video_id,
        title=info.title,
        thumbnail_url=info.thumbnail_url,
        duration_seconds=info.duration_seconds,
        quality_options=[*MP3_OPTIONS, *mp4_options(info.h264_resolutions)],
    )
