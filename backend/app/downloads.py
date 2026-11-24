"""Gestor de Descargas: crea Descargas, las ejecuta en segundo plano y controla sus estados.

Todo vive en memoria y en una carpeta temporal (ver ADR 0001), que se limpia sola:

- al arrancar se vacía la carpeta temporal;
- un archivo Listo que nadie recoge caduca a la hora (FILE_TTL);
- una Descarga desaparece de la lista 1 hora después de que ya no le quede nada pendiente
  (LIST_RETENTION): al terminar Fallida o Cancelada, o cuando su archivo se recoge o caduca.

Las Descargas se ejecutan en un grupo fijo de
MAX_PARALLEL_DOWNLOADS hilos: si todos están ocupados, la Descarga espera Pendiente en
una cola por orden de llegada y arranca sola cuando un hilo queda libre.

Como varios hilos tocan la misma Descarga (el que la ejecuta y los que atienden
peticiones HTTP), cada Descarga protege sus cambios con su propio lock y solo se
modifica a través de sus métodos. Hacia fuera se entregan copias (``DownloadSnapshot``)
para que nadie lea un estado a medio cambiar.
"""

import itertools
import logging
import queue
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Literal

from app.analysis import QualityOption, SourceErrorCode, analyze_video, source_error_code
from app.video_source import FetchCancelledError, FetchPhase, VideoSource


class DownloadState(StrEnum):
    """Estados de una Descarga (ver GLOSSARY.md).

    Debe coincidir con DownloadState en frontend/src/api.ts.
    """

    PENDING = "pending"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


logger = logging.getLogger(__name__)

# Cuánto espera en el servidor un archivo Listo que nadie recoge.
FILE_TTL = timedelta(hours=1)
# Cuánto sigue en la lista una Descarga a la que ya no le queda nada pendiente.
LIST_RETENTION = timedelta(hours=1)
# Cada cuánto se limpia en segundo plano (además de en cada petición a la API).
SWEEP_INTERVAL_SECONDS = 60

Clock = Callable[[], datetime]

# Cuántas Descargas avanzan a la vez: evita saturar la conexión o que YouTube limite.
MAX_PARALLEL_DOWNLOADS = 3

# Orden en el que avanza una Descarga; nunca vuelve a un estado anterior.
_ORDER = [
    DownloadState.PENDING,
    DownloadState.DOWNLOADING,
    DownloadState.CONVERTING,
    DownloadState.READY,
]
_TERMINAL = {DownloadState.READY, DownloadState.FAILED, DownloadState.CANCELLED}

# Debe coincidir con los códigos de Descarga en frontend/src/api.ts.
DownloadErrorCode = Literal[
    "unknown_quality_option",
    "download_not_found",
    "download_not_ready",
    "file_already_collected",
    "download_not_cancellable",
    "download_not_retryable",
]

# Estados desde los que se puede Reintentar (crea una Descarga nueva).
_RETRYABLE = {DownloadState.FAILED, DownloadState.CANCELLED}


# Por qué falló una Descarga. La web traduce cada código a un mensaje (los de la Fuente
# de vídeo son los mismos que en el Análisis). Debe coincidir con frontend/src/api.ts.
FailureCode = SourceErrorCode | Literal["unexpected_error"]


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
    failure_code: FailureCode | None
    file_available: bool


