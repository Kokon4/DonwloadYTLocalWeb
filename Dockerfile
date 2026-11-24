# Imagen para USAR la app (ver ADR 0002). Para desarrollar, ver README.md.
# Versiones fijadas (ver ADR 0003): imágenes base, librerías Python y frontend.
# Excepciones documentadas en el ADR: yt-dlp (se actualiza con un comando) y ffmpeg (viene
# de Debian trixie, la distribución de la imagen base fijada).

# --- Python base: una sola línea para cambiar de versión (la usa también update-yt-dlp) ---
FROM python:3.12.16-slim-trixie AS python-base

# --- Etapa 1: compilar la web Vue (Node solo hace falta aquí) ---
FROM node:24.22.3-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Etapa 2: imagen final con Python, ffmpeg y la web compilada ---
FROM python-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOWNLOADYT_TEMP_DIR=/tmp/downloadytlocalweb \
    DOWNLOADYT_FRONTEND_DIR=/app/frontend
# ffmpeg: convertir a MP3, unir vídeo y audio del MP4 e incrustar carátulas.
# Sin versión exacta a propósito: Debian retira las versiones antiguas al publicar parches
# de seguridad y la imagen dejaría de construirse (ver ADR 0003).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /frontend/dist ./frontend
# No ejecutar como root dentro del contenedor.
RUN useradd --create-home downloadyt
USER downloadyt
EXPOSE 8000
# Dentro del contenedor escucha en todas las interfaces; docker-compose.yml decide
# desde dónde se puede entrar (solo desde tu PC).
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
