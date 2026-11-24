import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// En desarrollo, Vite sirve Vue y reenvía /api al backend FastAPI (ver docs/arquitectura.md).
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
