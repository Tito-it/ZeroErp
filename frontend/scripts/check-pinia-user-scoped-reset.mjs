// Scopo: verifica meccanica del reset degli store user-scoped al logout
//        (`src/core/pinia-plugins/auto-reset.js`), senza browser e senza
//        dover fare login-A / logout / login-B a mano.
//
// Perche' esiste: il plugin e' l'unica difesa contro il data leak fra utenti
// sullo stesso browser (39 store `userScoped: true` su 43). Se smette di
// funzionare il sintomo e' SILENZIOSO — nessun errore, nessun build rosso,
// solo l'utente B che vede filtri e cache dell'utente A. Questo script rende
// quel guasto rumoroso, ed e' la rete da tenere durante gli upgrade di Pinia.
//
// Uso:
//   cd frontend && node scripts/check-pinia-user-scoped-reset.mjs
// Exit 0 = tutto verde. Exit 1 = almeno un caso rotto (dettaglio a video).

import { readFileSync } from 'node:fs'

import { createPinia, defineStore, setActivePinia } from 'pinia'
import { createApp, ref } from 'vue'

import {
  autoResetPlugin,
  registerUserScopedResetter,
  resetAllUserScopedStores,
} from '../src/core/pinia-plugins/auto-reset.js'

const esiti = []

// Scopo: registra l'esito di un singolo caso e lo stampa.
function verifica(nome, condizione, dettaglio = '') {
  esiti.push({ nome, ok: Boolean(condizione) })
  const marca = condizione ? '[ok]' : '[KO]'
  console.log(`${marca} ${nome}${condizione || !dettaglio ? '' : ` — ${dettaglio}`}`)
}

// Stessa sequenza di `src/main.js`, e non e' un dettaglio: `pinia.use(...)`
// chiamato PRIMA di `app.use(pinia)` mette il plugin in coda, e la coda viene
// scaricata solo da `install(app)`. Senza una app Vue il plugin non girerebbe
// mai e il test passerebbe... verificando nulla.
const pinia = createPinia()
pinia.use(autoResetPlugin)
createApp({ render: () => null }).use(pinia)
setActivePinia(pinia)

// --- Store di prova -------------------------------------------------------

// 1) User-scoped "normale": si affida allo snapshot + $resetToInitial.
const useLista = defineStore(
  'lista',
  () => {
    const items = ref([])
    const filters = ref({ ricerca: '', dataDa: null })
    return { items, filters }
  },
  { userScoped: true },
)

// 2) User-scoped con clearUserState: deve essere preferito allo snapshot
//    (e' il caso di auth/tabs/parameters, che puliscono anche localStorage).
let clearUserStateChiamato = 0
const useAuth = defineStore(
  'auth',
  () => {
    const token = ref(null)
    // Scopo: cleanup esplicito, ha la precedenza su $resetToInitial.
    function clearUserState() {
      clearUserStateChiamato += 1
      token.value = null
    }
    return { token, clearUserState }
  },
  { userScoped: true },
)

// 3) NON user-scoped: deve sopravvivere al logout (es. preferenze non legate
//    all'utente). Se lo azzerassimo, il reset sarebbe troppo largo.
const useAppShell = defineStore('appShell', () => {
  const sidebarAperta = ref(true)
  return { sidebarAperta }
})

// 4) Resetter module-scope (cache dei composable: useGlobalLookup, i18n, ...).
let cacheModulo = new Map([['clienti', ['a', 'b']]])
registerUserScopedResetter(() => cacheModulo.clear())

// --- Sessione "utente A" --------------------------------------------------

const lista = useLista()
const auth = useAuth()
const appShell = useAppShell()

lista.items = [{ id: 1 }, { id: 2 }]
lista.filters.ricerca = 'rossi'
lista.filters.dataDa = '2026-01-01'
auth.token = 'jwt-utente-A'
appShell.sidebarAperta = false

verifica(
  'precondizione: gli store contengono dati dell-utente A',
  lista.items.length === 2 && auth.token === 'jwt-utente-A' && cacheModulo.size === 1,
)

// --- Logout ---------------------------------------------------------------

resetAllUserScopedStores()

// --- Asserzioni -----------------------------------------------------------

verifica(
  'store user-scoped: items azzerati',
  lista.items.length === 0,
  `trovati ${lista.items.length} item residui`,
)
verifica(
  'store user-scoped: filtri azzerati (il caso che si vede a video)',
  lista.filters.ricerca === '' && lista.filters.dataDa === null,
  `ricerca=${JSON.stringify(lista.filters.ricerca)} dataDa=${JSON.stringify(lista.filters.dataDa)}`,
)
verifica(
  'store con clearUserState: invocato una volta sola',
  clearUserStateChiamato === 1,
  `invocazioni: ${clearUserStateChiamato}`,
)
verifica('store con clearUserState: token azzerato', auth.token === null, `token=${auth.token}`)
verifica(
  'store NON user-scoped: intatto (il reset non e- troppo largo)',
  appShell.sidebarAperta === false,
  'lo stato non user-scoped e stato azzerato per errore',
)
verifica(
  'resetter module-scope: cache dei composable svuotata',
  cacheModulo.size === 0,
  `${cacheModulo.size} voci residue`,
)

// --- Sessione "utente B": il reset deve reggere anche al giro dopo --------

lista.filters.ricerca = 'bianchi'
auth.token = 'jwt-utente-B'
cacheModulo = new Map([['clienti', ['c']]])
registerUserScopedResetter(() => cacheModulo.clear())
resetAllUserScopedStores()

verifica(
  'secondo logout: reset ancora efficace (registro non consumato)',
  lista.filters.ricerca === '' && auth.token === null,
)

// --- Guardia sull-API privata --------------------------------------------

// I commenti del plugin citano `pinia._s` per spiegare perche' NON si usa:
// vanno tolti prima del controllo, altrimenti il check accusa la propria
// documentazione.
const sorgente = readFileSync(
  new URL('../src/core/pinia-plugins/auto-reset.js', import.meta.url),
  'utf8',
)
const codice = sorgente
  .split('\n')
  .filter((riga) => !riga.trimStart().startsWith('//'))
  .join('\n')
verifica(
  'il plugin non legge API private di Pinia (pinia._s)',
  !/pinia\s*\._/.test(codice),
  'trovato un accesso a `pinia._*`: torna a dipendere dagli interni di Pinia',
)

// --- Esito ----------------------------------------------------------------

// Scopo: versione di Pinia effettivamente installata — va stampata, e' il dato
//        che rende leggibile l'esito durante un upgrade.
function versionePinia() {
  try {
    const pkg = readFileSync(
      new URL('../node_modules/pinia/package.json', import.meta.url),
      'utf8',
    )
    return JSON.parse(pkg).version
  } catch {
    return 'sconosciuta'
  }
}

const falliti = esiti.filter((e) => !e.ok)
console.log(
  `\n${esiti.length - falliti.length}/${esiti.length} verifiche superate ` +
    `(pinia ${versionePinia()})`,
)
if (falliti.length) {
  console.error(
    '\nIl reset user-scoped e ROTTO: al logout i dati dell-utente precedente\n' +
      'restano in memoria. NON proseguire con l-upgrade finche- non e verde.',
  )
  process.exit(1)
}
