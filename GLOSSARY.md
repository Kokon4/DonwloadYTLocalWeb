# DownloadYTLocalWeb

Aplicación web local para descargar vídeos individuales de YouTube como vídeo (MP4) o solo audio (MP3), eligiendo entre las calidades que el propio vídeo ofrece.

## Language

**Vídeo**:
Un único vídeo de YouTube identificado por su enlace. Las listas de reproducción no son un Vídeo y quedan fuera del alcance.
_Avoid_: Playlist, lista, URL (cuando se habla del contenido y no del enlace)

**Lista de reproducción**:
Una colección de Vídeos de YouTube. Fuera del alcance: un enlace que solo apunta a una Lista de reproducción se rechaza; si el enlace incluye un Vídeo concreto, se usa solo ese Vídeo.
_Avoid_: Lista (a secas), mix

**Análisis**:
La consulta previa de un Vídeo para conocer su título, miniatura, duración y las calidades que realmente ofrece.
_Avoid_: Preview, inspección, metadata

**Opción de calidad**:
Una combinación concreta de formato (MP4 o MP3) y calidad (resolución para MP4, bitrate para MP3) que el usuario puede elegir para un Vídeo tras su Análisis.
_Avoid_: Formato (a secas), preset, stream

**Descarga**:
El trabajo de obtener un Vídeo con una Opción de calidad concreta. Avanza por estados en segundo plano y termina entregando un único archivo al navegador.
_Avoid_: Job, tarea, trabajo, petición

### Estados de una Descarga

Una Descarga avanza siempre hacia delante y nunca vuelve a un estado anterior.

**Pendiente**: creada, esperando turno porque ya hay el máximo de Descargas en curso.
**Descargando**: obteniendo el contenido desde YouTube.
**Convirtiendo**: preparando el archivo final (conversión a MP3, unión de vídeo y audio, carátula y etiquetas).
**Lista**: el archivo está disponible para que el navegador lo recoja.
**Fallida**: terminó con un error. Reintentar crea una Descarga nueva; la Fallida no se reanuda.
_Avoid_: Error (como nombre de estado)
**Cancelada**: el usuario la detuvo antes de estar Lista.
