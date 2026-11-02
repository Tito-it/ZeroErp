// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ IL QUINTO GUARD DEL FRONTEND — una view che vive sotto `<KeepAlive>`
//        non puo' restare senza un `onActivated`, ne' suo ne' portato da un
//        composable.
//
// 🔴 PERCHE' ESISTE (2026-09-10). `AppLayout.vue` monta le view di dominio
//    dentro `<KeepAlive :max="10">`. Una view tenuta in cache NON ri-esegue
//    `onMounted` quando ci si torna: ri-esegue `onActivated`. ⇒ Si apre una
//    lista, si crea qualcosa da un'altra scheda, si torna: a video c'e' l'elenco
//    di prima. Nessun errore, nessuna riga di log.
//    ⚠️ E il `:max="10"` lo rende INTERMITTENTE, che e' la parte peggiore: con
//    undici o piu' view visitate la LRU ne sfratta una, e quella rimontata si
//    ricarica e sembra corretta. Un difetto che si riproduce a giorni alterni
//    non viene creduto.
//
// ⛔ DUE CRITERI DERIVATI, NESSUN ELENCO SCRITTO A MANO. Un elenco diverge al
//    primo file nuovo, e il presidio nascerebbe cieco proprio sulla view appena
//    aggiunta — cioe' sul caso per cui serve.
//
//    1) CHI STA SOTTO KEEPALIVE si legge da `router/index.js`: le rotte FIGLIE
//       di `AppLayout`. Quelle di primo livello (login, attivazioni, reset
//       password) non ci stanno, e per loro `onActivated` non scatterebbe mai.
//
//    2) CHI E' GIA' COPERTO si legge dai COMPOSABLE. `useSearchTable` ha un
//       `onActivated` che salta la prima attivazione (per non raddoppiare il
//       fetch del mount) e dalla seconda in poi rinfresca; `useListaConfigurabilePage`
//       lo usa. ⇒ Una view che passa di li' il rientro ce l'ha GIA', e
//       aggiungerle un `onActivated` proprio farebbe DUE fetch a ogni rientro.
//       La copertura si risolve in modo TRANSITIVO, perche' e' cosi' che
//       arriva: view → `useListaConfigurabilePage` → `useSearchTable`.
//
// ⚠️ E il criterio 2 non e' teoria: il 2026-09-10 questo guard, nella sua prima
//    forma (senza la risoluzione transitiva), ha dichiarato violate OTTO view
//    che erano a posto. La stessa svista aveva portato a convertirle, e le
//    conversioni sono state annullate. *Un presidio che non sa da dove arriva la
//    difesa segnala la difesa come un difetto.*
//
// ⚠️ L'ESENZIONE SI DICHIARA, non si spiega in prosa: `// keepalive-onmounted:
//    voluto — <motivo>` per un `onMounted` che NON deve ripetersi al rientro.
//
// Uso: node scripts/check-keepalive-onactivated.mjs   (o `npm run guards`)
// ------------------------------------------------------------

