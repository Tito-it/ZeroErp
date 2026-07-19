// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Scopo: Guard i18n — verifica che ogni chiave citata sia risolvibile nei locales.
//        Una chiave i18n mancante non produce un errore a runtime: vue-i18n
//        restituisce il path e l'utente vede un messaggio muto o un path grezzo.
//        Il difetto resta invisibile finche' qualcuno non apre quella schermata.
//
//        Copre TRE fronti, perche' le chiavi non nascono solo nel frontend:
//        A) chiavi citate nel codice FE      — t()/$t()/te()/tm() e prop *i18n-prefix*
//        B) chiavi EMESSE DAL DATABASE       — label_key/reason_key nei seed
//           `config.transizioni_stati_*` e nelle capability `fn_available_actions_*`
//        C) parita' it/en                    — nessuna chiave presente in una sola lingua
//
//        Il fronte B e' quello che intercetta la classe di difetto piu' insidiosa
//        (reason ordini emesse come `ordini.*` con l'archivio su `vendite.ordini.*`):
//        chiavi che il FE non cita mai perche' arrivano a runtime dalla capability.
//
// Uso:   npm run check:i18n   (exit 1 se qualcosa non risolve)

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const FE = join(dirname(fileURLToPath(import.meta.url)), '..')
const REPO = join(FE, '..')
const SRC = join(FE, 'src')
const LOCALES = join(SRC, 'locales')

// Chiamate i18n: t/$t/te/tm NON precedute da carattere identificatore. Il
// negative lookbehind e' essenziale: senza, `get(`/`request(` finiscono nel
// match e le URL delle API vengono scambiate per chiavi.
const CALL = /(?<![A-Za-z0-9_$.])(?:\$t|t|te|tm)\(\s*(['"`])([^'"`${}]*)/g
// Prefissi passati come prop e poi concatenati lato componente.
const PREFIX_PROP = /(?:i18n-prefix\s*=\s*["']([^"']+)["']|i18nPrefix\s*:\s*['"]([^'"]+)['"])/g
// Chiavi emesse dal DB: seed CSV (meta jsonb, virgolette raddoppiate) e corpo
// delle funzioni capability nella doc auto-gen.
const DB_KEY = /(?:label_key|reason_key)\W{1,6}([a-z][A-Za-z0-9_.]*\.[A-Za-z0-9_.]+)/g

const flatten = (obj, prefix = '', out = new Set()) => {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, out)
    else out.add(key)
  }
  return out
}

const walk = (dir, exts, out = []) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    const st = statSync(p)
    if (st.isDirectory()) {
      if (p !== LOCALES && name !== 'node_modules') walk(p, exts, out)
    } else if (exts.some((e) => name.endsWith(e))) out.push(p)
  }
  return out
}

const it = flatten(JSON.parse(readFileSync(join(LOCALES, 'it.json'), 'utf8')))
const en = flatten(JSON.parse(readFileSync(join(LOCALES, 'en.json'), 'utf8')))

// Una citazione e' valida se e' una chiave esatta OPPURE il prefisso di almeno
// una chiave: i prefissi sono legittimi (prop i18n-prefix, concatenazioni).
const prefixes = new Set()
for (const k of it) {
  const parts = k.split('.')
  for (let i = 1; i < parts.length; i++) prefixes.add(parts.slice(0, i).join('.'))
}
const resolves = (key) => it.has(key) || prefixes.has(key)

const problems = { missingFe: [], missingDb: [], parity: [] }
let citedFe = 0
let citedDb = 0

// --- A) chiavi citate nel frontend -----------------------------------------
for (const file of walk(SRC, ['.vue', '.js'])) {
  const text = readFileSync(file, 'utf8')
  const rel = relative(REPO, file)
  const lineOf = (idx) => text.slice(0, idx).split('\n').length

  for (const m of text.matchAll(CALL)) {
    const key = m[2]
    // Scarta non-chiavi: vuote, path/URL, frasi. Una chiave i18n e' fatta di
    // segmenti [a-z_] separati da punto e contiene almeno un punto.
    if (!key || !/^[a-zA-Z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$/.test(key)) continue
    citedFe++
    if (!resolves(key)) problems.missingFe.push({ rel, line: lineOf(m.index), key })
  }
  for (const m of text.matchAll(PREFIX_PROP)) {
    const key = m[1] || m[2]
    if (!key || !key.includes('.')) continue
    citedFe++
    if (!resolves(key)) problems.missingFe.push({ rel, line: lineOf(m.index), key })
  }
}

// --- B) chiavi emesse dal database -----------------------------------------
const dbSources = [
  join(REPO, 'db/changelog/migrations_v2/80_data/sql/config'),
  join(REPO, 'docs/it/dbzero/script/funzioni'),
]
for (const dir of dbSources) {
  let files = []
  try {
    files = walk(dir, ['.csv', '.md'])
  } catch {
    continue // sorgente assente (checkout parziale): non e' un fallimento del guard
  }
  for (const file of files) {
    const base = file.split('/').pop()
    if (base.endsWith('.md') && !base.startsWith('fn_available_actions')) continue
    if (base.endsWith('.csv') && !base.startsWith('transizioni_stati_')) continue
    const text = readFileSync(file, 'utf8')
    const rel = relative(REPO, file)
    const lineOf = (idx) => text.slice(0, idx).split('\n').length
    for (const m of text.matchAll(DB_KEY)) {
      const key = m[1]
      citedDb++
      if (!resolves(key)) problems.missingDb.push({ rel, line: lineOf(m.index), key })
    }
  }
}

// --- C) parita' it/en -------------------------------------------------------
for (const k of it) if (!en.has(k)) problems.parity.push(`solo it: ${k}`)
for (const k of en) if (!it.has(k)) problems.parity.push(`solo en: ${k}`)

// --- report -----------------------------------------------------------------
const dedup = (arr) => {
  const seen = new Set()
  return arr.filter((p) => {
    const s = `${p.rel}:${p.line}:${p.key}`
    return seen.has(s) ? false : seen.add(s)
  })
}
problems.missingFe = dedup(problems.missingFe)
problems.missingDb = dedup(problems.missingDb)

console.log(`i18n: ${it.size} chiavi it · ${en.size} en`)
console.log(`      ${citedFe} citazioni FE · ${citedDb} chiavi emesse dal DB`)

const section = (title, items, fmt) => {
  if (!items.length) return
  console.error(`\n✗ ${title} (${items.length}):`)
  for (const i of items.slice(0, 40)) console.error(`    ${fmt(i)}`)
  if (items.length > 40) console.error(`    … e altre ${items.length - 40}`)
}
section('chiavi citate nel FE e non presenti nei locales', problems.missingFe,
  (p) => `${p.rel}:${p.line}  ${p.key}`)
section('chiavi emesse dal DB e non risolvibili nel FE', problems.missingDb,
  (p) => `${p.rel}:${p.line}  ${p.key}`)
section('chiavi presenti in una sola lingua', problems.parity, (p) => p)

const total = problems.missingFe.length + problems.missingDb.length + problems.parity.length
if (total === 0) {
  console.log('\n✓ tutte le chiavi citate risolvono, parita it/en completa')
  process.exit(0)
}
console.error(`\n${total} problemi i18n.`)
process.exit(1)
