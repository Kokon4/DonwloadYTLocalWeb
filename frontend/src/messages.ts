// Textos en español que ve el usuario. El backend solo envía códigos (ver docs/arquitectura.md).
import type { ApiErrorCode, FailureCode } from './api'

/** Mensaje para cada código de error de la API. */
export const ERROR_MESSAGES: Record<ApiErrorCode, string> = {
  unsupported_link: 'Ese enlace no es de un Vídeo de YouTube. Copia el enlace desde la barra del navegador o desde el botón "Compartir".',
  playlist_not_supported:
    'Ese enlace es de una lista de reproducción. Las listas no están soportadas: abre un Vídeo de la lista y copia su enlace.',
  live_not_supported:
    'Ese Vídeo es un directo en curso o un estreno que aún no ha empezado. Se podrá descargar cuando termine.',
  video_unavailable:
    'No se puede acceder a ese Vídeo: puede ser privado, estar eliminado, tener restricción de edad o no estar disponible en tu país.',
  source_failed:
    'Algo falló al consultar YouTube. Si pasa con todos los Vídeos, probablemente hay que actualizar yt-dlp.',
  unknown_quality_option: 'Esa Opción de calidad ya no está disponible para este Vídeo. Vuelve a analizar el enlace.',
  download_not_found: 'Esa Descarga ya no existe (puede que se haya reiniciado la app).',
  download_not_ready: 'La Descarga todavía no está Lista.',
  file_already_collected: 'El archivo de esa Descarga ya se guardó.',
  download_not_cancellable: 'Esa Descarga ya había terminado y no se puede cancelar.',
  download_not_retryable: 'Solo se pueden reintentar las Descargas Fallidas o Canceladas.',
}
/** Cuando el backend no responde o falla sin código. */
export const UNEXPECTED_ERROR = 'No se pudo completar la operación. Comprueba que el backend está en marcha e inténtalo de nuevo.'

/** Por qué falló una Descarga (campo failure_code). */
export const FAILURE_MESSAGES: Record<FailureCode, string> = {
  live_not_supported: ERROR_MESSAGES.live_not_supported,
  video_unavailable:
    'YouTube ya no permite acceder a este Vídeo (puede haberse vuelto privado o haberse eliminado).',
  source_failed: ERROR_MESSAGES.source_failed,
  unexpected_error: 'Error inesperado al preparar el archivo. Más detalles en el log del servidor.',
}

/** Mensaje para cualquier error lanzado por la API. */
export function messageFor(code: ApiErrorCode | null): string {
  return code ? ERROR_MESSAGES[code] : UNEXPECTED_ERROR
}
