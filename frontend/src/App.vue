<script setup lang="ts">
import { ref } from 'vue'
import { analyzeLink, type Analysis } from './api'
import AnalysisCard from './components/AnalysisCard.vue'
import LinkForm from './components/LinkForm.vue'

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
  } catch {
    error.value = 'No se pudo analizar el enlace. Comprueba que es un Vídeo de YouTube.'
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
