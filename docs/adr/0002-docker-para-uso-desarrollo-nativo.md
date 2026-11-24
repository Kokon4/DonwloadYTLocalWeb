# Docker para usar la app, desarrollo nativo; un solo servidor en uso

El objetivo es poder clonar el repo en otro PC y usar la app con un par de pasos, sin instalar Python ni ffmpeg a mano. Por eso el modo uso es `docker compose up`: la imagen compila el frontend Vue y FastAPI sirve esos estáticos junto con la API desde un único proceso y puerto (mismo origen, sin CORS, sin Node en tiempo de ejecución). El desarrollo se hace fuera de Docker: Vite sirve Vue con recarga instantánea y redirige `/api` a FastAPI, es decir, dos servidores en desarrollo y uno en uso.

## Considered Options

- **Desarrollar también dentro de Docker**: descartado; añade volúmenes y configuración de recarga sin aportar valor para un proyecto personal.
- **Solo script/instrucciones de instalación**: descartado; instalar ffmpeg varía por sistema operativo (especialmente Windows).
- **Frontend y backend como dos servidores también en uso**: descartado; obliga a gestionar CORS y dos procesos para algo que es una sola app local.
