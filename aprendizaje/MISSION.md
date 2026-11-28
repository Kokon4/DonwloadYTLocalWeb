# Mission: Arquitectura y prácticas profesionales a través de DownloadYTLocalWeb

## Why
Usar este proyecto, que funciona pero que construí casi sin decidir yo, como base para aplicar en mi trabajo las prácticas que lo sostienen: separar responsabilidades, testear sin depender de servicios externos, controlar la concurrencia, documentar decisiones y empaquetar con Docker.

## Success looks like
- Ante un cambio pedido, sé en qué pieza del proyecto va y por qué, sin mirar la documentación.
- Puedo explicar y defender cada ADR del proyecto (y cuándo NO aplicaría esa decisión).
- Escribo un test en el seam de la API con una Fuente de vídeo falsa, sin ayuda.
- Encuentro y explico una carrera entre hilos como las que aparecieron en las revisiones (doble entrega, estado que retrocede).
- Monto un Dockerfile multi-etapa con versiones fijadas para otro proyecto.
- Añado yo solo una funcionalidad nueva al proyecto (p. ej. soporte de Listas de reproducción) siguiendo el mismo flujo: diseño → spec → tickets → TDD → revisión.

## Constraints
- Sesiones largas (45 min o más), varias lecciones seguidas si va bien.
- Ya manejo Python, JavaScript/TypeScript, HTTP/JSON y Git/terminal: no hay que enseñar la sintaxis, sino el diseño.
- Aprendo sobre el código real del repo, no con ejemplos inventados.

## Out of scope
- Aprender Python, TypeScript o Vue desde cero.
- Detalles internos de yt-dlp o ffmpeg más allá de lo que usa el proyecto.
- Despliegue en internet, autenticación y escalado (la app es local por decisión).
