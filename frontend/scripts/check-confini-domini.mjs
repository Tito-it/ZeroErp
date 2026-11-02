// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: Guard dei CONFINI FRA DOMINI (frontend-standards §«Confini fra
//        domini», decisione Tid 2026-09-26). Tre regole, tutte sugli import:
//
//   1. `core/` (e gli store globali) non importano MAI un dominio. Cio' che
//      un dominio aggiunge a `core` passa dai registri (`core/registri.js`,
//      `core/drawerEntita.js`, `core/estensioni.js`) e si iscrive dal
//      `<dominio>/iscrizioni.js`.
//   2. I MOTORI (`documenti`, `pratiche`) si possono importare da ogni
//      dominio, ma non importano i domini che li usano: li conoscono solo
//      per iscrizione.
//   3. Un dominio importa un altro dominio SOLO se le sue tabelle puntano a
//      un'entita' di quello (il verso delle FK): l'elenco qui sotto, con la
//      FK che lo giustifica. Il verso opposto — mostrare nella schermata a
//      monte qualcosa del dominio a valle — passa da un punto di estensione.
//
//   ⚠️ Un arco nuovo non si aggiunge qui per far passare il guard: si
//   aggiunge SE il modello lo ammette, cioe' se esiste la FK, e la si scrive
//   accanto. Un arco senza FK e' un'estensione da iscrivere, non un'eccezione.
//
//   Uso:
//     node scripts/check-confini-domini.mjs
//   Exit 1 al primo import fuori regola (li elenca tutti).
// ------------------------------------------------------------

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join, normalize, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))

// Cartelle che NON sono domini. `router` e `main.js`/`App.vue` sono la radice
// dell'app: montano tutto per mestiere, e i loro import non si controllano —
// ma `core` e gli store globali non importano la radice (vedi sotto).
const INFRASTRUTTURA = new Set(['core', 'stores', 'locales', 'assets'])
const RADICE = new Set(['router', 'main.js', 'App.vue'])
const MOTORI = new Set(['documenti', 'pratiche'])

// Gli archi fra domini ammessi, col riferimento del modello che li giustifica.
const ARCHI_AMMESSI = {
  'vendite -> anagrafiche': 'documenti e contratti puntano al billing_account e al soggetto',
  'vendite -> catalogo': 'le righe dei documenti puntano all\'articolo',
  'magazzino -> catalogo': 'lotti e movimenti puntano all\'articolo',
  'magazzino -> anagrafiche': 'magazzini.emittente_fiscale_id',
  'vendite -> magazzino': 'ddt.magazzino_id / magazzino_arrivo_id e resi.magazzino_id puntano al magazzino',
  'pagamenti -> anagrafiche': 'mandati, canali e movimenti puntano a soggetto e conto bancario',
  'pagamenti -> vendite': 'vendite_movimenti / vendite_contabili_righe puntano al documento',
  'anagrafiche -> catalogo': 'soggetti_titoli_iva_ambiti.articolo_id',
  'amministrazione -> anagrafiche': 'emittente fiscale e operatore sono un soggetto',
  'pratiche -> anagrafiche': 'pratiche.pratiche punta al cliente (billing account / soggetto)',
}

function fileSorgente(dir, acc = []) {
  for (const voce of readdirSync(dir)) {
    const p = join(dir, voce)
    if (statSync(p).isDirectory()) fileSorgente(p, acc)
    else if (/\.(vue|js)$/.test(voce) && !/\.(spec|test)\.js$/.test(voce)) acc.push(p)
  }
  return acc
}

const radiceDi = (p) => relative(SRC, p).split(sep)[0]

// Scopo: risolve lo specificatore di un import alla cartella di primo livello.
function bersaglio(da, spec) {
  let base
  if (spec.startsWith('@/')) base = resolve(SRC, spec.slice(2))
  else if (spec.startsWith('.')) base = resolve(dirname(da), spec)
  else return null
  for (const ext of ['', '.js', '.vue', '/index.js']) {
    if (existsSync(base + ext) && statSync(base + ext).isFile()) return radiceDi(normalize(base + ext))
  }
  return radiceDi(base)
}

// Import statici, dinamici e `import.meta.glob`, con apici, doppi apici o
// backtick: un `import(\`@/vendite/${nome}.vue\`)` in `core/` e' un import di
// dominio come gli altri, e con i soli apici passerebbe in silenzio.
const IMPORT_RE = /(?:from\s*|import\s*\(\s*|import\s+|import\.meta\.glob\(\s*)(['"`])((?:(?!\1)[^\n])+)\1/g

// Scopo: di uno specificatore con parti variabili (`${…}` di un template, `*`
//        di un glob) tiene il prefisso fisso: basta a dire in che dominio va.
function parteStatica(spec) {
  const fine = spec.search(/\$\{|\*/)
  return fine === -1 ? spec : spec.slice(0, fine)
}

const violazioni = []
for (const f of fileSorgente(SRC)) {
  const da = radiceDi(f)
  if (RADICE.has(da)) continue
  const testo = readFileSync(f, 'utf8')
  for (const m of testo.matchAll(IMPORT_RE)) {
    const spec = parteStatica(m[2])
    const a = bersaglio(f, spec)
    if (!a || a === da || INFRASTRUTTURA.has(a)) continue
    // La radice si importa solo dai domini (una view che naviga col router
    // importato e' un altro discorso, e non di confini). Da `core` no: il
    // router nomina tutti i domini, e importarlo e' una dipendenza
    // core → dominio dalla porta di servizio. `core` usa `routerApp()`.
    if (RADICE.has(a) && !INFRASTRUTTURA.has(da)) continue
    const riga = testo.slice(0, m.index).split('\n').length
    const dove = `${relative(SRC, f)}:${riga}  → ${m[2]}`
    if (INFRASTRUTTURA.has(da) && RADICE.has(a)) {
      violazioni.push(`${dove}\n      ${da}/ non importa la radice dell'app (${a}): il router nomina tutti i domini — usare core/routerApp.js`)
    } else if (INFRASTRUTTURA.has(da)) {
      violazioni.push(`${dove}\n      ${da}/ non importa un dominio: il dominio si iscrive (registri, estensioni)`)
    } else if (MOTORI.has(a)) {
      continue
    } else if (!ARCHI_AMMESSI[`${da} -> ${a}`]) {
      violazioni.push(`${dove}\n      ${da} -> ${a} non e' un arco del modello: se ${a} sta a valle, serve un punto di estensione`)
    }
  }
}

if (violazioni.length) {
  console.error('✗ Import fuori dai confini fra domini:')
  for (const v of violazioni) console.error(`  ${v}`)
  process.exit(1)
}
console.log(`✓ confini-domini: core non importa domini, motori iscritti, ${Object.keys(ARCHI_AMMESSI).length} archi del modello`)
