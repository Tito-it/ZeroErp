// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
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
//   Uso:
//     node scripts/check-drawer-width.mjs
//   Exit 1 se un file usa una chiave che non esiste.
// ------------------------------------------------------------

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))
const COSTANTI = join(SRC, 'core/constants.js')

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
}

if (colpevoli.length > 0) {
  console.error(
    '[ko] chiavi di DRAWER_WIDTH inesistenti — il drawer resta al default di '
    + `PrimeVue (320px) e nessuno se ne accorge. Ammesse: ${[...chiavi].join(', ')}`,
  )
  for (const c of colpevoli) console.error(`     ${c}`)
  process.exit(1)
}
console.log(`[ok] tutte le chiavi DRAWER_WIDTH esistono (${chiavi.size} ammesse)`)
