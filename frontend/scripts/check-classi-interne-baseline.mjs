// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: ⭐ IL REGISTRO DEGLI AGGANCI AL DOM INTERNO DI PRIMEVUE — un
//        cricchetto che, fuori dalle sedi, puo' solo calare.
//
// 🔴 PERCHE' ESISTE (2026-11-14, P1 del piano-migrazione-primevue-5 §8-bis
//    «Predisposizione»). Il nostro codice aggancia la struttura INTERNA dei
//    componenti PrimeVue in due modi: le classi generate (`.p-datatable-tbody`,
//    `.p-menu-item-link`, …) e gli attributi pass-through (`[data-pc-section=…]`).
//    Sono l'aggancio che si rompe SENZA che il build lo dica: se una versione
//    nuova — o un fork, o un'altra libreria — rinomina una classe, il selettore
//    non prende piu' niente e il componente torna nudo, in silenzio.
//    Qualunque uscita da PrimeVue li paga tutti, uno per uno.
//
// ⭐ IL CONFINE E' SUL MODELLO: ogni aggancio fuori da una SEDE e' una
//    dipendenza dalla libreria sparsa in un componente qualunque. Le sedi sono i
//    file il cui mestiere e' vestire i componenti di PrimeVue (i fogli globali,
//    i gusci che incarnano un componente): li' l'aggancio e' a casa, e si
//    migra in un posto solo. Fuori dalle sedi il registro:
//      · **cresce** → rosso, e nomina la coppia file → aggancio nuova;
//      · **cala**   → rosso anche questo: si abbassa con `--baseline`, o resta
//        lo spazio per rimetterlo;
//      · **uguale** → verde.
//
// ⭐ L'UNITA' E' LA COPPIA file → aggancio, non il file. Un file gia' in
//    registro che aggancia una classe NUOVA e' una dipendenza nuova, e va vista.
//
// ⛔ I COMMENTI NON SONO AGGANCI. Un commento che NOMINA `.p-tabpanel` per
//    spiegare una regola non dipende da niente: contato, il registro direbbe
//    una cosa diversa da quella che sembra (al 2026-11-14 erano 8 file su 21,
//    agganciati solo a parole). Si tolgono prima di cercare: `/* … */` nei CSS,
//    `/* … */` e `// …` negli script, `<!-- … -->` nei template.
// ⭐ GLI SCRIPT SI', invece: `el.querySelector('.p-row-toggler')` e' lo stesso
//    aggancio scritto in JavaScript, e si rompe allo stesso modo. Si leggono
//    i `.vue` interi e i `.js` di `src/`. ⚠️ Fuori i `.spec.js`: un selettore
//    di test che non trova piu' l'elemento fa fallire il test, cioe' non cede
//    in silenzio — e' gia' presidiato.
//
//   Uso:
//     node scripts/check-classi-interne-baseline.mjs             # confronto
//     node scripts/check-classi-interne-baseline.mjs --baseline  # riscrive il registro
// ------------------------------------------------------------

import { readFileSync, writeFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, relative, sep } from 'node:path'
import process from 'node:process'

const QUI = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(QUI, '../src')
const REGISTRO = resolve(QUI, 'classi-interne.baseline.json')
const riscrive = process.argv.includes('--baseline')

// Le due forme dell'aggancio. ⚠️ `\.p-` e non `p-`: `--p-primary-color` (le
//    variabili del tema, R4 del piano) e `class="p-invalid"` sono altre cose.
const CLASSE = /\.p-[a-z0-9-]+/g
// `[data-pc-section="rowtogglebutton"]`, `[data-pc-name=dialog]`, `[data-pc-section]`:
//    il valore si normalizza senza apici, cosi' la stessa coppia non conta due
//    volte per un cambio di virgolette.
const ATTRIBUTO = /\[\s*(data-pc-[a-z-]+)\s*(?:([~|^$*]?=)\s*['"]?([^'"\]\s]*)['"]?)?\s*\]/g

// Scopo: i file da leggere sotto src/, in ordine stabile (il registro e' un
//        file committato: un ordine ballerino lo renderebbe un diff illeggibile).
function fileSorgente(dir) {
  const out = []
  for (const nome of readdirSync(dir).sort()) {
    const p = resolve(dir, nome)
    if (statSync(p).isDirectory()) out.push(...fileSorgente(p))
    else if (/\.(vue|css)$/.test(nome)) out.push(p)
    else if (/\.(js|ts)$/.test(nome) && !/\.(spec|test)\.(js|ts)$/.test(nome)) out.push(p)
  }
  return out
}

