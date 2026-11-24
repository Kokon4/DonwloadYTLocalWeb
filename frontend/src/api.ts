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
 * Motivos por los que falla un Análisis: 422 (el enlace o el Vídeo) o 502 (YouTube/yt-dlp).
 * Debe coincidir con AnalysisErrorCode en backend/app/analysis.py.
 */
export type AnalysisErrorCode =
  | 'unsupported_link'
  | 'playlist_not_supported'
  | 'live_not_supported'
  | 'video_unavailable'
  | 'source_failed'

/** Error del Análisis. Sin código cuando no responde el backend (caído o error inesperado). */
export class AnalysisError extends Error {
  readonly code: AnalysisErrorCode | null

  constructor(code: AnalysisErrorCode | null) {
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
    throw new AnalysisError(null)
  }
  if (response.status === 422 || response.status === 502) {
    const body = (await response.json()) as { code?: AnalysisErrorCode }
    throw new AnalysisError(body.code ?? null)
  }
  if (!response.ok) {
    throw new AnalysisError(null)
  }
  return (await response.json()) as Analysis
}
