# Arquitectura y prácticas profesionales: Recursos

Todos los enlaces comprobados el 2026-11-24.

## Knowledge

- [Article: "Hexagonal architecture" (Ports & Adapters) by Alistair Cockburn, 2005](https://alistair.cockburn.us/hexagonal-architecture/)
  El artículo original: aislar la aplicación de lo externo (UI, BD, servicios) mediante puertos y adaptadores, para poder testearla sin ellos. Use for: por qué la Fuente de vídeo es una pieza aparte y por qué los tests no necesitan YouTube.
- [Article: "Test Double" by Martin Fowler](https://martinfowler.com/bliki/TestDouble.html)
  Vocabulario de Meszaros: dummy, fake, stub, spy, mock. Use for: qué es exactamente nuestra FakeVideoSource (un *fake*).
- [Article: "Mocks Aren't Stubs" by Martin Fowler](https://martinfowler.com/articles/mocksArentStubs.html)
  Verificación de estado frente a verificación de comportamiento; TDD clásico frente a mockista. Use for: por qué nuestros tests miran solo lo observable desde la API.
- [Article: "Documenting Architecture Decisions" by Michael Nygard, 2011](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
  El texto que propuso los ADR: decisiones cortas, numeradas, en el repo. Use for: lecciones sobre ADRs.
- [Book: _A Philosophy of Software Design_ (2.ª ed.) by John Ousterhout](https://web.stanford.edu/~ouster/cgi-bin/book.php)
  Módulos profundos frente a superficiales, ocultación de información, complejidad. Use for: diseño de módulos (Gestor de Descargas, Análisis).
- [Docs: FastAPI — Testing](https://fastapi.tiangolo.com/tutorial/testing/)
  TestClient + pytest. Use for: cómo funcionan nuestros tests en el seam HTTP.
- [Docs: FastAPI — Static Files](https://fastapi.tiangolo.com/tutorial/static-files/)
  `app.mount(..., StaticFiles(...))`. Use for: cómo FastAPI sirve la web compilada en modo uso.
- [Docs: Python — threading](https://docs.python.org/3/library/threading.html)
  Thread, Lock, Event, Semaphore; el GIL. Use for: lecciones de concurrencia.
- [Docs: Python — queue](https://docs.python.org/3/library/queue.html)
  Cola segura entre hilos. Use for: la cola FIFO de Descargas Pendientes.
- [Docs: Docker — Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
  Varias etapas FROM, COPY --from, --target. Use for: la lección de Docker.

## Wisdom (Communities)

- Pendiente de buscar comunidades de alta calidad sobre diseño de software y Python (a proponer cuando surja una pregunta que requiera experiencia real).

## Gaps

- Fuente de calidad sobre máquinas de estados en código de aplicación (no teoría de autómatas).
- Fuente de calidad sobre polling frente a SSE/WebSockets.
