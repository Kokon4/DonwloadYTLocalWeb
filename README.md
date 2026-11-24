# DownloadYTLocalWeb

Web local para descargar Vídeos de YouTube como MP3 o MP4, eligiendo entre las calidades que ofrece cada Vídeo.

- Cómo está construida: [docs/arquitectura.md](docs/arquitectura.md)
- Vocabulario del proyecto: [GLOSSARY.md](GLOSSARY.md)
- Decisiones de arquitectura: [docs/adr/](docs/adr/)

> **Estado:** en desarrollo. Ya funcionan el Análisis y las Descargas MP3 y MP4 (con carátula y etiquetas). Como máximo 3 Descargas avanzan a la vez y se pueden cancelar o reintentar. Faltan la limpieza automática y el modo uso con Docker (issues #9 y #10).

## Desarrollo

### Requisitos (Ubuntu)

```bash
sudo apt install python3.12-venv ffmpeg
```

También necesitas Python 3.12 y Node.js 24 (desarrollado con Node 24.21.0).

### Primera vez

```bash
# Backend
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# Frontend
cd ../frontend
npm install
```

### Arrancar

Hacen falta dos terminales (ver la sección "Dos formas de arrancar la app" en [docs/arquitectura.md](docs/arquitectura.md)):

```bash
# Terminal 1: backend en http://127.0.0.1:8000
cd backend
.venv/bin/uvicorn app.server:app --reload

# Terminal 2: frontend en http://localhost:5173
cd frontend
npm run dev
```

Abre **http://localhost:5173**. Vite reenvía las peticiones `/api` al backend.

### Tests y comprobación de tipos

```bash
# Backend
cd backend
.venv/bin/pytest        # tests
.venv/bin/mypy          # tipos

# Frontend
cd frontend
npx vue-tsc -b          # tipos
```

Los tests no usan internet: sustituyen la Fuente de vídeo (yt-dlp) por una falsa. Ver la sección "Cómo se prueba" en [docs/arquitectura.md](docs/arquitectura.md).
