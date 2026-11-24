"""Análisis: a partir del enlace que pega el usuario, qué Vídeo es y qué Opciones de calidad ofrece.

Es lógica de la app, no de YouTube: interpreta el enlace, pide los datos del Vídeo
a la Fuente de vídeo y decide las Opciones de calidad.
"""

from dataclasses import dataclass
from typing import Literal

from app.links import PlaylistLinkError, UnsupportedLinkError, video_id_from_link
from app.video_source import LiveVideoError, VideoSource, VideoSourceError, VideoUnavailableError

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
    default: bool = False


@dataclass(frozen=True)
class Analysis:
    video_id: str
    title: str
    thumbnail_url: str
    duration_seconds: int
    quality_options: list[QualityOption]


# El MP3 se genera al convertir, así que sus Opciones no dependen del Vídeo.
# MP3 Alta es la Opción por defecto porque la app está pensada sobre todo para música.
MP3_OPTIONS = [
    QualityOption(id="mp3-192", kind="mp3", label="MP3 · Alta (192 kbps)", default=True),
    QualityOption(id="mp3-128", kind="mp3", label="MP3 · Ligera (128 kbps)"),
]


def analyze_link(url: str, video_source: VideoSource) -> Analysis:
    try:
        video_id = video_id_from_link(url)
    except UnsupportedLinkError:
        raise AnalysisError("unsupported_link") from None
    except PlaylistLinkError:
        raise AnalysisError("playlist_not_supported") from None
    try:
        info = video_source.get_video_info(video_id)
    except LiveVideoError:
        raise AnalysisError("live_not_supported") from None
    except VideoUnavailableError:
        raise AnalysisError("video_unavailable") from None
    except VideoSourceError:
        raise AnalysisError("source_failed") from None
    return Analysis(
        video_id=video_id,
        title=info.title,
        thumbnail_url=info.thumbnail_url,
        duration_seconds=info.duration_seconds,
        quality_options=list(MP3_OPTIONS),
    )