// Scopo: il CSS senza commenti. In CSS `/* */` e' l'unico commento.
function senzaCommentiCss(s) {
  return s.replace(/\/\*[\s\S]*?\*\//g, ' ')
}

// Scopo: lo script senza commenti.
// ⚠️ Un commento si riconosce solo dove puo' cominciare: inizio riga o dopo uno
//    spazio. `accept: 'image/*'` o `'http://…'` restano dentro: scambiarli per
//    l'inizio di un commento inghiottirebbe il codice che segue, e un
//    cricchetto cieco su un tratto di file e' il modo in cui si allenta senza
//    che nessuno lo decida. Nel dubbio si CONTA: un falso positivo e' rosso e
//    si vede, un falso negativo no.
function senzaCommentiJs(s) {
  return s
    .replace(/(^|\s)\/\*[\s\S]*?\*\//g, '$1 ')
    .replace(/(^|\s)\/\/.*$/gm, '$1')
}

// Scopo: il testo in cui cercare, per tipo di file. Un `.vue` si divide nei
//        suoi blocchi, ognuno col suo linguaggio di commento.
function testoUtile(p, s) {
  if (p.endsWith('.css')) return senzaCommentiCss(s)
  if (!p.endsWith('.vue')) return senzaCommentiJs(s)
  const parti = []
  const resto = s
    .replace(/<style\b[^>]*>([\s\S]*?)<\/style>/g, (_, css) => {
      parti.push(senzaCommentiCss(css))
      return ' '
    })
    .replace(/<script\b[^>]*>([\s\S]*?)<\/script>/g, (_, js) => {
      parti.push(senzaCommentiJs(js))
      return ' '
    })
  parti.push(resto.replace(/<!--[\s\S]*?-->/g, ' '))
  return parti.join('\n')
}

// Scopo: gli agganci di un testo, distinti e in ordine.
function agganci(testo) {
  const trovati = new Set(testo.match(CLASSE) ?? [])
  for (const m of testo.matchAll(ATTRIBUTO)) {
    trovati.add(m[2] ? `[${m[1]}${m[2]}${m[3]}]` : `[${m[1]}]`)
  }
  return [...trovati].sort()
}

// ⭐ LE DUE ESENZIONI SONO DICHIARATE A MANO, e verificate sotto.
//    · `sedi` — {file: motivo}: i file dove agganciare il DOM di PrimeVue e' il
//      mestiere. Un criterio automatico («sta in assets/», «sta in
//      core/components») esenterebbe anche chi il debito ce l'ha davvero.
//    · `selettori_nostri` — {aggancio: motivo}: nomi che hanno la forma di
//      PrimeVue ma li scegliamo NOI. `.p-dark` e' il `darkModeSelector` che
//      `main.js` passa al tema: nessuna versione della libreria lo rinomina.
// ⚠️ `--baseline` le RIPORTA e non le ricalcola: sono decisioni, e un comando di
//    manutenzione non deve poterle svuotare per distrazione.
function leggiRegistro() {
  if (!existsSync(REGISTRO)) return {}
  return JSON.parse(readFileSync(REGISTRO, 'utf8'))
}
const registro = leggiRegistro()
const SEDI = registro.sedi ?? {}
const NOSTRI = registro.selettori_nostri ?? {}

const fuoriSede = {}
const inSede = {}
const nostriTrovati = new Set()
const fileTrovati = new Set()
for (const p of fileSorgente(SRC)) {
  const rel = relative(SRC, p).split(sep).join('/')
  fileTrovati.add(rel)
  const trovati = agganci(testoUtile(p, readFileSync(p, 'utf8')))
  const propri = trovati.filter((a) => {
    if (a in NOSTRI) { nostriTrovati.add(a); return false }
    return true
  })
  if (!propri.length) continue
  if (rel in SEDI) inSede[rel] = propri
  else fuoriSede[rel] = propri
}

// ⛔ L'ESENZIONE SI VERIFICA, o smette di essere un'esenzione e diventa un buco.
//    Una sede rinominata lascerebbe una riga che non copre piu' niente, e il
//    prossimo file che prendesse quel nome sarebbe esente per caso. Una sede
//    SENZA agganci invece e' ammessa: `AppDialog` oggi non ne ha, ed e' li' che
//    andra' il primo che serve al chrome dei dialog.
//    Un selettore nostro che nessuno usa piu' e' una riga che esenta il vuoto:
//    il giorno che PrimeVue introducesse una classe con quel nome, non la
//    vedremmo.
const sediSparite = Object.keys(SEDI).filter((f) => !fileTrovati.has(f))
const nostriSpariti = Object.keys(NOSTRI).filter((a) => !nostriTrovati.has(a))
if (sediSparite.length || nostriSpariti.length) {
  if (sediSparite.length) {
    console.error(
      `[ko] ${sediSparite.length} voci di \`sedi\` non corrispondono piu' a un file:\n` +
      sediSparite.map((f) => `       · ${f}`).join('\n') +
      '\n     Il file e stato rinominato o tolto: la voce va corretta o tolta.',
    )
  }
  if (nostriSpariti.length) {
    console.error(
      `[ko] ${nostriSpariti.length} voci di \`selettori_nostri\` non sono piu' usate da nessuno:\n` +
      nostriSpariti.map((a) => `       · ${a}`).join('\n') +
      '\n     La voce va tolta: esenta un nome che non usiamo piu.',
    )
  }
  process.exit(2)
}

const coppie = (mappa) =>
  Object.entries(mappa).flatMap(([f, as]) => as.map((a) => `${f} → ${a}`))
const nCoppieSedi = coppie(inSede).length

if (riscrive) {
  writeFileSync(
    REGISTRO,
    JSON.stringify(
      {
        _scopo:
          'Registro degli agganci al DOM interno di PrimeVue (classi `.p-*` e ' +
          'attributi `data-pc-*`) FUORI dalle sedi. PUO SOLO CALARE: il guard e ' +
          'rosso sia se cresce (una dipendenza nuova dalla libreria in un ' +
          'componente qualunque) sia se cala senza che questo file sia stato ' +
          'riscritto. Si riscrive con `--baseline`, e la ragione va nel messaggio ' +
          'di commit. `sedi` e `selettori_nostri` sono decisioni scritte a mano.',
        _regola:
          'docs/it/dev/work-in-progress/piano-migrazione-primevue-5.md §8-bis ' +
          '«Predisposizione», P1; frontend-standards §«Regole CSS per i componenti»',
        sedi: SEDI,
        selettori_nostri: NOSTRI,
        agganci: fuoriSede,
      },
      null,
      2,
    ) + '\n',
  )
  console.log(
    `[ok] registro riscritto: ${coppie(fuoriSede).length} agganci in ` +
    `${Object.keys(fuoriSede).length} file fuori dalle sedi ` +
    `(${nCoppieSedi} nelle sedi, non registrati)`,
  )
  process.exit(0)
}

if (!existsSync(REGISTRO)) {
  console.error(`[ko] registro assente (${REGISTRO}): crealo con --baseline`)
  process.exit(1)
}

const prima = new Set(coppie(registro.agganci ?? {}))
const ora = coppie(fuoriSede)
const nuovi = ora.filter((c) => !prima.has(c))
const spariti = [...prima].filter((c) => !ora.includes(c))

console.log(
  `agganci fuori dalle sedi: ${ora.length} in ${Object.keys(fuoriSede).length} file ` +
  `(registro: ${prima.size}) · nelle sedi: ${nCoppieSedi}`,
)

let rosso = false
if (nuovi.length) {
  rosso = true
  console.error(
    `\n[ko] ${nuovi.length} agganci al DOM interno di PrimeVue in piu' rispetto al registro:\n` +
    nuovi.map((c) => `       + ${c}`).join('\n') +
    '\n\n     Una classe `.p-*` (o un `data-pc-*`) in un componente qualunque e una\n' +
    '     dipendenza dalla libreria che nessun build segnala, e che un aggiornamento\n' +
    '     rompe in silenzio. Il suo posto e una sede: una classe `app-*` in\n' +
    '     `main.css`, un token in `theme.css`, o il building block che incarna il\n' +
    '     componente. Se il file E una sede, si dichiara in `sedi` col motivo.\n' +
    '     ⛔ Non sono motivi: «e solo un ritocco», «e scoped», «serve solo qui».',
  )
}
if (spariti.length) {
  rosso = true
  console.error(
    `\n[ko] ${spariti.length} agganci in MENO — e una buona notizia, ma il registro\n` +
    '     va abbassato, altrimenti resta lo spazio per rimetterli:\n' +
    spariti.map((c) => `       - ${c}`).join('\n') +
    '\n\n     ⇒ node scripts/check-classi-interne-baseline.mjs --baseline\n' +
    '       (e la ragione nel messaggio di commit)',
  )
}

if (rosso) process.exit(1)
console.log('[ok] registro degli agganci invariato: nessuna dipendenza nuova dal DOM di PrimeVue')
