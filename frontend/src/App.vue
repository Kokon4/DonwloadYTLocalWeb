<script setup lang="ts">
import { ref } from 'vue'
import { AnalysisError, analyzeLink, type Analysis, type AnalysisErrorCode } from './api'
import AnalysisCard from './components/AnalysisCard.vue'
import LinkForm from './components/LinkForm.vue'

const ERROR_MESSAGES: Record<AnalysisErrorCode, string> = {
  unsupported_link: 'Ese enlace no es de un Vídeo de YouTube. Copia el enlace desde la barra del navegador o desde el botón "Compartir".',
  playlist_not_supported:
    'Ese enlace es de una lista de reproducción. Las listas no están soportadas: abre un Vídeo de la lista y copia su enlace.',
  live_not_supported:
    'Ese Vídeo es un directo en curso o un estreno que aún no ha empezado. Se podrá descargar cuando termine.',
  video_unavailable:
    'No se puede acceder a ese Vídeo: puede ser privado, estar eliminado, tener restricción de edad o no estar disponible en tu país.',
  source_failed:
    'Algo falló al consultar YouTube. Si pasa con todos los Vídeos, probablemente hay que actualizar yt-dlp.',
}
const UNEXPECTED_ERROR = 'No se pudo analizar el enlace. Comprueba que el backend está en marcha e inténtalo de nuevo.'

const analysis = ref<Analysis | null>(null)
const selectedOptionId = ref('')
const analyzing = ref(false)
const error = ref<string | null>(null)

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
    const code = e instanceof AnalysisError ? e.code : null
    error.value = code ? ERROR_MESSAGES[code] : UNEXPECTED_ERROR
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
