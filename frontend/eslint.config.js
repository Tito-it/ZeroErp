import { defineConfig, globalIgnores } from 'eslint/config'
import globals from 'globals'
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import pluginOxlint from 'eslint-plugin-oxlint'
import skipFormatting from 'eslint-config-prettier/flat'

export default defineConfig([
  {
    name: 'app/files-to-lint',
    files: ['**/*.{vue,js,mjs,jsx}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),

  {
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },
  },

  {
    // Gli script in `scripts/` sono CLI di verifica eseguite da Node, non
    // codice di bundle: senza i globals Node, `process` risulta non definito.
    name: 'app/node-scripts',
    files: ['scripts/**/*.{js,mjs}'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },

  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],

  {
    // ⛔ Un nome usato nel TEMPLATE e non dichiarato nello `<script setup>`
    //    non e' un errore di compilazione: diventa `_ctx.<nome>` = undefined, e
    //    solleva nel render della prima riga che lo tocca — cioe' solo con i
    //    dati che lo raggiungono. Successo il 2026-09-17 su `LottiLista.vue`:
    //    `MANAGE_ICONS.ERRORE` senza import, lista bianca SOLO sulla scheda che
    //    aveva un lotto in ERRORE, conteggio corretto nell'etichetta accanto.
    //    Ne' la build ne' `flat/essential` lo vedono. Questa regola si':
    //    accesa il 2026-09-17 a zero segnalazioni sul codebase.
    name: 'app/template-nomi-non-dichiarati',
    files: ['**/*.vue'],
    rules: {
      'vue/no-undef-properties': 'error',
    },
  },

  // ⛔ Niente `v-html` (2026-09-26): inserisce HTML senza escape, cioe' la
  //    porta d'ingresso di uno script iniettato — e i token JWT stanno in
  //    localStorage, leggibili da quello script. Oggi le occorrenze sono ZERO:
  //    la regola le tiene tali. L'HTML che arriva dall'utente si ripulisce nel
  //    backend (`html_sanitizer_service`); un caso vero che lo richieda si
  //    discute prima, e si marca sul punto con il motivo.
  // Doc: docs/it/dev/sicurezza-e-qualita-statica.md, «Frontend».
  {
    name: 'app/no-v-html',
    files: ['**/*.vue'],
    rules: {
      'vue/no-v-html': 'error',
    },
  },

  ...pluginOxlint.buildFromOxlintConfigFile('.oxlintrc.json'),

  skipFormatting,
])
