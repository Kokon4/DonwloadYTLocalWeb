"""Punto de arranque real: la app con la Fuente de vídeo de yt-dlp.

Arrancar con: uvicorn app.server:app
"""

import tempfile
from pathlib import Path

from app.main import create_app
from app.video_source import YtDlpVideoSource

# Carpeta fija dentro del temporal del sistema, para poder limpiarla al arrancar (#9).
# La app la crea si no existe.
TEMP_DIR = Path(tempfile.gettempdir()) / "downloadytlocalweb"

app = create_app(video_source=YtDlpVideoSource(), temp_dir=TEMP_DIR)
