"""Piezas falsas compartidas por los tests."""

import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from app.video_source import FetchPhase, MediaFormat, Mp3Format, ProgressCallback, VideoInfo

# Puntos de la obtención en los que el test puede dejar "parada" a la Fuente falsa.
PausePoint = Literal["start", "downloading", "converting"]


class FakeVideoSource:
    """Fuente de vídeo falsa controlada por el test.

    - Para cada Vídeo devuelve sus datos o lanza el error indicado.
    - ``fetch`` escribe un archivo pequeño en lugar de descargar nada:
      empieza → Descargando al 40 % → Convirtiendo → archivo (.mp3 o .mp4) listo.
    - Con ``pause_at`` cada obtención se queda parada en ese punto hasta que el test
      llame a ``release()``, que deja continuar a una sola (o a ``count``).
    - ``late_events`` son avisos de progreso extra que se emiten tras Convirtiendo
      (para comprobar que una Descarga nunca retrocede).
    """

    def __init__(
        self,
        videos: dict[str, VideoInfo | Exception],
        pause_at: PausePoint | None = None,
        fetch_error: Exception | None = None,
        late_events: Iterable[tuple[FetchPhase, float | None]] = (),
    ) -> None:
        self.videos = videos
        self.pause_at = pause_at
        self.fetch_error = fetch_error
        self.late_events = list(late_events)
        self._releases = threading.Semaphore(0)

    def release(self, count: int = 1) -> None:
        self._releases.release(count)

    def _checkpoint(self, point: PausePoint) -> None:
        if self.pause_at == point:
            assert self._releases.acquire(timeout=5), "el test no liberó la Fuente falsa"

    def get_video_info(self, video_id: str) -> VideoInfo:
        result = self.videos[video_id]
        if isinstance(result, Exception):
            raise result
        return result

    def fetch(
        self,
        video_id: str,
        media_format: MediaFormat,
        destination_dir: Path,
        on_progress: ProgressCallback,
    ) -> Path:
        self._checkpoint("start")
        on_progress("downloading", 40.0)
        self._checkpoint("downloading")
        if self.fetch_error is not None:
            raise self.fetch_error
        on_progress("converting", None)
        for phase, percent in self.late_events:
            on_progress(phase, percent)
        self._checkpoint("converting")
        info = self.get_video_info(video_id)
        if isinstance(media_format, Mp3Format):
            path = destination_dir / f"{info.title}.mp3"
            path.write_bytes(fake_mp3_bytes(video_id, media_format.bitrate_kbps))
        else:
            path = destination_dir / f"{info.title}.mp4"
            path.write_bytes(fake_mp4_bytes(video_id, media_format.resolution))
        return path


def fake_mp3_bytes(video_id: str, bitrate_kbps: int) -> bytes:
    return f"fake-mp3:{video_id}:{bitrate_kbps}".encode()


def fake_mp4_bytes(video_id: str, resolution: int) -> bytes:
    return f"fake-mp4:{video_id}:{resolution}p".encode()


SONG = VideoInfo(
    title="Artista - Canción (Official Video)",
    thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    duration_seconds=213,
)


def videoclip(*h264_resolutions: int) -> VideoInfo:
    """Un Vídeo disponible en H.264 + AAC en las resoluciones indicadas."""
    return VideoInfo(
        title="Videoclip: en directo",
        thumbnail_url="https://i.ytimg.com/vi/x/hqdefault.jpg",
        duration_seconds=200,
        h264_resolutions=h264_resolutions,
    )
