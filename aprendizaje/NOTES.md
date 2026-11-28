# Notas de enseñanza

- El usuario aceptó casi todas mis recomendaciones durante la construcción sin decidir él: lo que más necesita es **recuperación activa y decisión propia** (predecir, elegir, justificar), no releer explicaciones.
- Prefiere sesiones largas (45+ min). Cada lección puede tener varias partes, pero cada parte debe acabar con un ejercicio con respuesta comprobable.
- Usar SIEMPRE el código real del repo (rutas y nombres de verdad) y el vocabulario de `../GLOSSARY.md` del proyecto.
- Idioma: español. Términos técnicos en inglés solo cuando son el nombre estándar (seam, fake, lock), explicándolos la primera vez.

## Plan tentativo (se ajusta según los learning-records)

1. Mapa del sistema: qué pieza hace qué, puertos y adaptadores, inyección de dependencias.
2. Tests en el seam: TestClient, fakes frente a mocks, qué es un buen test, TDD rojo → verde.
3. La máquina de estados de la Descarga: invariantes ("nunca retrocede") y quién los protege.
4. Concurrencia: hilos, locks, colas; las carreras reales que encontraron las revisiones.
5. Contrato de la API: códigos de error, 409/410/422/502 y por qué el backend no envía textos.
6. Frontend: polling, respuestas viejas que pisan a las nuevas, guardias contra doble clic.
7. Reproducibilidad: versiones fijadas, Docker multi-etapa, excepciones (yt-dlp, ffmpeg).
8. El flujo de trabajo: entrevista → ADR → spec → tickets tracer-bullet → TDD → revisión en dos ejes.
