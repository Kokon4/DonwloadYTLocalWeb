"""Punto de arranque real: la app con la Fuente de vídeo de yt-dlp.

Arrancar con: uvicorn app.server:app
"""

from app.main import create_app
from app.video_source import YtDlpVideoSource

app = create_app(video_source=YtDlpVideoSource())
