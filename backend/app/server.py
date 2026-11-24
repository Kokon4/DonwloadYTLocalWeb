"""Punto de arranque real: la app con la Fuente de vídeo de yt-dlp.

Arrancar con: uvicorn app.server:app
"""

import tempfile
from pathlib import Path

from app.main import create_app
from app.video_source import YtDlpVideoSource

# Carpeta fija dentro del temporal del sistema, para poder limpiarla al arrancar (#9).
TEMP_DIR = Path(tempfile.gettempdir()) / "downloadytlocalweb"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

app = create_app(video_source=YtDlpVideoSource(), temp_dir=TEMP_DIR)
