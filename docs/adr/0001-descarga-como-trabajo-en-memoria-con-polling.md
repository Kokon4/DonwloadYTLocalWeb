# Descarga como trabajo en segundo plano, en memoria, con polling

Una Descarga puede tardar minutos (bajada + conversión con ffmpeg), así que no se resuelve en una única petición HTTP: el backend crea una Descarga con identificador y estados (pendiente → descargando → convirtiendo → lista, o bien fallida / cancelada), la ejecuta en segundo plano con un máximo de 3 en paralelo (el resto espera como pendiente) y el navegador consulta su estado periódicamente (polling). Cuando está lista, el navegador recoge el archivo como una descarga normal. El estado vive solo en memoria y los archivos en una carpeta temporal: se borran tras ser recogidos, al pasar 1 hora sin recogerse, y al arrancar la aplicación.

## Considered Options

- **Petición síncrona**: descartada; sin progreso y expuesta a timeouts en vídeos largos.
- **SSE / WebSockets para el progreso**: descartados por ahora. Con un único usuario local el coste del polling es despreciable, y es más fácil de depurar y sobrevive a recargas de página sin lógica de reconexión. SSE queda como posible mejora.
- **SQLite para el estado**: descartado. Las Descargas son efímeras y no se quiere historial; perderlas al reiniciar es aceptable.
- **Guardar en una carpeta fija del servidor**: descartado en favor de la descarga por el navegador, que no depende de rutas del sistema ni de volúmenes Docker y funcionaría igual desde otro dispositivo.

## Consequences

- Reiniciar la aplicación cancela las Descargas en curso y vacía la lista.
- La aplicación no escala a varios procesos/réplicas (el estado no se comparte). No es un objetivo.
