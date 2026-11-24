"""API HTTP: capa fina que traduce peticiones del navegador en llamadas a la lógica de la app."""

from dataclasses import asdict
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.analysis import analyze_link
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

    @app.post("/api/analysis")
    def analyze(request: AnalysisRequest) -> AnalysisResponse:
        return AnalysisResponse.model_validate(asdict(analyze_link(request.url, video_source)))

    return app
