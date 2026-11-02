// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: Guard «un componente non parla HTTP» (frontend-standards §Regole per
//        il developer, regola 2; decisione Tid 2026-09-26). Un `.vue` non
//        importa il client axios (`core/api.js`): l'URL di un endpoint vive in
//        UN modulo `api/` (del dominio o `core/api/`) o dietro uno store, e il
//        componente chiama quella funzione dentro `execute` di useApiHandler.
//        Vale anche per i composable (`composables/*.js`): sono pezzi di
//        componente, e un URL scritto lì sfugge al modulo api/ come in un `.vue`.
//
//   Il difetto che previene: sette componenti di `core/` scrivevano l'URL a
//   mano, e quattro gestivano l'errore con un `catch` proprio — che perde
//   campi in errore, bersaglio e soluzione dell'envelope, e in due casi
//   mostrava un «errore» generico al posto del messaggio del backend.
//
//   Uso:
//     node scripts/check-api-componenti.mjs
//   Exit 1 se un `.vue` o un composable importa il client (li elenca tutti).
// ------------------------------------------------------------

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))
const CLIENT = resolve(SRC, 'core/api.js')

// Scopo: i `.vue` e i composable (`.js` sotto una cartella `composables/`,
//        esclusi gli spec).
function fileComponenti(dir, acc = []) {
  for (const voce of readdirSync(dir)) {
    const p = join(dir, voce)
    if (statSync(p).isDirectory()) fileComponenti(p, acc)
    else if (voce.endsWith('.vue')) acc.push(p)
    else if (voce.endsWith('.js') && !voce.endsWith('.spec.js')
      && dirname(p).split(/[\\/]/).includes('composables')) acc.push(p)
  }
  return acc
}

// Scopo: risolve lo specificatore di un import al file che indica.
function risolvi(da, spec) {
  let base
  if (spec.startsWith('@/')) base = resolve(SRC, spec.slice(2))
  else if (spec.startsWith('.')) base = resolve(dirname(da), spec)
  else return null
  return base.endsWith('.js') ? base : `${base}.js`
}

const violazioni = []
for (const f of fileComponenti(SRC)) {
  const testo = readFileSync(f, 'utf8')
  for (const m of testo.matchAll(/import\s+[^'"]*?from\s*['"]([^'"]+)['"]/g)) {
    if (risolvi(f, m[1]) === CLIENT) {
      const riga = testo.slice(0, m.index).split('\n').length
      violazioni.push(`${relative(SRC, f)}:${riga}  importa il client HTTP (${m[1]})`)
    }
  }
}

if (violazioni.length) {
  console.error('✗ Componenti che parlano HTTP da soli — usare un modulo api/ o uno store:')
  for (const v of violazioni) console.error(`  ${v}`)
  process.exit(1)
}
console.log('✓ api-componenti: nessun .vue né composable importa il client HTTP')