import { readFileSync, existsSync, readdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import process from 'node:process'

const QUI = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(QUI, '../src')
const ROUTER = resolve(SRC, 'router/index.js')
const COMPOSABLES = resolve(SRC, 'core/composables')
const ESENZIONE = /\/\/\s*keepalive-onmounted:\s*voluto\b/
const CHIAMA_ONACTIVATED = /\bonActivated\s*\(/
const CHIAMA_ONMOUNTED = /\bonMounted\s*\(/

// ⛔ SI GUARDA IL CODICE, NON LA PROSA — e in questo repo non e' un dettaglio:
//    i commenti NOMINANO di continuo `onActivated`, `onMounted` e i composable
//    dello scaffolding (`useSearchTable` compare in commento in una trentina di
//    file che non lo chiamano). Un presidio che cerca una stringa nel sorgente
//    si accende sulla frase che spiega il difetto invece che sul difetto — e'
//    la stessa lezione gia' pagata a backend sul guardrail dei seed lista
//    (`_sorgente_senza_commenti`, 2026-08-26).
// ⚠️ Il verso in cui sbaglierebbe e' il PEGGIORE: una view che spiega in un
//    commento perche' NON usa `useSearchTable` verrebbe dichiarata «coperta
//    dallo scaffolding», cioe' il guard confermerebbe il difetto invece di
//    trovarlo. Verde per cecita'.
// Scopo: il sorgente senza commenti di riga, di blocco e HTML (i `.vue` ne
//        hanno di tutti e tre i tipi). Le stringhe non si toccano: un nome di
//        composable dentro una stringa non esiste, in pratica.
function senzaCommenti(sorgente) {
  return sorgente
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/(^|[^:])\/\/.*$/gm, '$1')
}

// ── 1. Quali composable PORTANO un `onActivated`, transitivamente ────────────
const usa = new Map()      // composable -> altri composable che importa
const diretto = new Set()  // composable che chiama onActivated di suo
for (const f of readdirSync(COMPOSABLES).filter((n) => n.endsWith('.js'))) {
  const nome = f.replace(/\.js$/, '')
  const s = senzaCommenti(readFileSync(resolve(COMPOSABLES, f), 'utf8'))
  if (CHIAMA_ONACTIVATED.test(s)) diretto.add(nome)
  usa.set(nome, [...s.matchAll(/from\s+'\.\/(use[A-Za-z0-9_]+)'/g)].map((m) => m[1]))
}
const copre = new Set(diretto)
for (let cambiato = true; cambiato; ) {
  cambiato = false
  for (const [nome, importati] of usa) {
    if (!copre.has(nome) && importati.some((i) => copre.has(i))) {
      copre.add(nome); cambiato = true
    }
  }
}

// ── 2. Quali view stanno sotto KeepAlive ─────────────────────────────────────
const router = readFileSync(ROUTER, 'utf8')
const children = [...router.matchAll(/\bchildren:\s*\[/g)]
if (children.length !== 1) {
  console.error(
    `[ko] router/index.js ha ${children.length} blocchi \`children:\`: questo guard ne assume UNO\n` +
    '     (quello di AppLayout) per dividere le rotte sotto KeepAlive da quelle di primo\n' +
    '     livello. Va aggiornato il criterio, non disattivato il controllo.',
  )
  process.exit(2)
}
const taglio = children[0].index

// ⚠️ Si accettano `../` e l'alias `@/`: oggi il router usa solo la prima forma,
//    ma un guard che conosce una sola convenzione diventa cieco il giorno in cui
//    si adotta l'altra — e lo diventa in silenzio, che e' il modo peggiore.
const riferimenti = []
for (const m of router.matchAll(/import\(\s*['"]((?:\.\.\/|@\/)[^'"]+\.vue)['"]\s*\)/g)) {
  riferimenti.push({ percorso: m[1], pos: m.index })
}
for (const m of router.matchAll(/^import\s+(\w+)\s+from\s+['"]((?:\.\.\/|@\/)[^'"]+\.vue)['"]/gm)) {
  // ⚠️ TUTTI gli usi, non il primo: lo stesso componente puo' stare su due
  //    rotte, una di primo livello e una figlia — con `indexOf` la seconda
  //    sparirebbe dal perimetro.
  for (const u of router.matchAll(new RegExp(`component:\\s*${m[1]}\\b`, 'g'))) {
    riferimenti.push({ percorso: m[2], pos: u.index })
  }
}

// ⛔ IL PRESIDIO DEL PRESIDIO: se le rotte dichiarate sono piu' dei riferimenti
//    risolti, questo guard sta guardando meno di quello che crede — e senza
//    questo confronto non lo direbbe nessuno.
const rotteDichiarate = [...router.matchAll(/\bcomponent:/g)].length
if (riferimenti.length < rotteDichiarate) {
  console.error(
    `[ko] router/index.js dichiara ${rotteDichiarate} rotte ma questo guard ne ha risolte\n` +
    `     ${riferimenti.length}: ${rotteDichiarate - riferimenti.length} sfuggono al criterio (una forma di import\n` +
    '     non prevista?). Il perimetro va riallineato, non ridotto in silenzio.',
  )
  process.exit(2)
}
const sotto = [...new Set(riferimenti.filter((r) => r.pos > taglio).map((r) => r.percorso))]
const top = new Set(riferimenti.filter((r) => r.pos < taglio).map((r) => r.percorso))

// ── 3. Il controllo ──────────────────────────────────────────────────────────
const violazioni = []
const esentate = []
const coperte = []
const irrisolti = []
for (const rel of sotto.sort()) {
  const file = rel.startsWith('@/') ? resolve(SRC, rel.slice(2)) : resolve(SRC, 'router', rel)
  // ⛔ Un percorso che non risolve NON si salta in silenzio: sarebbe una view
  //    uscita dal perimetro senza che nessuno lo dica — il modo in cui un
  //    presidio smette di guardare proprio cio' per cui era nato.
  if (!existsSync(file)) { irrisolti.push(rel); continue }
  const originale = readFileSync(file, 'utf8')
  const s = senzaCommenti(originale)
  if (!CHIAMA_ONMOUNTED.test(s)) continue          // non carica al mount: niente da dire
  if (CHIAMA_ONACTIVATED.test(s)) continue         // ce l'ha di suo
  const nome = file.slice(SRC.length + 1)
  // ⚠️ CHIAMATO, non nominato: `useX(` e non `useX`. Il nome da solo compare
  //    nella prosa di decine di file che quel composable non lo usano.
  const tramite = [...copre].filter((c) => new RegExp(`\\b${c}\\s*\\(`).test(s))
  if (tramite.length) { coperte.push(`${nome}  ←  ${tramite.join(', ')}`); continue }
  // ⚠️ L'esenzione si cerca nel sorgente ORIGINALE: e' un commento, e sul testo
  //    ripulito non esisterebbe piu'.
  if (ESENZIONE.test(originale)) { esentate.push(nome); continue }
  violazioni.push(nome)
}

console.log(
  `view sotto <KeepAlive>: ${sotto.length}  |  di primo livello (esenti per costruzione): ${top.size}\n` +
  `composable che portano un onActivated: ${copre.size} (${[...copre].sort().join(', ')})`,
)
for (const c of coperte) console.log(`[--] coperta dallo scaffolding: ${c}`)
for (const e of esentate) console.log(`[--] esenzione dichiarata: ${e}`)

if (irrisolti.length) {
  console.error(
    `\n[ko] ${irrisolti.length} rotte puntano a file che non esistono a questo percorso:\n` +
    irrisolti.map((r) => `       · ${r}`).join('\n') +
    '\n\n     Non e\' una svista da saltare: finche\' restano, quelle view non le guarda\n' +
    '     nessuno — ne\' questo guard ne\' il router al primo caricamento.',
  )
  process.exit(2)
}

if (violazioni.length) {
  console.error(
    '\n[ko] Queste view vivono sotto `<KeepAlive>`, caricano in `onMounted` e nessuno\n' +
    '     porta loro un `onActivated`:\n' +
    violazioni.map((v) => `       · ${v}`).join('\n') +
    '\n\n     Al rientro non ricaricano: a video resta l\'elenco di prima, senza errore.\n' +
    '     ⇒ Sposta il caricamento in `onActivated` (SOSTITUISCE `onMounted`: sotto\n' +
    '       KeepAlive al primo montaggio scattano entrambi, quindi tenerli tutti e\n' +
    '       due farebbe due fetch).\n' +
    '     ⇒ Se l\'`onMounted` e\' voluto e non deve ripetersi, dichiaralo:\n' +
    '       `// keepalive-onmounted: voluto — <motivo>`',
  )
  process.exit(1)
}

console.log('[ok] ogni view sotto KeepAlive ha un onActivated, suo o dello scaffolding')
