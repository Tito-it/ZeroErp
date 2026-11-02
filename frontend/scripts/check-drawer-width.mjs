// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: Guard delle chiavi di `DRAWER_WIDTH`: ogni `DRAWER_WIDTH.X` scritto in
//        `src/` deve esistere in `core/constants.js`.
//
//   Nasce da un difetto reale (`TitoloIvaDrawer.vue`, trovato in collaudo il
//   2026-09-02): `:style="{ width: DRAWER_WIDTH.LARGE }"` — chiave che non
//   esiste. `undefined` finisce in `width`, il browser ignora la regola e il
//   drawer resta al default di PrimeVue: **320px**. Le griglie a 2 e 3 colonne
//   collassano e la maschera sembra scritta male quando e' solo strizzata.
//
//   ⛔ E' la famiglia dei difetti che questo repo paga piu' cari: non rompe il
//   build, non lo vede nessun lint, e si scopre solo perche' qualcuno guarda.
//
//   ⭐ E LA LARGHEZZA DI `<AppDrawer>` SI SCRIVE DALLA SCALA (2026-10-03, D-4
//   di work-done/analisi-fe-chrome-drawer.md). Una chiave sbagliata non
//   e' l'unico modo di uscirne: `VersioneDrawer` aveva `'1000px'` scritto a
//   mano, e questo guard non lo vedeva perche' non nominava `DRAWER_WIDTH`.
//   Sul tag della sede si ferma il valore LETTERALE (`width="…"`, o
//   `:width="'…'"`); un'espressione (`:width="larghezzaDrawer"`) la controlla
//   il validatore della prop, a runtime.
//
//   Uso:
//     node scripts/check-drawer-width.mjs
//   Exit 1 se un file usa una chiave che non esiste, o scrive a mano la
//   larghezza di un `<AppDrawer>`.
// ------------------------------------------------------------

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))
const COSTANTI = join(SRC, 'core/constants.js')
// Le sole sedi che montano il `Drawer` di PrimeVue: il guscio dei drawer
// laterali, il menu mobile e i filtri dal basso (lo stesso elenco di
// `eslint.config.js`, IMPORT_PRIMEVUE_RISERVATI).
const SEDI_DRAWER = [
  'core/components/AppDrawer.vue',
  'core/components/AppLayout.vue',
  'core/components/FiltriLista.vue',
]

// Scopo: sorgente senza commenti. ⚠️ Serve a distinguere chi USA la costante da
//        chi la NOMINA: `assets/main.css` cita `DRAWER_WIDTH.X` in un commento
//        per spiegare come PrimeVue riceve la larghezza, e senza questo passo
//        il guard segnalerebbe un testo — cioe' diventerebbe rumore.
function senzaCommenti(testo) {
  return testo
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
}

function fileSorgente(dir, acc = []) {
  for (const voce of readdirSync(dir)) {
    const p = join(dir, voce)
    if (statSync(p).isDirectory()) fileSorgente(p, acc)
    else if (/\.(vue|js|css)$/.test(voce)) acc.push(p)
  }
  return acc
}

// Le chiavi dichiarate: si leggono dal blocco `export const DRAWER_WIDTH = {…}`
// invece di importarlo, cosi' il guard non ha bisogno di un bundler.
const sorgenteCostanti = readFileSync(COSTANTI, 'utf8')
const blocco = sorgenteCostanti.match(/export const DRAWER_WIDTH = \{([\s\S]*?)\n\}/)
if (!blocco) {
  console.error('[ko] blocco `export const DRAWER_WIDTH = {…}` non trovato in core/constants.js')
  process.exit(1)
}
const chiavi = new Set(
  [...senzaCommenti(blocco[1]).matchAll(/^\s*([A-Z_]+)\s*:/gm)].map((m) => m[1]),
)
if (chiavi.size === 0) {
  console.error('[ko] nessuna chiave letta da DRAWER_WIDTH: il rilevamento e\' rotto')
  process.exit(1)
}

const colpevoli = []
for (const percorso of fileSorgente(SRC)) {
  const testo = senzaCommenti(readFileSync(percorso, 'utf8'))
  for (const m of testo.matchAll(/DRAWER_WIDTH\.([A-Z_]+)/g)) {
    if (!chiavi.has(m[1])) {
      colpevoli.push(`${relative(SRC, percorso)}: DRAWER_WIDTH.${m[1]}`)
    }
  }
  // ⚠️ Gli attributi si scorrono con le virgolette rispettate: la forma
  //    canonica del tag ha `@update:visible="(v) => emit(…)"`, e con `[^>]*` il
  //    `>` della freccia chiudeva il tag — ogni larghezza scritta DOPO
  //    l'handler passava muta (trovato il 2026-10-03).
  for (const t of testo.matchAll(/<AppDrawer\b((?:[^>"']|"[^"]*"|'[^']*')*)>/g)) {
    const m = t[1].match(/\swidth="([^"]*)"|\s:width="'([^']*)'"/)
    if (!m) continue
    colpevoli.push(
      `${relative(SRC, percorso)}: <AppDrawer> con la larghezza scritta a mano `
      + `(${m[1] ?? m[2]}) — si passa :width="DRAWER_WIDTH.X"`,
    )
  }
  // ⛔ `primevue/drawer` fuori dalle sedi. Il lint lo ferma nell'editor, ma un
  //    `eslint-disable-next-line` lo zittisce in qualunque file: come per
  //    dialog e DataTable, l'ultima parola e' di un guard, che le direttive non
  //    le legge (frontend-standards §«Import PrimeVue riservati»).
  const rel = relative(SRC, percorso)
  if (/from\s+['"]primevue\/drawer['"]/.test(testo) && !SEDI_DRAWER.includes(rel)) {
    colpevoli.push(`${rel}: importa primevue/drawer — si usa <AppDrawer> (sedi: ${SEDI_DRAWER.join(', ')})`)
  }
}

if (colpevoli.length > 0) {
  console.error(
    '[ko] larghezze di drawer fuori dalla scala DRAWER_WIDTH — una chiave che non '
    + 'esiste lascia il drawer al default di PrimeVue (320px) e nessuno se ne '
    + `accorge. Ammesse: ${[...chiavi].join(', ')}`,
  )
  for (const c of colpevoli) console.error(`     ${c}`)
  process.exit(1)
}
console.log(`[ok] tutte le chiavi DRAWER_WIDTH esistono (${chiavi.size} ammesse)`)