class Download:
    def __init__(
        self,
        id: int,
        video_id: str,
        title: str,
        quality_option: QualityOption,
        work_dir: Path,
        clock: Clock,
    ) -> None:
        self.id = id
        self.video_id = video_id
        self.title = title
        self.quality_option = quality_option
        self.work_dir = work_dir
        self._clock = clock
        self.created_at = clock()
        # Cuándo quedó Lista (para la caducidad del archivo).
        self._ready_at: datetime | None = None
        # Cuándo dejó de tener nada pendiente (para retirarla de la lista).
        self._settled_at: datetime | None = None
        self._lock = threading.Lock()
        self._state = DownloadState.PENDING
        self._progress: float | None = None
        self._failure_code: FailureCode | None = None
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
                failure_code=self._failure_code,
                file_available=self._file_available,
            )

    def start(self) -> bool:
        """Un hilo ha cogido la Descarga: deja de estar Pendiente.

        Todavía no se conoce el porcentaje (yt-dlp tarda un poco en consultar YouTube).
        Devuelve False si se canceló mientras esperaba en la cola: no hay que ejecutarla.
        """
        with self._lock:
            if self._state is not DownloadState.PENDING:
                return False
            self._state = DownloadState.DOWNLOADING
            self._progress = None
            return True

    def cancel(self) -> None:
        """Pasa a Cancelada al momento; si está en curso, la obtención abortará en cuanto pueda."""
        with self._lock:
            if self._state in _TERMINAL:
                raise DownloadError("download_not_cancellable")
            self._state = DownloadState.CANCELLED
            self._progress = None
            self._settled_at = self._clock()

    def ensure_retryable(self) -> None:
        """Solo se reintenta lo que terminó sin archivo: Fallida o Cancelada."""
        with self._lock:
            if self._state not in _RETRYABLE:
                raise DownloadError("download_not_retryable")

    def is_cancelled(self) -> bool:
        """Lo consulta la Fuente de vídeo para saber si debe abortar."""
        with self._lock:
            return self._state is DownloadState.CANCELLED

    def advance(self, phase: FetchPhase, percent: float | None) -> None:
        """Aplica un aviso de progreso. Los avisos que harían retroceder se ignoran."""
        target = DownloadState.DOWNLOADING if phase == "downloading" else DownloadState.CONVERTING
        with self._lock:
            if self._state in _TERMINAL or _ORDER.index(target) < _ORDER.index(self._state):
                return
            self._state = target
            self._progress = percent

    def mark_ready(self, file_path: Path) -> bool:
        """Devuelve False si se canceló justo antes de terminar: el archivo sobra."""
        with self._lock:
            if self._state is DownloadState.CANCELLED:
                return False
            self._state = DownloadState.READY
            self._progress = None
            self._file_path = file_path
            self._file_available = True
            self._ready_at = self._clock()
            return True

    def mark_failed(self, code: FailureCode) -> None:
        with self._lock:
            if self._state is DownloadState.CANCELLED:
                return
            self._state = DownloadState.FAILED
            self._progress = None
            self._failure_code = code
            self._settled_at = self._clock()

    def claim_file(self) -> Path:
        """Reserva el archivo para entregarlo. Solo la primera petición lo consigue."""
        with self._lock:
            if self._state is not DownloadState.READY:
                raise DownloadError("download_not_ready")
            if not self._file_available or self._file_path is None:
                raise DownloadError("file_already_collected")
            self._file_available = False
            self._settled_at = self._clock()
            return self._file_path

    def expire_file(self) -> bool:
        """Si el archivo Listo lleva FILE_TTL sin recogerse, deja de estar disponible.

        Devuelve True si acaba de caducar (hay que borrarlo del disco).
        """
        with self._lock:
            if not self._file_available or self._ready_at is None:
                return False
            expired_at = self._ready_at + FILE_TTL
            if self._clock() < expired_at:
                return False
            self._file_available = False
            # Caducó en ese momento, aunque la limpieza se haya enterado más tarde.
            self._settled_at = expired_at
            return True

    def is_past_retention(self) -> bool:
        """True si ya no le queda nada pendiente desde hace LIST_RETENTION."""
        with self._lock:
            return (
                self._settled_at is not None
                and self._clock() - self._settled_at >= LIST_RETENTION
            )


