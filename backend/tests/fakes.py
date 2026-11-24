"""Piezas falsas compartidas por los tests."""

import threading
from datetime import UTC, datetime, timedelta
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Literal

from app.video_source import (
    FetchCancelledError,
    FetchPhase,
    MediaFormat,
    Mp3Format,
    ProgressCallback,
    VideoInfo,
)

# Puntos de la obtención en los que el test puede dejar "parada" a la Fuente falsa.
PausePoint = Literal["start", "downloading", "converting"]


class FakeVideoSource:
    """Fuente de vídeo falsa controlada por el test.

    - Para cada Vídeo devuelve sus datos o lanza el error indicado.
    - ``fetch`` escribe un archivo pequeño en lugar de descargar nada:
      empieza (deja un archivo parcial) → Descargando al 40 % → Convirtiendo → archivo
      (.mp3 o .mp4) listo.
    - Si se cancela mientras está parada al empezar o descargando, aborta al momento,
      como la real. Parada en Convirtiendo NO aborta hasta que se la libera (como ffmpeg,
      que no se puede cortar a medias) y entonces descarta el resultado.
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
        fetch_error_times: int | None = None,
        fail_at: Literal["downloading", "converting"] = "downloading",
        late_events: Iterable[tuple[FetchPhase, float | None]] = (),
    ) -> None:
        self.videos = videos
        self.pause_at = pause_at
        self.fetch_error = fetch_error
        # Cuántas obtenciones fallan con ``fetch_error`` (None: todas).
        self._failures_left = fetch_error_times
        self.fail_at = fail_at
        self.late_events = list(late_events)
        self._releases = threading.Semaphore(0)

    def release(self, count: int = 1) -> None:
        self._releases.release(count)

    def _checkpoint(
        self, point: PausePoint, is_cancelled: Callable[[], bool], interruptible: bool = True
    ) -> None:
        if self.pause_at != point:
            return
        deadline = time.monotonic() + 5
        while True:
            if interruptible and is_cancelled():
                raise FetchCancelledError()
            if self._releases.acquire(timeout=0.01):
                break
            assert time.monotonic() < deadline, "el test no liberó la Fuente falsa"
        if interruptible and is_cancelled():
            # Se canceló justo mientras recibía el permiso: lo devuelve para otra obtención.
            self._releases.release()
            raise FetchCancelledError()

    def _maybe_fail(self, point: Literal["downloading", "converting"]) -> None:
        if self.fetch_error is None or self.fail_at != point or self._failures_left == 0:
            return
        if self._failures_left is not None:
            self._failures_left -= 1
        raise self.fetch_error

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
        is_cancelled: Callable[[], bool],
    ) -> Path:
        (destination_dir / "descarga.part").write_bytes(b"parcial")
        self._checkpoint("start", is_cancelled)
        on_progress("downloading", 40.0)
        self._checkpoint("downloading", is_cancelled)
        self._maybe_fail("downloading")
        on_progress("converting", None)
        self._maybe_fail("converting")
        for phase, percent in self.late_events:
            on_progress(phase, percent)
        self._checkpoint("converting", is_cancelled, interruptible=False)
        if is_cancelled():
            raise FetchCancelledError()
        info = self.get_video_info(video_id)
        if isinstance(media_format, Mp3Format):
            path = destination_dir / f"{info.title}.mp3"
            path.write_bytes(fake_mp3_bytes(video_id, media_format.bitrate_kbps))
        else:
            path = destination_dir / f"{info.title}.mp4"
            path.write_bytes(fake_mp4_bytes(video_id, media_format.resolution))
        (destination_dir / "descarga.part").unlink()
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


class FakeClock:
    """Reloj falso: el tiempo solo avanza cuando el test llama a ``advance``."""

    def __init__(self) -> None:
        self._now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, **delta: float) -> None:
        self._now += timedelta(**delta)
