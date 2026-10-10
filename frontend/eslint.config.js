import { defineConfig, globalIgnores } from 'eslint/config'
import globals from 'globals'
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import pluginOxlint from 'eslint-plugin-oxlint'
import skipFormatting from 'eslint-config-prettier/flat'
import { readFileSync } from 'node:fs'

// ⛔ I componenti PrimeVue che hanno un wrapper nostro non si importano
//    direttamente (2026-10-03, decisione di Tid). Il lint li ferma nell'editor,
//    mentre si scrive: la regola la verifica lo strumento, non la memoria di chi
//    scrive. `sedi` = i soli file che lo possono importare, esentati per
//    configurazione e non con un commento. Per la DataTable le sedi sono i
//    componenti che SONO lo standard, e si leggono dalla sezione `standard` del
//    registro `scripts/datatable.baseline.json` (una sede sola per l'elenco,
//    2026-10-03): le altre eccezioni si marcano sul punto,
//    `eslint-disable-next-line no-restricted-imports -- <motivo>`, e restano
//    presidiate dal registro, un cricchetto che il lint non sa essere: un
//    commento costa dieci secondi, una riga nel registro costa un diff.
// ⚠️ I guard `check-dialog-chrome.mjs` e `check-datatable-baseline.mjs` restano,
//    e non per ridondanza: un `eslint-disable-next-line` zittisce questa regola
//    in qualunque file, i guard le direttive non le leggono. Il primo controlla
//    anche il chrome (header, closable, confirmAction), il secondo il verso del
//    debito. Un componente nuovo entra qui quando nasce il
//    suo wrapper.
// Doc: docs/it/dev/frontend/frontend-standards.md §«Import PrimeVue riservati».
// Scopo: i componenti che sono lo standard della lista, dal registro DataTable
//        (chiavi relative a src/). ⛔ Il file c'e' sempre in git: se manca, il
//        lint si ferma qui invece di esentare nessuno in silenzio.
function standardDataTable() {
  const registro = JSON.parse(readFileSync(new URL('./scripts/datatable.baseline.json', import.meta.url), 'utf8'))
  return Object.keys(registro.standard).map((f) => `src/${f}`)
}

const IMPORT_PRIMEVUE_RISERVATI = [
  {
    name: 'primevue/dialog',
    sedi: ['src/core/components/AppDialog.vue'],
    message: 'Si usa <AppDialog> (core/components/AppDialog.vue): il chrome delle dialog ha una sede sola.',
  },
  {
    name: 'primevue/confirmdialog',
    sedi: ['src/App.vue'],
    message: "La ConfirmDialog e' solo globale, in App.vue: si chiede con useConfirmAction.",
  },
  {
    name: 'primevue/useconfirm',
    sedi: ['src/core/composables/useConfirmAction.js'],
    message: 'Si usa useConfirmAction (core/composables/useConfirmAction.js).',
  },
  {
    name: 'primevue/datatable',
    sedi: standardDataTable(),
    message:
      'Una lista si monta con <ListaConfigurabile codice="...">. Un\'eccezione va motivata in un ' +
      'commento sopra l\'import, marcata con eslint-disable-next-line e scritta nel registro ' +
      '(node scripts/check-datatable-baseline.mjs --baseline).',
  },
  {
    // Dal 2026-10-03, a migrazione finita (80 → 0, analisi-fe-chrome-drawer):
    // nessun registro, perche' non c'e' debito da far calare. Le due sedi in
    // piu' non sono drawer laterali e non sono eccezioni: il menu mobile
    // (`AppLayout`, da sinistra) e i filtri compatti (`FiltriLista`, dal basso)
    // usano il componente `Drawer` per un'altra cosa (analisi §2, forma E).
    name: 'primevue/drawer',
    sedi: [
      'src/core/components/AppDrawer.vue',
      'src/core/components/AppLayout.vue',
      'src/core/components/FiltriLista.vue',
    ],
    message:
      'Un drawer laterale si monta con <AppDrawer> (core/components/AppDrawer.vue): testata, ' +
      'larghezza, uscita con conferma, footer e readonly hanno una sede sola.',
  },
]

// Scopo: la regola con tutti gli import riservati tranne `tranne` — per le
//        sedi, che il proprio import lo devono fare. ⚠️ In flat config le opzioni
//        di una regola si SOSTITUISCONO, non si sommano: una sede riceve l'elenco
//        intero meno il suo, altrimenti sarebbe libera di importare gli altri.
function importRiservati(tranne = null) {
  return [
    'error',
    {
      paths: IMPORT_PRIMEVUE_RISERVATI.filter((p) => p.name !== tranne).map(({ name, message }) => ({
        name,
        message,
      })),
    },
  ]
}

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

  {
    name: 'app/import-primevue-riservati',
    files: ['src/**/*.{vue,js}'],
    rules: {
      'no-restricted-imports': importRiservati(),
    },
  },
  ...IMPORT_PRIMEVUE_RISERVATI.filter((p) => p.sedi?.length).map((p) => ({
    name: `app/import-primevue-riservati/sede:${p.name}`,
    files: p.sedi,
    rules: {
      'no-restricted-imports': importRiservati(p.name),
    },
  })),

  {
    // ⛔ Un `eslint-disable` che non copre piu' niente e' un'eccezione rimasta
    //    aperta sul vuoto: la lista e' passata a `<ListaConfigurabile>`, il
    //    commento no, e il prossimo import su quella riga passerebbe muto.
    name: 'app/direttive-inutilizzate',
    linterOptions: {
      reportUnusedDisableDirectives: 'error',
    },
  },

  ...pluginOxlint.buildFromOxlintConfigFile('.oxlintrc.json'),

  skipFormatting,
])
