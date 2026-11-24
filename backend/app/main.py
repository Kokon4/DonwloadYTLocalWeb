"""API HTTP: capa fina que traduce peticiones del navegador en llamadas a la lógica de la app."""

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.analysis import AnalysisError, analyze_link
from app.downloads import DownloadError, DownloadErrorCode, DownloadManager, DownloadSnapshot
from app.video_source import VideoSource


class AnalysisRequest(BaseModel):
    url: str


class QualityOptionResponse(BaseModel):
    id: str
    kind: Literal["mp4", "mp3"]
    label: str
    default: bool


class AnalysisResponse(BaseModel):
    video_id: str
    title: str
    thumbnail_url: str
    duration_seconds: int
    quality_options: list[QualityOptionResponse]


class DownloadRequest(BaseModel):
    video_id: str
    quality_option_id: str


class DownloadQualityOption(BaseModel):
    id: str
    label: str


class DownloadResponse(BaseModel):
    id: int
    video_id: str
    title: str
    quality_option: DownloadQualityOption
    state: str
    progress: float | None
    failure_code: str | None
    file_available: bool
    created_at: datetime

    @classmethod
    def of(cls, download: DownloadSnapshot) -> "DownloadResponse":
        return cls(
            id=download.id,
            video_id=download.video_id,
            title=download.title,
            quality_option=DownloadQualityOption(
                id=download.quality_option.id, label=download.quality_option.label
            ),
            state=download.state.value,
            progress=download.progress,
            failure_code=download.failure_code,
            file_available=download.file_available,
            created_at=download.created_at,
        )


# Código HTTP de cada error de Descarga.
DOWNLOAD_ERROR_STATUS: dict[DownloadErrorCode, int] = {
    "unknown_quality_option": 422,
    "download_not_found": 404,
    "download_not_ready": 409,
    "file_already_collected": 410,
    "download_not_cancellable": 409,
    "download_not_retryable": 409,
}


def create_app(video_source: VideoSource, temp_dir: Path) -> FastAPI:
    app = FastAPI(title="DownloadYTLocalWeb")
    downloads = DownloadManager(video_source, temp_dir)

    # Todos los errores de la app responden {"code": ...}; la web elige el mensaje.
    @app.exception_handler(AnalysisError)
    def analysis_error(_: Request, error: AnalysisError) -> JSONResponse:
        # 422: el enlace no se puede analizar. 502: falló YouTube/yt-dlp, no el enlace.
        status = 502 if error.code == "source_failed" else 422
        return JSONResponse(status_code=status, content={"code": error.code})

    @app.exception_handler(DownloadError)
    def download_error(_: Request, error: DownloadError) -> JSONResponse:
        return JSONResponse(status_code=DOWNLOAD_ERROR_STATUS[error.code], content={"code": error.code})

    @app.post("/api/analysis")
    def analyze(request: AnalysisRequest) -> AnalysisResponse:
        return AnalysisResponse.model_validate(asdict(analyze_link(request.url, video_source)))

    @app.post("/api/downloads", status_code=201)
    def create_download(request: DownloadRequest) -> DownloadResponse:
        return DownloadResponse.of(downloads.create(request.video_id, request.quality_option_id))

    @app.get("/api/downloads")
    def list_downloads() -> list[DownloadResponse]:
        return [DownloadResponse.of(d) for d in downloads.list()]

    @app.get("/api/downloads/{download_id}")
    def get_download(download_id: int) -> DownloadResponse:
        return DownloadResponse.of(downloads.get(download_id))

    @app.post("/api/downloads/{download_id}/cancel")
    def cancel_download(download_id: int) -> DownloadResponse:
        return DownloadResponse.of(downloads.cancel(download_id))

    @app.post("/api/downloads/{download_id}/retry", status_code=201)
    def retry_download(download_id: int) -> DownloadResponse:
        return DownloadResponse.of(downloads.retry(download_id))

    @app.get("/api/downloads/{download_id}/file")
    def download_file(download_id: int, background: BackgroundTasks) -> FileResponse:
        path = downloads.claim_file(download_id)
        # Se borra del servidor cuando la respuesta termina de enviarse.
        background.add_task(downloads.delete_file, download_id)
        return FileResponse(path, filename=path.name, content_disposition_type="attachment")

    return app
