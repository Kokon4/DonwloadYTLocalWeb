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

export async function analyzeLink(url: string): Promise<Analysis> {
  const response = await fetch('/api/analysis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!response.ok) {
    throw new Error(`El Análisis falló (HTTP ${response.status})`)
  }
  return (await response.json()) as Analysis
}
