// Contrato con el backend (ver la spec, issue #1). Debe coincidir con los modelos de FastAPI.

export type QualityKind = 'mp4' | 'mp3'

export interface QualityOption {
  id: string
  kind: QualityKind
  label: string
  /** La Opción que se preselecciona en la interfaz. */
  default: boolean
}

export interface Analysis {
  video_id: string
  title: string
  thumbnail_url: string
  duration_seconds: number
  quality_options: QualityOption[]
}

/**
 * Códigos de error que envía el backend como {"code": ...}. Deben coincidir con
 * AnalysisErrorCode (backend/app/analysis.py) y DownloadErrorCode (backend/app/downloads.py).
 */
export type ApiErrorCode =
  // Análisis
  | 'unsupported_link'
  | 'playlist_not_supported'
  | 'live_not_supported'
  | 'video_unavailable'
  | 'source_failed'
  // Descargas
  | 'unknown_quality_option'
  | 'download_not_found'
  | 'download_not_ready'
  | 'file_already_collected'

/** Error de la API. Sin código cuando no responde el backend (caído o error inesperado). */
export class ApiError extends Error {
  readonly code: ApiErrorCode | null

  constructor(code: ApiErrorCode | null) {
    super(code ?? 'unexpected_error')
    this.code = code
  }
}

export async function analyzeLink(url: string): Promise<Analysis> {
  let response: Response
  try {
    response = await fetch('/api/analysis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
  } catch {
    throw new ApiError(null)
  }
  if (!response.ok) throw await apiErrorFrom(response)
  return (await response.json()) as Analysis
}

/** Convierte una respuesta de error en ApiError, con su código si el backend lo envía. */
async function apiErrorFrom(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { code?: unknown }
    if (typeof body.code === 'string') return new ApiError(body.code as ApiErrorCode)
  } catch {
    // Cuerpo que no es JSON (p. ej. el proxy de Vite con el backend caído).
  }
  return new ApiError(null)
}

/** Estados de una Descarga (ver GLOSSARY.md). Debe coincidir con DownloadState en backend/app/downloads.py. */
export type DownloadState = 'pending' | 'downloading' | 'converting' | 'ready' | 'failed'

/** Estados en los que la Descarga ya no cambia. */
export const TERMINAL_STATES: readonly DownloadState[] = ['ready', 'failed']

export interface Download {
  id: number
  video_id: string
  title: string
  quality_option: { id: string; label: string }
  state: DownloadState
  /** Porcentaje 0–100 mientras se descarga; null cuando no se conoce. */
  progress: number | null
  error_message: string | null
  /** True mientras el archivo espera en el servidor a que el navegador lo recoja. */
  file_available: boolean
  created_at: string
}

/**
 * Crea una Descarga. El backend vuelve a analizar el Vídeo, así que además de
 * 'unknown_quality_option' puede fallar con los mismos códigos que el Análisis.
 */
export async function createDownload(videoId: string, qualityOptionId: string): Promise<Download> {
  let response: Response
  try {
    response = await fetch('/api/downloads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, quality_option_id: qualityOptionId }),
    })
  } catch {
    throw new ApiError(null)
  }
  if (!response.ok) throw await apiErrorFrom(response)
  return (await response.json()) as Download
}

export async function listDownloads(): Promise<Download[]> {
  const response = await fetch('/api/downloads')
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return (await response.json()) as Download[]
}

export function downloadFileUrl(download: Download): string {
  return `/api/downloads/${download.id}/file`
}
