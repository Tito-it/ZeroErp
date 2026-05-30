import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        // API nativa rolldown (Vite 8): `codeSplitting` con groups (l'ex
        // `advancedChunks`, ora deprecato). Estrae SOLO i vendor sempre-eager
        // (vue/router/pinia, vue-i18n, axios): regressione-zero (gia'
        // caricati al boot) + cache a lungo termine.
        //
        // PrimeVue NON e' splittato di proposito (verificato col visualizer
        // 2026-05-29): la sua superficie condivisa da >=2 route e' ~800 KB
        // raw / ~170 KB gzip intrinseci. Estrarla in vendor-primevue (a) non
        // spegne il warning (lo sposta sul nuovo chunk >500 KB) e (b)
        // regredisce il boot di +72 KB gzip (perdita compressione di
        // vicinanza). Il warning residuo sul main e' cosmetico: i byte sono
        // la libreria UI realmente usata, non grasso. Vedi
        // docs/.../brief-fe-bundle-splitting.md.
        codeSplitting: {
          groups: [
            { name: 'vendor-core', test: /node_modules\/(vue|vue-router|pinia|@vue)\// },
            { name: 'vendor-i18n', test: /node_modules\/(vue-i18n|@intlify)\// },
            { name: 'vendor-http', test: /node_modules\/axios\// },
          ],
        },
      },
    },
  },
})
