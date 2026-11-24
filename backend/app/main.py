"""API HTTP: capa fina que traduce peticiones del navegador en llamadas a la lógica de la app."""

from dataclasses import asdict
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.analysis import AnalysisError, analyze_link
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


def create_app(video_source: VideoSource) -> FastAPI:
    app = FastAPI(title="DownloadYTLocalWeb")

    @app.exception_handler(AnalysisError)
    def analysis_error(_: Request, error: AnalysisError) -> JSONResponse:
        # 422: el enlace no se puede analizar. 502: falló YouTube/yt-dlp, no el enlace.
        status = 502 if error.code == "source_failed" else 422
        return JSONResponse(status_code=status, content={"code": error.code})

    @app.post("/api/analysis")
    def analyze(request: AnalysisRequest) -> AnalysisResponse:
        return AnalysisResponse.model_validate(asdict(analyze_link(request.url, video_source)))

    return app
