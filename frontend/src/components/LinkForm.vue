<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ busy: boolean }>()
const emit = defineEmits<{ submit: [url: string] }>()

const url = ref('')

function onSubmit() {
  const trimmed = url.value.trim()
  if (trimmed) emit('submit', trimmed)
}
</script>

<template>
  <form class="link-form" @submit.prevent="onSubmit">
    <label for="link" class="visually-hidden">Enlace de YouTube</label>
    <input
      id="link"
      v-model="url"
      type="text"
      inputmode="url"
      placeholder="Pega aquí el enlace de YouTube"
      autocomplete="off"
      :disabled="busy"
    />
    <button type="submit" :disabled="busy || !url.trim()">
      {{ busy ? 'Analizando…' : 'Analizar' }}
    </button>
  </form>
</template>

<style scoped>
.link-form {
  display: flex;
  gap: 0.5rem;
}
input {
  flex: 1;
  min-width: 0;
}
</style>
