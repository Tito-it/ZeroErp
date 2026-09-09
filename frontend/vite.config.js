import { fileURLToPath, URL } from 'node:url'
// ⚠️ Import esplicito e non il globale `process`: la configurazione eslint da'
//    i globals di Node ai soli `scripts/**`, quindi qui `process` risulterebbe
//    non definito — e il cancello del lint lo ha preso al primo giro
//    (2026-09-09). Importarlo funziona a prescindere da come e' configurato il
//    linter, che e' meglio che allargare i globals per un file.
import process from 'node:process'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// ⭐ `VITEST` lo imposta vitest stesso: sotto test il plugin dei devtools non
//    serve (non c'e' nessun browser da ispezionare) e si porta dietro babel,
//    cioe' secondi di avvio per niente. Una riga qui evita un SECONDO file di
//    configurazione: vitest legge questo, quindi alias, plugin e risoluzione
//    sono gli stessi della build — che e' il motivo per cui si e' scelto vitest.
const inTest = !!process.env.VITEST

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    ...(inTest ? [] : [vueDevTools()]),
  ],

  // ⭐ Il PRIMO test del frontend (2026-09-09). Fino a quel giorno non esisteva
  //    nessuno strumento di test: zero file, nessuno script, nessun pacchetto.
  //    ⚠️ `environment` resta quello di node, non jsdom: qui si provano
  //    composable e JS puro, che un DOM non lo toccano. Il giorno in cui servira'
  //    montare un componente si aggiungeranno `@vue/test-utils` + `jsdom` —
  //    allora, non prima: una dipendenza messa «per dopo» resta in
  //    `package.json` senza un solo test che la usi.
  test: {
    include: ['src/**/*.{test,spec}.js'],
    reporters: ['default'],
  },
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
