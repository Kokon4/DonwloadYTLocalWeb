<script setup lang="ts">
import { ref } from 'vue'
import { analyzeLink, ApiError, createDownload, type Analysis, type Download } from './api'
import AnalysisCard from './components/AnalysisCard.vue'
import DownloadList from './components/DownloadList.vue'
import LinkForm from './components/LinkForm.vue'
import { messageFor } from './messages'
import { useDownloads } from './useDownloads'


const analysis = ref<Analysis | null>(null)
const selectedOptionId = ref('')
const analyzing = ref(false)
const error = ref<string | null>(null)
const creating = ref(false)
const { downloads, busy, track, save, cancel, retry } = useDownloads()

function errorMessage(e: unknown): string {
  return messageFor(e instanceof ApiError ? e.code : null)
}

/** Ejecuta una acción (Cancelar, Reintentar) sobre una Descarga y muestra el error si falla. */
async function runDownloadAction(
  action: (download: Download) => Promise<void>,
  download: Download,
) {
  error.value = null
  try {
    await action(download)
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function onDownload() {
  if (!analysis.value) return
  creating.value = true
  error.value = null
  try {
    track(await createDownload(analysis.value.video_id, selectedOptionId.value))
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    creating.value = false
  }
}

async function onSubmit(url: string) {
  analyzing.value = true
  error.value = null
  analysis.value = null
  try {
    const result = await analyzeLink(url)
    analysis.value = result
    // El backend decide qué Opción de calidad va preseleccionada.
    const preselected = result.quality_options.find((o) => o.default) ?? result.quality_options[0]
    selectedOptionId.value = preselected?.id ?? ''
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    analyzing.value = false
  }
}
</script>

<template>
  <main>
    <h1>Descargar de YouTube</h1>
    <LinkForm :busy="analyzing" @submit="onSubmit" />
    <p v-if="analyzing" class="status" role="status">Analizando el Vídeo…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <AnalysisCard
      v-if="analysis"
      v-model:selected-option-id="selectedOptionId"
      :analysis="analysis"
      :creating="creating"
      @download="onDownload"
    />
    <DownloadList
      :downloads="downloads"
      :busy="busy"
      @save="save"
      @cancel="runDownloadAction(cancel, $event)"
      @retry="runDownloadAction(retry, $event)"
    />
  </main>
</template>

<style scoped>
main {
  max-width: 760px;
  margin: 0 auto;
  padding: 2rem 16px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
h1 {
  margin: 0;
  color: var(--text-strong);
}
.status {
  margin: 0;
}
.error {
  margin: 0;
  color: var(--danger);
}
</style>
