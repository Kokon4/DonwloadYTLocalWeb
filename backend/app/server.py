"""Punto de arranque real: la app con la Fuente de vídeo de yt-dlp.

Arrancar con: uvicorn app.server:app

Variables de entorno (las usa la imagen Docker):
- DOWNLOADYT_TEMP_DIR: carpeta temporal de las Descargas.
- DOWNLOADYT_FRONTEND_DIR: web compilada a servir (modo uso). Si no se indica, solo se
  sirve la API: en desarrollo la web la sirve Vite (ver ADR 0002).
"""

import os
import tempfile
from pathlib import Path

from app.main import create_app
from app.video_source import YtDlpVideoSource

# Carpeta fija, para poder limpiarla al arrancar (#9). La app la crea si no existe.
TEMP_DIR = Path(
    os.environ.get("DOWNLOADYT_TEMP_DIR") or Path(tempfile.gettempdir()) / "downloadytlocalweb"
)

_frontend_dir = os.environ.get("DOWNLOADYT_FRONTEND_DIR")
FRONTEND_DIR = Path(_frontend_dir) if _frontend_dir else None

app = create_app(video_source=YtDlpVideoSource(), temp_dir=TEMP_DIR, frontend_dir=FRONTEND_DIR)
