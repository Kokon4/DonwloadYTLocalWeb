"""Gestor de Descargas: crea Descargas, las ejecuta en segundo plano y controla sus estados.

Todo vive en memoria (ver ADR 0001). Cada Descarga se ejecuta en su propio hilo; el
límite de Descargas en paralelo llegará en el #6.

Como varios hilos tocan la misma Descarga (el que la ejecuta y los que atienden
peticiones HTTP), cada Descarga protege sus cambios con su propio lock y solo se
modifica a través de sus métodos. Hacia fuera se entregan copias (``DownloadSnapshot``)
para que nadie lea un estado a medio cambiar.
"""

import itertools
import shutil
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from app.analysis import QualityOption, analyze_video
from app.video_source import FetchPhase, VideoSource


class DownloadState(StrEnum):
    """Estados de una Descarga (ver GLOSSARY.md).

    Debe coincidir con DownloadState en frontend/src/api.ts.
    """

    PENDING = "pending"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    READY = "ready"
    FAILED = "failed"


# Orden en el que avanza una Descarga; nunca vuelve a un estado anterior.
_ORDER = [
    DownloadState.PENDING,
    DownloadState.DOWNLOADING,
    DownloadState.CONVERTING,
    DownloadState.READY,
]
_TERMINAL = {DownloadState.READY, DownloadState.FAILED}

# Debe coincidir con los códigos de Descarga en frontend/src/api.ts.
DownloadErrorCode = Literal[
    "unknown_quality_option", "download_not_found", "download_not_ready", "file_already_collected"
]


class DownloadError(Exception):
    def __init__(self, code: DownloadErrorCode) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class DownloadSnapshot:
    """Foto coherente de una Descarga en un instante."""

    id: int
    video_id: str
    title: str
    quality_option: QualityOption
    created_at: datetime
    state: DownloadState
    progress: float | None
    error_message: str | None
    file_available: bool


class Download:
    def __init__(
        self, id: int, video_id: str, title: str, quality_option: QualityOption, work_dir: Path
    ) -> None:
        self.id = id
        self.video_id = video_id
        self.title = title
        self.quality_option = quality_option
        self.work_dir = work_dir
        self.created_at = datetime.now(UTC)
        self._lock = threading.Lock()
        self._state = DownloadState.PENDING
        self._progress: float | None = None
        self._error_message: str | None = None
        self._file_path: Path | None = None
        # True mientras el archivo esté en el servidor esperando a que el navegador lo recoja.
        self._file_available = False

    def snapshot(self) -> DownloadSnapshot:
        with self._lock:
            return DownloadSnapshot(
                id=self.id,
                video_id=self.video_id,
                title=self.title,
                quality_option=self.quality_option,
                created_at=self.created_at,
                state=self._state,
                progress=self._progress,
                error_message=self._error_message,
                file_available=self._file_available,
            )

    def advance(self, phase: FetchPhase, percent: float | None) -> None:
        """Aplica un aviso de progreso. Los avisos que harían retroceder se ignoran."""
        target = DownloadState.DOWNLOADING if phase == "downloading" else DownloadState.CONVERTING
        with self._lock:
            if self._state in _TERMINAL or _ORDER.index(target) < _ORDER.index(self._state):
                return
            self._state = target
            self._progress = percent

    def mark_ready(self, file_path: Path) -> None:
        with self._lock:
            self._state = DownloadState.READY
            self._progress = None
            self._file_path = file_path
            self._file_available = True

    def mark_failed(self, message: str) -> None:
        with self._lock:
            self._state = DownloadState.FAILED
            self._progress = None
            self._error_message = message

    def claim_file(self) -> Path:
        """Reserva el archivo para entregarlo. Solo la primera petición lo consigue."""
        with self._lock:
            if self._state is not DownloadState.READY:
                raise DownloadError("download_not_ready")
            if not self._file_available or self._file_path is None:
                raise DownloadError("file_already_collected")
            self._file_available = False
            return self._file_path


class DownloadManager:
    def __init__(self, video_source: VideoSource, temp_dir: Path) -> None:
        self._video_source = video_source
        self._temp_dir = temp_dir
        self._downloads: dict[int, Download] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    def create(self, video_id: str, quality_option_id: str) -> DownloadSnapshot:
        """Crea una Descarga y la lanza en segundo plano.

        Se vuelve a analizar el Vídeo para conocer su título y comprobar que la Opción de
        calidad elegida existe (puede lanzar AnalysisError).
        """
        analysis = analyze_video(video_id, self._video_source)
        option = analysis.find_option(quality_option_id)
        if option is None:
            raise DownloadError("unknown_quality_option")
        with self._lock:
            download_id = next(self._ids)
            download = Download(
                download_id, video_id, analysis.title, option, self._temp_dir / str(download_id)
            )
            self._downloads[download_id] = download
        threading.Thread(target=self._run, args=(download,), daemon=True).start()
        return download.snapshot()

    def list(self) -> list[DownloadSnapshot]:
        """Las Descargas, de la más reciente a la más antigua."""
        with self._lock:
            downloads = sorted(self._downloads.values(), key=lambda d: d.id, reverse=True)
        return [d.snapshot() for d in downloads]

    def get(self, download_id: int) -> DownloadSnapshot:
        return self._find(download_id).snapshot()

    def claim_file(self, download_id: int) -> Path:
        """Ruta del archivo para entregarlo; a partir de aquí ya no está disponible."""
        return self._find(download_id).claim_file()

    def delete_file(self, download_id: int) -> None:
        """Borra del servidor el archivo ya entregado."""
        shutil.rmtree(self._find(download_id).work_dir, ignore_errors=True)

    def _find(self, download_id: int) -> Download:
        with self._lock:
            download = self._downloads.get(download_id)
        if download is None:
            raise DownloadError("download_not_found")
        return download

    def _run(self, download: Download) -> None:
        try:
            download.work_dir.mkdir(parents=True, exist_ok=True)
            path = self._video_source.fetch(
                download.video_id,
                download.quality_option.media_format,
                download.work_dir,
                download.advance,
            )
        except Exception:
            download.mark_failed("No se pudo completar la Descarga.")
            shutil.rmtree(download.work_dir, ignore_errors=True)
            return
        download.mark_ready(path)
