// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: Guard delle SOGLIE DELLA FINESTRA (frontend-standards §Responsive,
//        decisione Tid 2026-09-26, strada B). Una `@media` puo' stare nel
//        componente, ma una soglia di larghezza deve essere una di
//        `BREAKPOINTS` (core/constants.js), scritta nella forma canonica:
//          max-width: <B - 0.02>px   («sotto B»: BREAKPOINTS.X si legge `< X`)
//          min-width: <B>px          («da B in su»)
//        Una `@media` non accetta `var()`, quindi il numero resta scritto nel
//        CSS: questo file e' cio' che lo tiene uguale alla sua fonte.
//
//   Il difetto che previene: `max-width: 1024px` accanto a `1023.98px` — alla
//   finestra larga esattamente 1024px la topbar si credeva tablet e il resto
//   desktop. Le soglie che dipendono dal RIQUADRO (drawer, dialog) non sono
//   `@media`: sono `@container`, e qui non si contano.
//   Le query senza larghezza (`hover`, `pointer`, `prefers-*`) sono libere.
//
//   Uso:
//     node scripts/check-media-soglie.mjs
//   Exit 1 se una soglia non e' canonica (le elenca tutte).
// ------------------------------------------------------------

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))

// Scopo: legge BREAKPOINTS dalla sua sede, senza importarla (constants.js
//        importa altri moduli dell'app).
function leggiBreakpoints() {
  const testo = readFileSync(join(SRC, 'core/constants.js'), 'utf8')
  const blocco = testo.match(/export const BREAKPOINTS = \{([\s\S]*?)\}/)
  if (!blocco) throw new Error('BREAKPOINTS non trovato in core/constants.js')
  return [...blocco[1].matchAll(/([A-Z_]+):\s*(\d+)/g)].map(m => ({ nome: m[1], px: Number(m[2]) }))
}

function fileStile(dir, acc = []) {
  for (const voce of readdirSync(dir)) {
    const p = join(dir, voce)
    if (statSync(p).isDirectory()) fileStile(p, acc)
    else if (/\.(vue|css)$/.test(voce)) acc.push(p)
  }
  return acc
}

const bp = leggiBreakpoints()
const ammesse = new Map()
for (const { nome, px } of bp) {
  ammesse.set(`max-width:${(px - 0.02).toFixed(2)}px`, nome)
  ammesse.set(`min-width:${px}px`, nome)
}

const violazioni = []
for (const f of fileStile(SRC)) {
  // I commenti CSS non contano: una soglia citata in una nota non e' una regola.
  const testo = readFileSync(f, 'utf8').replace(/\/\*[\s\S]*?\*\//g, m => m.replace(/[^\n]/g, ''))
  for (const m of testo.matchAll(/@media([^{]*)\{/g)) {
    for (const w of m[1].matchAll(/\(\s*((?:max|min)-width)\s*:\s*([^)]+?)\s*\)/g)) {
      const chiave = `${w[1]}:${w[2].replace(/\s+/g, '')}`
      if (!ammesse.has(chiave)) {
        const riga = testo.slice(0, m.index).split('\n').length
        violazioni.push(`${relative(SRC, f)}:${riga}  (${w[1]}: ${w[2]})`)
      }
    }
  }
}

if (violazioni.length) {
  console.error('✗ Soglie di finestra fuori da BREAKPOINTS (forma: max-width B-0.02px, min-width Bpx):')
  for (const v of violazioni) console.error(`  ${v}`)
  console.error(`  ammesse: ${[...ammesse.keys()].join(', ')}`)
  process.exit(1)
}
console.log(`✓ media-soglie: ogni @media cita BREAKPOINTS (${bp.map(b => b.nome).join(', ')})`)
