// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: Guard del contratto d'uso di `<ListaConfigurabile>` nei componenti
//        che lo montano.
//
//   Nasce da un difetto reale (2026-07-31, `IndirizziSearchTable`): convertendo
//   una lista da `<DataTable>` la firma di `@row-click` CAMBIA — il BB emette
//   `data` direttamente, PrimeVue emetteva l'evento con `event.data` dentro.
//   Un handler rimasto `onRowClick(event) { ... event.data }` riceve la riga e
//   legge `undefined`: **non rompe il build, rompe il click**. Nessun lint lo
//   vede, e a video sembra solo che "il drawer non si apra".
//
//   Uso:
//     node scripts/check-liste-configurabili.mjs
//   Exit 1 se un componente viola il contratto.
// ------------------------------------------------------------

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))
// Il BB stesso monta la DataTable e usa `event.data`: e' il traduttore, non un
// consumatore. Escluso per costruzione, non per eccezione.
const ESCLUSI = ['core/components/ListaConfigurabile.vue']

// Scopo: sorgente senza commenti. Serve a distinguere chi MONTA il componente
//        da chi lo NOMINA — `GeoSearchTable` (ritirato il 2026-09-27) lo citava
//        in un commento proprio per dire che non lo usava, e montava
//        `<DataTable>`, dove `event.data` e' corretto. Senza questo passaggio il guard segnalerebbe codice giusto,
//        cioe' diventerebbe rumore da ignorare.
function senzaCommenti(testo) {
  return testo
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/^\s*\/\/.*$/gm, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
}

// Scopo: elenco ricorsivo dei .vue sotto src.
function fileVue(dir, acc = []) {
  for (const voce of readdirSync(dir)) {
    const p = join(dir, voce)
    if (statSync(p).isDirectory()) fileVue(p, acc)
    else if (voce.endsWith('.vue')) acc.push(p)
  }
  return acc
}

// Scopo: nome dell'handler passato a @row-click, se e' un riferimento a
//        funzione (`@row-click="onRowClick"`). Gli arrow inline si validano
//        da soli a vista e non hanno un corpo da ispezionare qui.
function handlerRowClick(testo) {
  const m = testo.match(/@row-click="([A-Za-z_$][\w$]*)"/)
  return m ? m[1] : null
}

const problemi = []
for (const percorso of fileVue(SRC)) {
  const rel = relative(SRC, percorso).replace(/\\/g, '/')
  if (ESCLUSI.includes(rel)) continue
  const testo = senzaCommenti(readFileSync(percorso, 'utf8'))
  if (!testo.includes('<ListaConfigurabile')) continue

  const handler = handlerRowClick(testo)
  if (!handler) continue

  // Corpo della funzione handler (dichiarazione o const arrow).
  const decl = new RegExp(
    `function\\s+${handler}\\s*\\(([^)]*)\\)\\s*\\{([\\s\\S]*?)\\n\\}` +
    `|const\\s+${handler}\\s*=\\s*\\(?([^)=]*)\\)?\\s*=>\\s*\\{?([\\s\\S]{0,200})`,
  )
  const m = testo.match(decl)
  if (!m) continue
  const param = (m[1] ?? m[3] ?? '').trim()
  const corpo = m[2] ?? m[4] ?? ''

  // Il difetto: il parametro E' la riga, ma il corpo lo tratta come evento
  // PrimeVue leggendone `.data`.
  if (param && new RegExp(`\\b${param}\\.data\\b`).test(corpo)) {
    problemi.push({
      file: rel,
      handler,
      dettaglio: `\`${handler}(${param})\` legge \`${param}.data\`, ma <ListaConfigurabile> ` +
        'emette gia\' la riga: il valore risulta undefined.',
    })
  }
}

if (problemi.length) {
  console.error(`[X] ${problemi.length} componenti violano il contratto di <ListaConfigurabile>:\n`)
  for (const p of problemi) {
    console.error(`  ${p.file}`)
    console.error(`    ${p.dettaglio}\n`)
  }
  console.error('Correzione: l\'handler riceve la RIGA, non l\'evento PrimeVue.')
  process.exit(1)
}

console.log('[ok] contratto @row-click di <ListaConfigurabile> rispettato ovunque')
