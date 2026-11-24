# DownloadYTLocalWeb

Web local para descargar Vídeos de YouTube como MP3 o MP4, eligiendo entre las calidades que ofrece cada Vídeo.

- Cómo está construida: [docs/arquitectura.md](docs/arquitectura.md)
- Vocabulario del proyecto: [GLOSSARY.md](GLOSSARY.md)
- Decisiones de arquitectura: [docs/adr/](docs/adr/)

Funciona: Análisis, Descargas MP3 y MP4 (con carátula y etiquetas), máximo 3 Descargas a la vez, cancelar, reintentar y limpieza automática de temporales.

## Usar la app (con Docker)

Solo necesitas [Docker](https://docs.docker.com/get-docker/) con Docker Compose. No hace falta instalar Python, Node ni ffmpeg: van dentro de la imagen.

```bash
git clone https://github.com/Kokon4/DonwloadYTLocalWeb.git
cd DonwloadYTLocalWeb
docker compose up --build
```

Abre **http://localhost:8000**. Para pararla, `Ctrl+C` (o `docker compose down` si la arrancaste con `-d`, en segundo plano).

- Solo es accesible desde tu propio PC (`127.0.0.1`), no desde otros dispositivos de la red.
- La primera vez tarda unos minutos en construir la imagen; las siguientes arranca en segundos.
- Los archivos se guardan en la carpeta de descargas de tu navegador.

### Cuando YouTube deje de funcionar: actualizar yt-dlp

YouTube cambia a menudo y, cada cierto tiempo, la versión de yt-dlp deja de funcionar (Descargas Fallidas con "probablemente hay que actualizar yt-dlp"). Se arregla con:

```bash
docker compose run --rm update-yt-dlp && docker compose up --build
```

Cambia la versión fijada en `backend/requirements.txt` a la última y reconstruye la imagen. Ver [ADR 0003](docs/adr/0003-yt-dlp-fijado-con-actualizacion-en-un-paso.md).

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
