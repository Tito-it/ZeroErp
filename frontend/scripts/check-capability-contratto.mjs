// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: Guard del CONTRATTO delle capability. Tre verifiche:
//        1. ogni campo che il frontend legge da un blob `capabilities.*` e'
//           un campo che una `script.fn_available_actions_*` (o la
//           `script.fn_capability_*` di promo) emette davvero;
//        2. idem per i nomi passati al BB `useEntityCapabilities`
//           (`flag('can_x')`, `editFlag: 'can_x'`, `azioneNegata('can_x')`
//           — per quest'ultima anche il suo motivo `can_x_reason[_key]`);
//        3. ⭐ IL CRICCHETTO DELLE LETTURE PIATTE (brief-be-fe-capability-
//           annidata §4.3): una chiave di primo livello del blob letta FUORI
//           da `capabilities` e' la forma che api.md §«Il blob sta SOTTO
//           `capabilities`» ha chiuso. Le sole ammesse sono gli omonimi
//           DICHIARATI in `capability-letture-piatte.json`, e possono solo
//           calare.
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
//   ⭐ DAL 2026-09-23 LA FORMA E' UNA: il blob sta sotto `capabilities`
//   (decisione Tid, api.md; conversione in brief-be-fe-capability-annidata).
//   Fino a quel giorno i dettagli di vendite lo fondevano nella testata
//   (`detail.can_x`), e li' il campo era indistinguibile da qualunque altro:
//   questo guard ne vedeva solo meta'. Ora vede tutte le letture annidate
//   (verifica 1-2) e conta quelle piatte rimaste (verifica 3).
//
//   ⛔ Il cricchetto NON conta «tutto cio' che somiglia a una capability».
//   E' stato PROVATO e scartato il 2026-09-23: su 46 token `can_*` del
//   frontend, 28 sono fuori dal contratto — capability di RIGA come
//   `can_remove`, predicati calcolati in Python come `can_esegui_ora`, flag
//   emessi da viste — e quasi nessuno e' un difetto. Criterio di AGENTS.md:
//   *un cancello che capisce un caso su cinque boccia a caso e passa a caso;
//   dopo due blocchi sbagliati qualcuno lo spegne.*
//   ⇒ Conta le sole chiavi di PRIMO LIVELLO del blob, lette dal
//   `RETURN jsonb_build_object(...)` della doc auto-gen: niente elenco
//   scritto qui. Gli omonimi (una chiave del blob che e' anche una colonna o
//   un campo di un'altra sorgente) si DICHIARANO nel registro, con il
//   motivo, e il registro e' verificato: una voce che non copre piu' niente
//   ferma il guard invece di restare a coprire il vuoto.
//
//   🔴 Il caso che ha fatto scrivere il cricchetto, trovato convertendo
//   (2026-09-23): `pdf` e' una chiave di primo livello del blob di cinque
//   documenti, e i drawer la passavano piatta a `EntityPdfButton`
//   (`:pdf="detail.pdf"`). Annidato il blob, il pulsante avrebbe perso il
//   `mode` senza nessun errore — e il conteggio del brief l'aveva data per
//   una chiave interna.
//
//   Uso:
//     node scripts/check-capability-contratto.mjs
//   Exit 1 al primo difetto (li elenca tutti).
// ------------------------------------------------------------

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))
const DOC = fileURLToPath(new URL('../../docs/it/dbzero/script/funzioni', import.meta.url))
const REGISTRO = fileURLToPath(new URL('./capability-letture-piatte.json', import.meta.url))
// ⚠️ Due famiglie di nomi per la stessa cosa: `fn_available_actions_*` per i
//    documenti con una matrice di stati, `fn_capability_promo_articolo` per la
//    promo (stato TEMPORALE, niente transizioni). Unificarle e' una decisione
//    DB che nessuno ha preso; qui si leggono entrambe.
const FUNZIONE_CAPABILITY = /^fn_(available_actions|capability)_.+\.md$/

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
//        Con `soloRitorno`, la sola chiamata del `RETURN`: le chiavi di PRIMO
//        livello del blob, cioe' quelle che una lettura piatta scambierebbe
//        per campi del dettaglio (un `key`/`label_key` di un'azione no).
function chiaviJsonb(corpo, { soloRitorno = false } = {}) {
  const chiavi = []
  const chiamata = soloRitorno ? /RETURN\s+jsonb_build_object\s*\(/gi : /jsonb_build_object\s*\(/gi
  for (const m of corpo.matchAll(chiamata)) {
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
  const primoLivello = new Set()
  let funzioni = 0
  for (const f of readdirSync(DOC).filter((n) => FUNZIONE_CAPABILITY.test(n))) {
    funzioni += 1
    const corpo = corpoFunzione(readFileSync(join(DOC, f), 'utf8'))
    for (const k of chiaviJsonb(corpo)) chiavi.add(k)
    // ⚠️ Chi delega (inventario, rettifica → documento_interno) non ha un
    //    `RETURN jsonb_build_object` suo: le sue chiavi sono quelle del
    //    delegato, che la scansione trova comunque.
    for (const k of chiaviJsonb(corpo, { soloRitorno: true })) primoLivello.add(k)
  }
  if (funzioni === 0) {
    console.error('[xx] nessuna capability nella doc auto-gen: contratto non leggibile.')
    console.error('     Il guard NON passa in silenzio: senza contratto non verifica niente.')
    process.exit(1)
  }
  // ⚠️ Funzioni trovate ma zero chiavi = il parser non capisce piu' la doc
  //    (formato cambiato): fallire, non passare in silenzio.
  if (chiavi.size === 0 || primoLivello.size === 0) {
    console.error('[xx] nessuna chiave di jsonb_build_object letta: parser della doc auto-gen da rivedere.')
    process.exit(1)
  }
  return { chiavi, primoLivello, funzioni }
}

// Scopo: i campi letti dal blob annidato, in tutte le forme in cui il
//        frontend ci arriva (`capabilities.x`, `capabilities.value.x`,
//        `capabilities?.x`, `caps.capabilities.x`).
const LETTURA = /\bcapabilities\s*(?:\?\.|\.)\s*(?:value\s*(?:\?\.|\.)\s*)?([a-z][a-z0-9_]*)/g
// Scopo: la stessa lettura con le parentesi (`capabilities.value['can_x']`).
//        Una chiave calcolata (`[\`${flag}_reason\`]`) non e' leggibile qui: la
//        copre la verifica di `azioneNegata` sotto.
const LETTURA_PARENTESI = /\bcapabilities\s*(?:\??\.\s*value\s*)?(?:\?\.)?\[\s*(['"`])([a-z][a-z0-9_]*)\1\s*\]/g
// Scopo: la DESTRUTTURAZIONE — `const { pdf, can_x: c } = <ricevente>`.
//        Un ricevente `capabilities` (o `.value`) e' una lettura annidata, e i
//        nomi si verificano sul contratto; qualunque altro ricevente e' una
//        lettura PIATTA, e si conta nel cricchetto.
// ⚠️ Solo l'assegnazione (`} =`, non `=>`/`==`), a un livello di graffe: la
//    destrutturazione di un PARAMETRO (`({ pdf }) =>`) non dice da dove viene
//    l'oggetto, e resta fuori — limite dichiarato, non un buco nascosto.
const DESTRUTTURAZIONE = /\{([^{}]*)\}\s*=(?![=>])\s*([^;\n]+)/g
const RICEVENTE_BLOB = /^\s*(?:[\w$.?]+\.)?capabilities(?:\s*\??\.\s*value)?\b/
// ⚠️ `value` e' l'unwrap di un ref, non un campo del blob: la regex lo
//    attraversa, e se compare da solo non e' un campo da verificare.
const NON_CAMPI = new Set(['value'])
// Scopo: i nomi passati al BB — `flag('can_x')` e `editFlag: 'can_x'` — nei
//        soli file che lo importano (`flag(` da solo e' un nome qualunque).
const ARGOMENTO_BB = /(?:\b(?:flag|azioneNegata)\s*\(\s*|\beditFlag\s*:\s*)['"]([a-z][a-z0-9_]*)['"]/g
// Scopo: `azioneNegata('can_x', …)` legge anche `can_x_reason` /
//        `can_x_reason_key` con una chiave calcolata: almeno uno dei due deve
//        stare nel contratto, o il pulsante negato non comparira' mai.
const ARGOMENTO_NEGATA = /\bazioneNegata\s*\(\s*['"]([a-z][a-z0-9_]*)['"]/g
const IMPORTA_BB = /\buseEntityCapabilities\b/
// Scopo: una chiave di i18n (`'vendite.ddt.pdf.dialog_title'`) contiene
//        `.pdf` ma non e' una lettura: le chiavi puntate si tolgono prima di
//        cercare le letture piatte. Solo quelle — togliere OGNI stringa
//        accecherebbe il guard sulle espressioni dei template.
// ⛔ Apici SINGOLI e backtick, mai i doppi: fra doppi apici stanno le
//    espressioni dei template, e `:pdf="detail.pdf"` ha la stessa forma di
//    una chiave puntata. Con i doppi il guard era cieco proprio sul caso per
//    cui e' nato (provato per mutazione, 2026-09-23). Una chiave i18n fra
//    doppi apici in uno script (prettier li normalizza) darebbe un rosso
//    visibile, non un buco.
const CHIAVE_I18N = /(['`])[a-z0-9_]+(?:\.[a-z0-9_]+)+\1/g
// Scopo: il valore di un attributo STATICO del template (`i18n-prefix=
//        "vendite.ddt.pdf"`) e' testo, non un'espressione: si toglie. Quelli
//        legati (`:x`, `v-x`, `@x`, `#x`) restano, perche' sono codice.
const ATTRIBUTO_STATICO = /(\s)(?![:@#]|v-)([a-zA-Z][\w-]*)="[^"]*"/g

function sorgenti() {
  const out = []
  const cammina = (dir) => {
    for (const nome of readdirSync(dir).sort()) {
      const p = join(dir, nome)
      if (statSync(p).isDirectory()) { cammina(p); continue }
      if (!/\.(vue|js)$/.test(nome) || nome.endsWith('.spec.js')) continue
      out.push({ rel: relative(SRC, p).split(sep).join('/'), src: senzaCommenti(readFileSync(p, 'utf8')) })
    }
  }
  cammina(SRC)
  return out
}

// Scopo: {campo: Set<file>} delle letture che finiscono fuori contratto.
function aggiungi(mappa, campo, file) {
  if (!mappa.has(campo)) mappa.set(campo, new Set())
  mappa.get(campo).add(file)
}

// Scopo: le letture PIATTE di una chiave di primo livello: `.chiave` (o
//        `?.chiave`) il cui ricevente NON e' `capabilities` / `capabilities.value`.
// ⚠️ Il secondo lookbehind non e' ridondante: senza, `capabilities?.x` verrebbe
//    letto partendo dal `.` dopo il `?`, dove il primo non vede piu' il
//    ricevente — e una lettura GIUSTA risulterebbe piatta.
//        Contano anche l'accesso con parentesi (`detail['pdf']`) e la
//        destrutturazione da un ricevente che non e' il blob.
function letturePiatte(src, primoLivello) {
  const pulito = src.replace(CHIAVE_I18N, "''").replace(ATTRIBUTO_STATICO, '$1$2=""')
  const destrutturate = nomiDestrutturati(pulito).filter((d) => !d.blob)
  const conteggio = {}
  for (const k of primoLivello) {
    const punto = new RegExp(
      String.raw`(?<!\bcapabilities\s*(?:\??\.\s*value\s*)?)(?<!\?)\??\.\s*${k}\b`, 'g',
    )
    const parentesi = new RegExp(
      String.raw`(?<!\bcapabilities\s*(?:\??\.\s*value\s*)?)(?<!\?)(?:\?\.)?\[\s*(['"\x60])${k}\1\s*\]`, 'g',
    )
    const n = [...pulito.matchAll(punto)].length + [...pulito.matchAll(parentesi)].length
      + destrutturate.filter((d) => d.nome === k).length
    if (n > 0) conteggio[k] = n
  }
  return conteggio
}

// Scopo: i nomi di ogni destrutturazione per assegnazione, col flag `blob` se
//        il ricevente e' `capabilities`. `{ a: alias, b = 1, ...resto }` →
//        `a`, `b` (il resto non e' un nome del blob).
function nomiDestrutturati(src) {
  const out = []
  for (const m of src.matchAll(DESTRUTTURAZIONE)) {
    const blob = RICEVENTE_BLOB.test(m[2])
    for (const parte of m[1].split(',')) {
      const nome = parte.trim().split(/\s*[:=]\s*/)[0]
      if (/^[a-z][a-z0-9_]*$/.test(nome)) out.push({ nome, blob })
    }
  }
  return out
}

const { chiavi, primoLivello, funzioni } = contratto()
const registro = JSON.parse(readFileSync(REGISTRO, 'utf8'))
const echi = registro.echi ?? {}
const dichiarate = registro.piatte ?? {}

const lette = new Map()
const argomentiFuori = new Map()
const piatte = {}
for (const { rel, src } of sorgenti()) {
  for (const m of src.matchAll(LETTURA)) if (!NON_CAMPI.has(m[1])) aggiungi(lette, m[1], rel)
  for (const m of src.matchAll(LETTURA_PARENTESI)) aggiungi(lette, m[2], rel)
  for (const d of nomiDestrutturati(src)) if (d.blob) aggiungi(lette, d.nome, rel)
  if (IMPORTA_BB.test(src)) {
    for (const m of src.matchAll(ARGOMENTO_BB)) if (!chiavi.has(m[1])) aggiungi(argomentiFuori, m[1], rel)
    for (const m of src.matchAll(ARGOMENTO_NEGATA)) {
      if (!chiavi.has(`${m[1]}_reason`) && !chiavi.has(`${m[1]}_reason_key`)) {
        aggiungi(argomentiFuori, `${m[1]}_reason[_key]`, rel)
      }
    }
  }
  const conteggio = letturePiatte(src, [...primoLivello].filter((k) => !(k in echi)))
  if (Object.keys(conteggio).length) piatte[rel] = conteggio
}

let rosso = false

console.log(`contratto: ${chiavi.size} chiavi da ${funzioni} capability (doc auto-gen), ${primoLivello.size} di primo livello`)
console.log(`frontend:  ${lette.size} campi letti da un blob \`capabilities\``)

// ── 1-2. Il contratto ─────────────────────────────────────────────
// ⚠️ `argomentiFuori` e' gia' filtrato sul contratto mentre si legge; `lette`
//    raccoglie tutto (serve al conteggio in testa) e si filtra qui.
for (const [mappa, forma] of [[lette, 'capabilities.'], [argomentiFuori, 'flag/editFlag/azioneNegata: ']]) {
  const campi = [...mappa.keys()].filter((k) => !chiavi.has(k)).sort()
  if (campi.length === 0) continue
  rosso = true
  console.error(`\n[xx] ${campi.length} campi che NESSUNA capability emette:\n`)
  for (const campo of campi) {
    console.error(`  ${forma}${campo}`)
    for (const f of [...mappa.get(campo)].sort()) console.error(`       ${f}`)
  }
  console.error('\n  Un refuso, oppure il database ha rinominato il campo.')
  console.error('  ⚠️ A video non si vedrebbe come un errore: il pulsante resta spento')
  console.error('     e sembra una regola. Confronta con la doc auto-gen della capability.')
}

// ── 3. Il cricchetto delle letture piatte ─────────────────────────
// ⛔ Il registro si VERIFICA: un'eco che non e' piu' una chiave del blob
//    esenterebbe un nome qualunque, cioe' coprirebbe il vuoto.
const echiSpariti = Object.keys(echi).filter((k) => !primoLivello.has(k))
if (echiSpariti.length) {
  rosso = true
  console.error(`\n[xx] ${echiSpariti.length} \`echi\` del registro non sono piu' chiavi di primo livello del blob:`)
  for (const k of echiSpariti) console.error(`       · ${k}`)
  console.error('     Il database li ha tolti o rinominati: la voce va tolta, o esenta il vuoto.')
}
const nuove = []
const calate = []
for (const file of new Set([...Object.keys(piatte), ...Object.keys(dichiarate)])) {
  const ora = piatte[file] ?? {}
  const prima = dichiarate[file]?.chiavi ?? {}
  for (const k of new Set([...Object.keys(ora), ...Object.keys(prima)])) {
    const n = ora[k] ?? 0
    const atteso = prima[k] ?? 0
    if (n > atteso) nuove.push(`${file}  .${k}  (${n}, registro ${atteso})`)
    if (n < atteso) calate.push(`${file}  .${k}  (${n}, registro ${atteso})`)
  }
}
const totale = Object.values(piatte).reduce((t, c) => t + Object.values(c).reduce((a, b) => a + b, 0), 0)
console.log(`piatte:    ${totale} letture di una chiave del blob fuori da \`capabilities\`` +
  (nuove.length ? '' : ', tutte omonimi dichiarati'))
if (nuove.length) {
  rosso = true
  console.error(`\n[xx] ${nuove.length} letture PIATTE di una chiave del blob, non dichiarate:\n`)
  for (const r of nuove) console.error(`       + ${r}`)
  console.error('\n  Il blob sta SOTTO `capabilities` (api.md): si legge `capabilities.x`, o')
  console.error('  il BB `useEntityCapabilities`. Se invece e\' un OMONIMO — stesso nome,')
  console.error('  altra sorgente (una colonna, il registro dei lock) — si dichiara in')
  console.error('  scripts/capability-letture-piatte.json, col motivo.')
}
if (calate.length) {
  rosso = true
  console.error(`\n[xx] ${calate.length} voci del registro in MENO di quelle dichiarate — buona notizia,`)
  console.error('     ma il registro va abbassato, o resta lo spazio per rimetterle:\n')
  for (const r of calate) console.error(`       - ${r}`)
}

if (rosso) process.exit(1)
console.log('[ok] ogni campo letto dal blob e\' un campo che il database emette, e nessuna lettura piatta in piu\'')
