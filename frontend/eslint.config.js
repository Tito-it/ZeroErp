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

  ...pluginOxlint.buildFromOxlintConfigFile('.oxlintrc.json'),

  skipFormatting,
])
