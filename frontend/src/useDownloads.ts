import { onMounted, onUnmounted, ref } from 'vue'
import {
  cancelDownload,
  downloadFileUrl,
  listDownloads,
  retryDownload,
  TERMINAL_STATES,
  type Download,
} from './api'

const POLL_INTERVAL_MS = 1000

/**
 * Lista de Descargas del servidor, consultada por polling (ver ADR 0001).
 *
 * Mientras haya alguna Descarga sin terminar, se pregunta cada segundo. Cuando una
 * Descarga que esta página vio en curso pasa a Lista, el navegador guarda el archivo
 * automáticamente. Las que ya estaban Listas al cargar la página no se guardan solas
 * (para no repetir descargas al recargar): para esas queda el botón "Guardar".
 *
 * Solo hay una consulta en vuelo a la vez, y se descarta cualquier respuesta pedida
 * antes del último cambio local (p. ej. una Descarga recién creada), para que una
 * respuesta vieja no "borre" de la pantalla lo que acaba de pasar.
 */
export function useDownloads() {
  const downloads = ref<Download[]>([])
  const seenInProgress = new Set<number>()
  const autoSaved = new Set<number>()
  let timer: ReturnType<typeof setTimeout> | null = null
  let inFlight = false
  let refreshAgain = false
  let localChanges = 0
  let stopped = false

  async function refresh() {
    if (stopped) return
    if (inFlight) {
      refreshAgain = true
      return
    }
    inFlight = true
    const changesAtStart = localChanges
    try {
      const fresh = await listDownloads()
      if (changesAtStart === localChanges) {
        downloads.value = fresh
        handleFinished()
      } else {
        refreshAgain = true
      }
    } catch {
      // Backend no disponible: se reintenta en el siguiente ciclo.
    } finally {
      inFlight = false
    }
    if (refreshAgain) {
      refreshAgain = false
      void refresh()
    } else {
      schedule()
    }
  }

  function handleFinished() {
    for (const download of downloads.value) {
      if (!TERMINAL_STATES.includes(download.state)) {
        seenInProgress.add(download.id)
      } else if (
        download.state === 'ready' &&
        download.file_available &&
        seenInProgress.has(download.id) &&
        !autoSaved.has(download.id)
      ) {
        autoSaved.add(download.id)
        save(download)
      }
    }
  }

  /** Programa la próxima consulta si queda alguna Descarga sin terminar. */
  function schedule() {
    if (stopped) return
    if (timer) clearTimeout(timer)
    timer = null
    const anyInProgress = downloads.value.some((d) => !TERMINAL_STATES.includes(d.state))
    if (anyInProgress) timer = setTimeout(refresh, POLL_INTERVAL_MS)
  }

  /** Añade una Descarga recién creada y reactiva el polling. */
  function track(download: Download) {
    localChanges++
    downloads.value = [download, ...downloads.value.filter((d) => d.id !== download.id)]
    seenInProgress.add(download.id)
    schedule()
  }

  /** Ids de las Descargas con una acción (Cancelar, Reintentar) en vuelo: sus botones se desactivan. */
  const busy = ref(new Set<number>())

  /** Ejecuta la acción si no hay otra en vuelo para esa Descarga (evita dobles clics). */
  async function exclusive(download: Download, action: () => Promise<void>) {
    if (busy.value.has(download.id)) return
    busy.value.add(download.id)
    try {
      await action()
    } finally {
      busy.value.delete(download.id)
    }
  }

  /** Cancela una Descarga y muestra al momento su nuevo estado. Puede lanzar ApiError. */
  async function cancel(download: Download) {
    await exclusive(download, async () => {
      replaceDownload(await cancelDownload(download))
      schedule()
    })
  }

  /** Reintenta una Descarga Fallida o Cancelada: aparece una Descarga nueva. Puede lanzar ApiError. */
  async function retry(download: Download) {
    await exclusive(download, async () => track(await retryDownload(download)))
  }

  /** Sustituye una Descarga de la lista por su versión más reciente conocida. */
  function replaceDownload(updated: Download) {
    localChanges++
    downloads.value = downloads.value.map((d) => (d.id === updated.id ? updated : d))
  }

  /** Pide al navegador que guarde el archivo (como un enlace de descarga normal). */
  function save(download: Download) {
    const link = document.createElement('a')
    link.href = downloadFileUrl(download)
    link.download = ''
    document.body.appendChild(link)
    link.click()
    link.remove()
    // El servidor marca el archivo como recogido: se oculta "Guardar".
    replaceDownload({ ...download, file_available: false })
  }

  onMounted(() => void refresh())
  onUnmounted(() => {
    stopped = true
    if (timer) clearTimeout(timer)
  })

  return { downloads, busy, track, save, cancel, retry }
}