class DownloadManager:
    def __init__(self, video_source: VideoSource, temp_dir: Path, clock: Clock) -> None:
        self._video_source = video_source
        self._temp_dir = temp_dir
        self._clock = clock
        # Restos de una ejecución anterior: sus Descargas ya no existen (estado en memoria).
        # Ojo: si hay otra instancia de la app usando la misma carpeta, se borran sus archivos.
        _empty_dir(temp_dir)
        self._downloads: dict[int, Download] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        # Cola por orden de llegada; lo que espera en ella está Pendiente.
        self._queue: queue.Queue[Download] = queue.Queue()
        # Hilos "daemon": al parar la app no se espera a que terminen, y las Descargas en
        # curso y Pendientes se abandonan (ver ADR 0001).
        for number in range(1, MAX_PARALLEL_DOWNLOADS + 1):
            threading.Thread(
                target=self._work, name=f"download-worker-{number}", daemon=True
            ).start()
        threading.Thread(target=self._sweep_periodically, name="download-sweeper", daemon=True).start()

    def create(self, video_id: str, quality_option_id: str) -> DownloadSnapshot:
        """Crea una Descarga y la lanza en segundo plano.

        Se vuelve a analizar el Vídeo para conocer su título y comprobar que la Opción de
        calidad elegida existe (puede lanzar AnalysisError).
        """
        self.sweep()
        analysis = analyze_video(video_id, self._video_source)
        option = analysis.find_option(quality_option_id)
        if option is None:
            raise DownloadError("unknown_quality_option")
        return self._enqueue(video_id, analysis.title, option)

    def retry(self, download_id: int) -> DownloadSnapshot:
        """Crea una Descarga nueva con el mismo Vídeo y Opción; la original no cambia.

        No se repite el Análisis: se reutilizan el título y la Opción ya conocidos.
        """
        self.sweep()
        original = self._find(download_id)
        original.ensure_retryable()
        return self._enqueue(original.video_id, original.title, original.quality_option)

    def _enqueue(self, video_id: str, title: str, option: QualityOption) -> DownloadSnapshot:
        with self._lock:
            download_id = next(self._ids)
            download = Download(
                download_id, video_id, title, option, self._work_dir(download_id), self._clock
            )
            self._downloads[download_id] = download
        self._queue.put(download)
        return download.snapshot()

    def list(self) -> list[DownloadSnapshot]:
        """Las Descargas, de la más reciente a la más antigua."""
        self.sweep()
        with self._lock:
            downloads = sorted(self._downloads.values(), key=lambda d: d.id, reverse=True)
        return [d.snapshot() for d in downloads]

    def get(self, download_id: int) -> DownloadSnapshot:
        self.sweep()
        return self._find(download_id).snapshot()

    def claim_file(self, download_id: int) -> Path:
        """Ruta del archivo para entregarlo; a partir de aquí ya no está disponible."""
        self.sweep()
        return self._find(download_id).claim_file()

    def cancel(self, download_id: int) -> DownloadSnapshot:
        self.sweep()
        download = self._find(download_id)
        download.cancel()
        return download.snapshot()

    def delete_file(self, download_id: int) -> None:
        """Borra del servidor el archivo ya entregado (aunque la Descarga ya no esté en la lista)."""
        _delete_dir(self._work_dir(download_id))

    def _work_dir(self, download_id: int) -> Path:
        """Carpeta de trabajo de una Descarga dentro de la carpeta temporal."""
        return self._temp_dir / str(download_id)

    def sweep(self) -> None:
        """Caduca los archivos sin recoger y retira de la lista lo que ya no importa."""
        with self._lock:
            downloads = list(self._downloads.values())
        for download in downloads:
            if download.expire_file():
                _delete_dir(download.work_dir)
            if download.is_past_retention():
                with self._lock:
                    self._downloads.pop(download.id, None)
                _delete_dir(download.work_dir)

    def _sweep_periodically(self) -> None:
        """Limpia también aunque nadie use la web (p. ej. pestaña cerrada)."""
        while True:
            time.sleep(SWEEP_INTERVAL_SECONDS)
            try:
                self.sweep()
            except Exception:
                logger.exception("Falló la limpieza periódica")

    def _find(self, download_id: int) -> Download:
        with self._lock:
            download = self._downloads.get(download_id)
        if download is None:
            raise DownloadError("download_not_found")
        return download

    def _work(self) -> None:
        """Bucle de cada hilo trabajador: coge la Descarga Pendiente más antigua y la ejecuta."""
        while True:
            self._run(self._queue.get())

    def _run(self, download: Download) -> None:
        if not download.start():
            return  # se canceló mientras esperaba en la cola: no hay nada que hacer
        try:
            download.work_dir.mkdir(parents=True, exist_ok=True)
            path = self._video_source.fetch(
                download.video_id,
                download.quality_option.media_format,
                download.work_dir,
                download.advance,
                download.is_cancelled,
            )
        except FetchCancelledError:
            pass  # ya está Cancelada; solo queda borrar lo descargado
        except Exception as error:
            # La causa técnica va al log del servidor; la web explica el código al usuario.
            logger.exception("La Descarga %s falló", download.id)
            download.mark_failed(source_error_code(error) or "unexpected_error")
        else:
            if download.mark_ready(path):
                return  # Lista: el archivo se queda hasta que el navegador lo recoja
            # Se canceló justo cuando terminaba: el archivo sobra.
        # Fallida o Cancelada: fuera los archivos parciales.
        _delete_dir(download.work_dir)


def _empty_dir(directory: Path) -> None:
    """Deja la carpeta vacía (y la crea si no existe)."""
    directory.mkdir(parents=True, exist_ok=True)
    for child in directory.iterdir():
        if child.is_dir():
            _delete_dir(child)
        else:
            child.unlink(missing_ok=True)


def _delete_dir(directory: Path) -> None:
    """Borra una carpeta y todo su contenido; no falla si ya no existe."""
    shutil.rmtree(directory, ignore_errors=True)
