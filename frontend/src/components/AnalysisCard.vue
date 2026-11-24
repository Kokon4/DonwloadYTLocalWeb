<script setup lang="ts">
import { computed } from 'vue'
import type { Analysis } from '../api'

const props = defineProps<{ analysis: Analysis }>()
const selectedOptionId = defineModel<string>('selectedOptionId', { required: true })

const duration = computed(() => {
  const total = props.analysis.duration_seconds
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = String(total % 60).padStart(2, '0')
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`
})
</script>

<template>
  <article class="card">
    <img :src="analysis.thumbnail_url" :alt="`Miniatura de ${analysis.title}`" />
    <div class="details">
      <h2>{{ analysis.title }}</h2>
      <p class="duration">Duración: {{ duration }}</p>
      <fieldset>
        <legend>Opción de calidad</legend>
        <label v-for="option in analysis.quality_options" :key="option.id" class="option">
          <input v-model="selectedOptionId" type="radio" name="quality" :value="option.id" />
          {{ option.label }}
        </label>
      </fieldset>
    </div>
  </article>
</template>

<style scoped>
.card {
  display: grid;
  grid-template-columns: minmax(0, 240px) 1fr;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: 8px;
}
h2 {
  margin: 0 0 0.25rem;
  font-size: 1.1rem;
  color: var(--text-strong);
}
.duration {
  margin: 0 0 0.75rem;
}
fieldset {
  border: none;
  padding: 0;
  margin: 0;
}
legend {
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--text-strong);
}
.option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.2rem 0;
}
@media (max-width: 560px) {
  .card {
    grid-template-columns: 1fr;
  }
}
</style>
