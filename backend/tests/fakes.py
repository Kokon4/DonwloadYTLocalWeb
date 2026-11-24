"""Piezas falsas compartidas por los tests."""

import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from app.video_source import FetchPhase, MediaFormat, ProgressCallback, VideoInfo

# Puntos de la obtención en los que el test puede dejar "parada" a la Fuente falsa.
PausePoint = Literal["start", "downloading", "converting"]


class FakeVideoSource:
    """Fuente de vídeo falsa controlada por el test.

    - Para cada Vídeo devuelve sus datos o lanza el error indicado.
    - ``fetch`` escribe un archivo pequeño en lugar de descargar nada:
      empieza → Descargando al 40 % → Convirtiendo → archivo listo.
    - Con ``pause_at`` la obtención se queda parada en ese punto hasta que el test
      llame a ``release()``.
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
        self._released = threading.Event()

    def release(self) -> None:
        self._released.set()

    def _checkpoint(self, point: PausePoint) -> None:
        if self.pause_at == point:
            assert self._released.wait(timeout=5), "el test no liberó la Fuente falsa"

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
        path = destination_dir / f"{info.title}.mp3"
        path.write_bytes(fake_mp3_bytes(video_id, media_format.bitrate_kbps))
        return path


def fake_mp3_bytes(video_id: str, bitrate_kbps: int) -> bytes:
    return f"fake-mp3:{video_id}:{bitrate_kbps}".encode()


SONG = VideoInfo(
    title="Artista - Canción (Official Video)",
    thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    duration_seconds=213,
)
