// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: Guard del CONTRATTO delle capability: ogni campo che il frontend
//        legge da un blob `capabilities.*` deve essere un campo che una
//        `script.fn_available_actions_*` emette davvero.
//
//   Nasce dal brief magazzino 2-bis (R-1, 2026-09-23), e dalla forma di
//   guasto che api.md §Capability descrive in prima persona:
//
//     «Prima di dichiarare fatta una capability, verificare che il client la
//      LEGGA. Un campo dichiarato e mai letto sembra presidiato e non
//      presidia niente: nel 2026 il motivo di un pulsante spento non era MAI
//      stato reso a video, perche' il frontend leggeva un nome di campo
//      diverso da quello emesso — e niente falliva.»
//
//   ⛔ E' la famiglia dei difetti che questo repo paga piu' cari: un refuso su
//   `can_registra_reason_key` non rompe il build, non accende il lint, e a
//   video lascia un pulsante grigio che sembra una REGOLA. Lo stesso vale per
//   una rinomina a DB: il campo cambia nome, il frontend continua a leggere
//   quello vecchio, e nessuno se ne accorge finche' qualcuno non guarda.
//
//   LA SORGENTE DEL CONTRATTO E' LA DOC AUTO-GENERATA, non un elenco scritto
//   qui: `docs/it/dbzero/script/funzioni/fn_available_actions_*.md` riflette
//   le funzioni VIVE nel database (AGENTS.md §«DDL dalla doc auto-gen, mai
//   dagli YAML»). Vale la regola di casa: *un elenco scritto in due posti ne
//   ha sempre uno stantio, e quello senza presidio e' sempre la copia.*
//
//   ⚠️ IL PERIMETRO E' IL BLOB ANNIDATO, ED E' UNA SCELTA. Nel progetto le
//   capability viaggiano in DUE forme:
//     * annidata — `detail.capabilities.can_x` (magazzino): il campo si
//       riconosce dal codice, e questo guard lo verifica;
//     * piatta — `detail.can_x`, letta dal BB `useEntityCapabilities`
//       (vendite): li' il campo e' indistinguibile da qualunque altro campo
//       del dettaglio, e nessuna analisi statica puo' dire se `detail.can_x`
//       sia una capability o un dato.
//   ⛔ Estendere il guard «a tutto cio' che somiglia a una capability» e'
//   stato PROVATO e scartato il 2026-09-23: su 46 token `can_*` del frontend,
//   28 sono fuori dal contratto delle `fn_available_actions_*` — e quasi
//   nessuno e' un difetto (capability di RIGA come `can_remove`, predicati
//   calcolati in Python come `can_esegui_ora`, flag emessi da viste). Vale il
//   criterio di AGENTS.md: *un cancello che capisce un caso su cinque boccia
//   a caso e passa a caso; dopo due blocchi sbagliati qualcuno lo spegne, e
//   un presidio spento e' peggio di uno assente.*
//   ⇒ Meglio un cancello stretto e vero che uno largo e rumoroso. Il giorno
//   in cui le due forme diventeranno una, questo guard le coprira' entrambe
//   senza cambiare una riga.
//
//   Uso:
//     node scripts/check-capability-contratto.mjs
//   Exit 1 al primo campo fuori contratto (li elenca tutti).
// ------------------------------------------------------------

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))
const DOC = fileURLToPath(new URL('../../docs/it/dbzero/script/funzioni', import.meta.url))

// Scopo: sorgente senza commenti, per non leggere un nome citato in una nota
//        come se fosse codice (stessa cura di check-dialog-chrome).
function senzaCommenti(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').replace(/<!--[\s\S]*?-->/g, '')
}

// Scopo: il CONTRATTO — l'unione delle chiavi che le capability emettono,
//        letta dal corpo delle funzioni nella doc auto-generata.
// ⚠️ Unione e non «la funzione di quel dominio»: legare un file del frontend
//    alla sua funzione vorrebbe una mappa cablata qui, cioe' un secondo
//    elenco da tenere allineato. L'unione basta a fermare cio' che conta —
//    un refuso e una rinomina non sono in NESSUNA funzione.
// Scopo: il corpo PL/pgSQL fra i due `$function$`, senza commenti SQL.
// ⚠️ I commenti si tolgono con un lettore che conosce le stringhe: un `--`
//    dentro un letterale non e' un commento, e un apostrofo in un commento
//    («e'») non apre una stringa — due cose che una regex sbaglia.
function corpoFunzione(md) {
  const m = md.match(/\$function\$([\s\S]*?)\$function\$/)
  if (!m) return ''
  const src = m[1]
  let out = ''
  let i = 0
  while (i < src.length) {
    const c = src[i]
    if (c === "'") {
      // Stringa SQL: `''` e' l'apostrofo escapato, non la chiusura.
      let j = i + 1
      while (j < src.length && !(src[j] === "'" && src[j + 1] !== "'")) j += src[j] === "'" ? 2 : 1
      out += src.slice(i, j + 1)
      i = j + 1
    } else if (c === '-' && src[i + 1] === '-') {
      while (i < src.length && src[i] !== '\n') i += 1
    } else if (c === '/' && src[i + 1] === '*') {
      const fine = src.indexOf('*/', i + 2)
      i = fine === -1 ? src.length : fine + 2
    } else {
      out += c
      i += 1
    }
  }
  return out
}

