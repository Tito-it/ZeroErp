// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: Guard dei codepoint PrimeIcons cablati in `src/assets/main.css`.
//
//   Le icone composite di dominio (`.app-nav-icon-*`, frontend-standards
//   §"Iconografia di dominio") non usano le classi `pi-*`: incollano il GLIFO
//   con `content: "\eXXX"`. Se un aggiornamento di primeicons rinumera i
//   codepoint, quelle icone diventano **glifi sbagliati in silenzio** — nessun
//   errore, nessun test rosso, solo un camion al posto di una matita.
//
//   Questo script confronta ogni codepoint cablato con la mappa
//   `.pi-<nome>:before { content: "\eXXX" }` del primeicons.css INSTALLATO, e
//   dice per ciascuno che icona è diventato.
//
//   Uso:
//     node scripts/check-primeicons-codepoints.mjs            # confronto
//     node scripts/check-primeicons-codepoints.mjs --baseline # scrive la baseline
//
//   Exit code 1 se un codepoint cablato non esiste più nel font o se è
//   cambiato rispetto alla baseline: è pensato per girare PRIMA e DOPO un
//   aggiornamento di primeicons.
// ------------------------------------------------------------

import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const MAIN_CSS = resolve(HERE, '../src/assets/main.css')
const PRIMEICONS_CSS = resolve(HERE, '../node_modules/primeicons/primeicons.css')
const BASELINE = resolve(HERE, 'primeicons-codepoints.baseline.json')

const scriveBaseline = process.argv.includes('--baseline')

// --- 1. Mappa codepoint -> nome icona, dal font INSTALLATO ------------------
if (!existsSync(PRIMEICONS_CSS)) {
  console.error(`[X] primeicons non installato: ${PRIMEICONS_CSS}`)
  process.exit(1)
}
const primeicons = readFileSync(PRIMEICONS_CSS, 'utf8')
const perCodepoint = new Map()
// `.pi-nome:before { content: "\eXXX" }` — il CSS puo' essere minificato o no,
// quindi si accetta qualunque spaziatura fra selettore e content.
const RE_ICONA = /\.pi-([a-z0-9-]+):before\s*\{\s*content:\s*"\\([0-9a-fA-F]{4})"/g
for (const m of primeicons.matchAll(RE_ICONA)) {
  const [, nome, code] = m
  const key = code.toLowerCase()
  if (!perCodepoint.has(key)) perCodepoint.set(key, [])
  perCodepoint.get(key).push(nome)
}

// --- 2. Codepoint cablati nel nostro CSS -----------------------------------
const mainCss = readFileSync(MAIN_CSS, 'utf8')
const righe = mainCss.split('\n')
const cablati = []
let selettoreCorrente = null
righe.forEach((riga, i) => {
  const sel = riga.match(/^\s*(\.[a-z0-9-]+(?:::?(?:before|after))?)\s*\{/i)
  if (sel) selettoreCorrente = sel[1]
  const c = riga.match(/content:\s*"\\([0-9a-fA-F]{4})"/)
  if (c) {
    cablati.push({
      linea: i + 1,
      selettore: selettoreCorrente ?? '(ignoto)',
      code: c[1].toLowerCase(),
      // Commento inline `/* pi-nome — ... */`: e' la nostra dichiarazione di
      // INTENZIONE, l'unico modo per accorgersi che il glifo e' cambiato.
      // Normalizzato SENZA il prefisso `pi-`, perche' e' la forma in cui le
      // icone stanno nella mappa estratta da primeicons.css.
      atteso: ((riga.match(/\/\*\s*pi-([a-z0-9-]+)/) ?? [])[1]) ?? null,
    })
  }
})

if (cablati.length === 0) {
  console.log('[ok] nessun codepoint cablato in main.css — niente da verificare')
  process.exit(0)
}

// --- 3. Risoluzione --------------------------------------------------------
const risolti = cablati.map((c) => ({
  ...c,
  nomi: perCodepoint.get(c.code) ?? [],
}))

if (scriveBaseline) {
  const snapshot = Object.fromEntries(
    risolti.map((r) => [r.code, r.nomi.slice().sort()]),
  )
  writeFileSync(BASELINE, JSON.stringify(snapshot, null, 2) + '\n')
  console.log(`[ok] baseline scritta: ${BASELINE} (${Object.keys(snapshot).length} codepoint)`)
  process.exit(0)
}

let problemi = 0
console.log(`Codepoint PrimeIcons cablati in main.css: ${risolti.length}\n`)
for (const r of risolti) {
  const nomi = r.nomi.length ? r.nomi.join(', ') : '(NESSUNA ICONA CON QUESTO CODICE)'
  let stato = '  '
  if (r.nomi.length === 0) {
    stato = '[X]'; problemi++
  } else if (r.atteso && !r.nomi.includes(r.atteso)) {
    stato = '[!]'; problemi++
  }
  const att = r.atteso ? `  atteso=${r.atteso}` : ''
  console.log(`${stato} main.css:${String(r.linea).padStart(4)}  \\${r.code}  ${r.selettore}  ->  ${nomi}${att}`)
}

// --- 4. Confronto con la baseline (se esiste) ------------------------------
if (existsSync(BASELINE)) {
  const base = JSON.parse(readFileSync(BASELINE, 'utf8'))
  const drift = []
  for (const r of risolti) {
    const prima = base[r.code]
    if (!prima) continue
    const ora = r.nomi.slice().sort()
    if (JSON.stringify(prima) !== JSON.stringify(ora)) {
      drift.push(`  \\${r.code}: era [${prima.join(', ')}] ora [${ora.join(', ')}]`)
    }
  }
  if (drift.length) {
    console.log(`\n[X] ${drift.length} codepoint CAMBIATI rispetto alla baseline:`)
    drift.forEach((d) => console.log(d))
    problemi += drift.length
  } else {
    console.log('\n[ok] nessun drift rispetto alla baseline')
  }
} else {
  console.log(`\n[i] nessuna baseline (${BASELINE}) — creala con --baseline PRIMA di aggiornare primeicons`)
}

if (problemi) {
  console.log(`\n[X] ${problemi} problemi: le icone composite di dominio vanno riviste a video.`)
  process.exit(1)
}
console.log('\n[ok] tutti i codepoint cablati risolvono a un\'icona esistente')
