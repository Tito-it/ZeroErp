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
  //    ⚠️ `environment` resta quello di NODE, ed e' il default giusto: la gran
  //    parte dei test prova composable e JS puro, che un DOM non lo toccano, e
  //    in node partono piu' in fretta.
  // ⭐ **Dal 2026-09-23 si montano anche i componenti** (`@vue/test-utils` +
  //    `jsdom`, ok di Tid): quel giorno e' arrivato dopo che TRE cantieri in
  //    una settimana — rate, filtri di lista, barra del drawer di magazzino —
  //    hanno lasciato scoperto lo stesso difetto, e i filtri ne hanno pagati
  //    due in un giorno soli (brief-fe-filtri-lista §9).
  //    ⛔ Il DOM NON si accende qui per tutti: chi ne ha bisogno lo dichiara
  //    in testa al proprio file con `// @vitest-environment jsdom`. Accenderlo
  //    globalmente rallenterebbe i test puri — che sono la maggioranza — per
  //    servire i pochi che montano, e nasconderebbe QUALI file toccano il DOM.
  //    Il presidio e' la riga stessa: si legge in cima al file che la usa.
  //    ⭐ `setupFiles`: le misure «righe per pagina» (BB `core/misurePagina`)
  //    nell'app le carica il guard del router; nei test le registra
  //    `src/core/misurePagina.setup-test.js`, prima di ogni file.
  test: {
    include: ['src/**/*.{test,spec}.js'],
    setupFiles: ['src/core/misurePagina.setup-test.js'],
    reporters: ['default'],
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  // ⭐ In sviluppo si entra SOLO da Nginx, come in produzione (2026-09-25,
  //    piano-be-fe-accessi-credenziale-e-vesti §2): il browser apre
  //    `https://<host>/`, Nginx passa `/api/` a Gunicorn e il resto a Vite.
  //    Cosi' la catena davanti al backend e' una sola (Nginx = 1 proxy fidato,
  //    `DJANGO_TRUSTED_PROXY_COUNT`), e in sviluppo si provano davvero rate
  //    limit, HTTPS e l'IP del client.
  //    ⛔ Niente `proxy` per `/api` e niente `--host`: una seconda strada
  //    Vite → Django scavalcherebbe Nginx (e Django vedrebbe una catena che in
  //    produzione non esiste). Una chiamata API arrivata a Vite deve fallire.
  server: {
    host: '127.0.0.1',
    strictPort: true,
    // Niente `ws.clientPort`: senza, il client HMR apre il websocket sull'host
    // E sulla porta della pagina, cioe' quella di Nginx. La porta d'ingresso
    // resta scritta in un posto solo, il vhost.
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