// Scopo: le chiavi di ogni `jsonb_build_object(...)` del corpo — gli argomenti
//        di primo livello in posizione pari che sono un letterale. Gli oggetti
//        annidati li trova la stessa scansione, uno per occorrenza.
function chiaviJsonb(corpo) {
  const chiavi = []
  for (const m of corpo.matchAll(/jsonb_build_object\s*\(/gi)) {
    const args = []
    let depth = 1
    let arg = ''
    let i = m.index + m[0].length
    while (i < corpo.length && depth > 0) {
      const c = corpo[i]
      if (c === "'") {
        let j = i + 1
        while (j < corpo.length && !(corpo[j] === "'" && corpo[j + 1] !== "'")) j += corpo[j] === "'" ? 2 : 1
        arg += corpo.slice(i, j + 1)
        i = j + 1
        continue
      }
      if (c === '(') depth += 1
      if (c === ')') depth -= 1
      if (depth === 0 || (c === ',' && depth === 1)) { args.push(arg.trim()); arg = '' } else arg += c
      i += 1
    }
    args.forEach((a, n) => {
      const lett = n % 2 === 0 && a.match(/^'([a-z][a-z0-9_]*)'$/)
      if (lett) chiavi.push(lett[1])
    })
  }
  return chiavi
}

// ⭐ Solo le CHIAVI di un `jsonb_build_object` (gli argomenti in posizione
//    pari), non «ogni letterale seguito da una virgola»: la regex di prima
//    raccoglieva anche `'database'`, `'conferma'`, `'pi pi-check'`… cioe'
//    valori, e un refuso che coincideva con uno di quei letterali passava.
function contratto() {
  const chiavi = new Set()
  let funzioni = 0
  for (const f of readdirSync(DOC).filter((n) => n.startsWith('fn_available_actions_') && n.endsWith('.md'))) {
    funzioni += 1
    for (const k of chiaviJsonb(corpoFunzione(readFileSync(join(DOC, f), 'utf8')))) chiavi.add(k)
  }
  if (funzioni === 0) {
    console.error('[xx] nessuna fn_available_actions_* nella doc auto-gen: contratto non leggibile.')
    console.error('     Il guard NON passa in silenzio: senza contratto non verifica niente.')
    process.exit(1)
  }
  // ⚠️ Funzioni trovate ma zero chiavi = il parser non capisce piu' la doc
  //    (formato cambiato): fallire, non passare in silenzio.
  if (chiavi.size === 0) {
    console.error('[xx] nessuna chiave di jsonb_build_object letta: parser della doc auto-gen da rivedere.')
    process.exit(1)
  }
  return { chiavi, funzioni }
}

// Scopo: i campi letti dal blob annidato, in tutte le forme in cui il
//        frontend ci arriva (`capabilities.x`, `capabilities.value.x`,
//        `capabilities?.x`, `caps.capabilities.x`).
const LETTURA = /\bcapabilities\s*(?:\?\.|\.)\s*(?:value\s*(?:\?\.|\.)\s*)?([a-z][a-z0-9_]*)/g
// ⚠️ `value` e' l'unwrap di un ref, non un campo del blob: la regex lo
//    attraversa, e se compare da solo non e' un campo da verificare.
const NON_CAMPI = new Set(['value'])

function letture() {
  const trovate = new Map()
  const cammina = (dir) => {
    for (const nome of readdirSync(dir)) {
      const p = join(dir, nome)
      if (statSync(p).isDirectory()) { cammina(p); continue }
      if (!/\.(vue|js)$/.test(nome)) continue
      const src = senzaCommenti(readFileSync(p, 'utf8'))
      for (const m of src.matchAll(LETTURA)) {
        if (NON_CAMPI.has(m[1])) continue
        if (!trovate.has(m[1])) trovate.set(m[1], new Set())
        trovate.get(m[1]).add(relative(SRC, p))
      }
    }
  }
  cammina(SRC)
  return trovate
}

const { chiavi, funzioni } = contratto()
const lette = letture()
const fuori = [...lette.keys()].filter((k) => !chiavi.has(k)).sort()

console.log(`contratto: ${chiavi.size} chiavi da ${funzioni} capability (doc auto-gen)`)
console.log(`frontend:  ${lette.size} campi letti da un blob \`capabilities\``)

if (fuori.length > 0) {
  console.error(`\n[xx] ${fuori.length} campi che NESSUNA capability emette:\n`)
  for (const campo of fuori) {
    console.error(`  capabilities.${campo}`)
    for (const f of [...lette.get(campo)].sort()) console.error(`       ${f}`)
  }
  console.error('\n  Un refuso, oppure il database ha rinominato il campo.')
  console.error('  ⚠️ A video non si vedrebbe come un errore: il pulsante resta spento')
  console.error('     e sembra una regola. Confronta con la doc auto-gen della capability.')
  process.exit(1)
}
console.log('[ok] ogni campo letto dal blob e\' un campo che il database emette')
