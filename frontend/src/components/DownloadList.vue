<script setup lang="ts">
import type { Download, DownloadState } from '../api'

defineProps<{ downloads: Download[] }>()
const emit = defineEmits<{ save: [download: Download] }>()

// Nombres de los estados tal como aparecen en GLOSSARY.md.
const STATE_LABELS: Record<DownloadState, string> = {
  pending: 'Pendiente',
  downloading: 'Descargando',
  converting: 'Convirtiendo',
  ready: 'Lista',
  failed: 'Fallida',
}
</script>

<template>
  <section v-if="downloads.length" aria-labelledby="downloads-title">
    <h2 id="downloads-title">Descargas</h2>
    <ul>
      <li v-for="download in downloads" :key="download.id" class="item">
        <div class="info">
          <p class="title">{{ download.title }}</p>
          <p class="meta">
            {{ download.quality_option.label }} ·
            <span :class="['state', download.state]">{{ STATE_LABELS[download.state] }}</span>
            <template v-if="download.state === 'downloading' && download.progress !== null">
              · {{ Math.round(download.progress) }} %
            </template>
          </p>
          <progress
            v-if="download.state === 'downloading'"
            :value="download.progress ?? undefined"
            max="100"
          />
          <p v-if="download.error_message" class="error">{{ download.error_message }}</p>
        </div>
        <button
          v-if="download.state === 'ready' && download.file_available"
          type="button"
          @click="emit('save', download)"
        >
          Guardar
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
h2 {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
  color: var(--text-strong);
}
ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.info {
  flex: 1;
  min-width: 0;
}
.title {
  margin: 0;
  color: var(--text-strong);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meta {
  margin: 0;
  font-size: 0.9rem;
}
.state.ready {
  color: var(--success);
  font-weight: 600;
}
.state.failed,
.error {
  color: var(--danger);
}
.error {
  margin: 0.25rem 0 0;
  font-size: 0.9rem;
}
progress {
  width: 100%;
  margin-top: 0.4rem;
  accent-color: var(--accent);
}
</style>
