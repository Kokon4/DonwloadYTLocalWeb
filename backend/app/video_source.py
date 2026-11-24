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


class VideoSource(Protocol):
    def get_video_info(self, video_id: str) -> VideoInfo: ...


class YtDlpVideoSource:
    """Fuente de vídeo real, usando yt-dlp como librería."""

    def get_video_info(self, video_id: str) -> VideoInfo:
        import yt_dlp

        options = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(options) as ydl:
            # Diccionario tal cual lo devuelve yt-dlp; aquí lo traducimos a VideoInfo.
            raw_info: dict[str, Any] = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
        return VideoInfo(
            title=raw_info["title"],
            thumbnail_url=raw_info["thumbnail"],
            duration_seconds=int(raw_info["duration"]),
        )
