// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: ⭐ IL VERSO DEL REGISTRO DELLE `DataTable` GREZZE — un cricchetto che
//        può solo calare.
//
// 🔴 PERCHE' ESISTE (2026-09-10). `.codex/AGENTS.md` apre con la regola zero
//    della lista — *«una lista si monta con `<ListaConfigurabile>`, importare
//    `primevue/datatable` in una view è l'ECCEZIONE e va motivata in un
//    commento sopra l'import»* — e chiude con la verifica:
//
//        grep -rl "from 'primevue/datatable'" frontend/src --include=*.vue | wc -l
//        «Se il numero SALE dopo il tuo lavoro, hai aggiunto una lista fuori standard.»
//
//    ⛔ Ma quel numero non lo confronta nessuno con niente. «Sale» rispetto a
//    cosa? A una cifra che chi legge dovrebbe ricordare a memoria. Ed e' andata
//    come doveva: **48 il 03-08, risalite a 57 il 30-08**, poi di nuovo 48.
//    Un registro senza un verso non e' un registro: e' una lista, e una lista
//    che nessuno confronta non ferma niente.
//
// ⭐ QUI IL NUMERO DIVENTA UN CANCELLO, e il verso e' scritto nel comportamento:
//      · **cresce** → rosso, e dice QUALI file sono nuovi;
//      · **cala**   → rosso anche questo, con un altro messaggio: abbassa la
//        baseline. ⚠️ Non e' pedanteria — una baseline che resta alta dopo un
//        miglioramento **riapre lo spazio che si era appena chiuso**, in
//        silenzio. Un cricchetto che non si stringe non e' un cricchetto.
//      · **uguale** → verde.
//
// ⭐ E LA BASELINE ELENCA I FILE, non conta e basta: cosi' il messaggio dice
//    quale file e' comparso, e il `git diff` del registro si legge.
//
// ⚠️ DUE SOGLIE, non una. La regola chiede DUE cose — che le eccezioni siano
//    poche E che ognuna sia motivata — e la seconda oggi e' rispettata da 14 su
//    48. Tenerle separate permette di far calare quella che si puo' far calare
//    adesso (scrivere un commento costa una riga) senza aspettare la
//    riscrittura di una lista.
//
//   Uso:
//     node scripts/check-datatable-baseline.mjs             # confronto
//     node scripts/check-datatable-baseline.mjs --baseline  # riscrive il registro
// ------------------------------------------------------------

import { readFileSync, writeFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, relative, sep } from 'node:path'
import process from 'node:process'

const QUI = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(QUI, '../src')
const REGISTRO = resolve(QUI, 'datatable.baseline.json')
// ⚠️ Apici singoli O DOPPI: prettier normalizza ai singoli, ma un file arrivato
//    da fuori (o scritto prima del format) userebbe i doppi e questo registro
//    smetterebbe di vederlo — cieco in silenzio, che e' il solo modo in cui un
//    cricchetto si allenta senza che nessuno lo decida.
const IMPORT_GREZZO = /from\s+['"]primevue\/datatable['"]/
// Una direttiva di lint (`// eslint-disable…`, `/* oxlint-disable… */`): marca
// l'eccezione per lo strumento, non la motiva per chi legge.
const DIRETTIVA_LINT = /^\s*(\/\/|\/\*)\s*(eslint|oxlint)-(disable|enable)/
const riscrive = process.argv.includes('--baseline')

// Scopo: tutti i `.vue` sotto src/, in ordine stabile (il registro e' un file
//        committato: un ordine ballerino lo renderebbe un diff illeggibile).
function fileVue(dir) {
  const out = []
  for (const nome of readdirSync(dir).sort()) {
    const p = resolve(dir, nome)
    if (statSync(p).isDirectory()) out.push(...fileVue(p))
    else if (nome.endsWith('.vue')) out.push(p)
  }
  return out
}

// ⭐ I COMPONENTI CHE SONO LO STANDARD NON SONO IL DEBITO (2026-09-10).
//    `ListaConfigurabile` la `DataTable` DEVE importarla: e' il building block
//    che incarna la regola. L'altra e' l'eccezione che la regola zero NOMINA
//    di suo pugno (il dettaglio espanso della ricerca → SearchDetailTable).
//    ⭐ `RigheMasterDetailTable` e' uscita da qui il 2026-09-28: dal lotto B di
//    brief-db-liste-righe-documento monta `<DrawerTabLista>`, e le righe di un
//    documento non sono piu' un'eccezione alla regola zero.
// ⛔ Contarle come debito faceva dire al registro una cosa diversa da quella che
//    sembrava: 48 «liste fuori standard» di cui tre erano lo standard. Un
//    registro si legge per il numero, e un numero che comprende la soluzione
//    insieme al problema non si puo' usare per decidere niente.
// ⚠️ L'elenco e' DICHIARATO e non derivato — un criterio automatico («sta in
//    core/components») esenterebbe anche i BB che il debito ce l'hanno davvero
//    (`GeoSearchTable`, che serviva liste ancora da portare su
//    `<ListaConfigurabile>`, e' rimasto contato finche' e' esistito: ritirato
//    il 2026-09-27, brief-db-liste-datatable-grezze riga 9). In cambio l'esenzione e'
//    VERIFICATA sotto: un file dichiarato qui che non esiste piu', o che ha
//    smesso di importare `DataTable`, ferma il guard invece di restare a
//    coprire il vuoto.
const STANDARD = new Set(Object.keys(leggiStandard()))

// Scopo: la sezione `standard` del registro ({file: motivo}), o vuota se il
//        registro non c'e' ancora (prima esecuzione con `--baseline`).
function leggiStandard() {
  if (!existsSync(REGISTRO)) return {}
  return JSON.parse(readFileSync(REGISTRO, 'utf8')).standard ?? {}
}

const grezze = []
const senzaMotivazione = []
const standardTrovati = new Set()
for (const p of fileVue(SRC)) {
  const s = readFileSync(p, 'utf8')
  const i = s.search(IMPORT_GREZZO)
  if (i === -1) continue
  const rel = relative(SRC, p).split(sep).join('/')
  if (STANDARD.has(rel)) { standardTrovati.add(rel); continue }
  grezze.push(rel)
  // ⚠️ «Motivata» = la riga IMMEDIATAMENTE sopra l'import (saltate le
  //    direttive di lint) e' un commento: il motivo sta attaccato a cio' che
  //    motiva. Non si prova a capire cosa dica: un criterio che giudica il
  //    contenuto di una frase boccia a caso, e dopo due blocchi sbagliati
  //    qualcuno lo spegne (stessa ragione per cui il progetto NON ha un cancello
  //    automatico sui messaggi d'errore: `.codex/AGENTS.md`).
  // ⛔ Una DIRETTIVA di lint non e' una motivazione, e si salta (2026-10-03):
  //    dal giorno in cui `no-restricted-imports` ferma l'import, ogni eccezione
  //    ha un `// eslint-disable-next-line` subito sopra. Contato come commento,
  //    avrebbe reso «motivati» in un colpo gli 11 file che non lo sono — un
  //    cricchetto che si allenta senza che nessuno lo decida. Si guarda sopra
  //    le direttive, cosi' il motivo scritto prima resta dentro.
  // ⛔ ADIACENTE, non «in una finestra» (2026-10-31). Fino a quel giorno
  //    bastava un commento in una delle QUATTRO righe sopra, fermandosi alla
  //    prima riga vuota: ma l'intestazione del file (`// Scopo: …`) arriva
  //    spesso agli import SENZA riga vuota, e allora due o tre import piu' su
  //    la finestra la trovava e la dava per motivo. Dieci file risultavano
  //    «motivati» dalla sola intestazione — un registro che cala senza che
  //    nessuno abbia scritto niente (la stessa forma del caso `NoteDrawer` del
  //    2026-10-03, che la riga vuota aveva chiuso solo a meta').
  const righe = s.split('\n')
  let rigaImport = s.slice(0, i).split('\n').length - 1
  while (rigaImport > 0 && DIRETTIVA_LINT.test(righe[rigaImport - 1])) rigaImport--
  const sopra = rigaImport > 0 ? righe[rigaImport - 1] : ''
  if (!/^\s*(\/\/|\/\*|\*)/.test(sopra)) {
    senzaMotivazione.push(rel)
  }
}

const adesso = { grezze, senza_motivazione: senzaMotivazione }

// ⛔ L'ESENZIONE SI VERIFICA, o smette di essere un'esenzione e diventa un buco.
//    Un file dichiarato standard che e' stato rinominato — o che ha smesso di
//    importare `DataTable` — lascerebbe qui una riga che non copre piu' niente,
//    e la prossima lista che prendesse quel nome sarebbe esente per caso.
const standardSpariti = [...STANDARD].filter((f) => !standardTrovati.has(f))
if (standardSpariti.length) {
  console.error(
    `[ko] ${standardSpariti.length} voci di \`standard\` non corrispondono piu' a un file\n` +
    '     che importa `DataTable`:\n' +
    standardSpariti.map((f) => `       · ${f}`).join('\n') +
    '\n\n     O il file e stato rinominato, o non e piu una DataTable grezza: in\n' +
    '     entrambi i casi la voce va tolta o corretta, altrimenti esenta il vuoto.',
  )
  process.exit(2)
}

if (riscrive) {
  writeFileSync(
    REGISTRO,
    JSON.stringify(
      {
        _scopo:
          'Registro di debito delle `DataTable` grezze. PUO SOLO CALARE: il guard ' +
          'e rosso sia se cresce (hai aggiunto una lista fuori standard) sia se cala ' +
          'senza che questo file sia stato riscritto (una baseline stantia riapre lo ' +
          'spazio appena chiuso). Si riscrive con `--baseline`, e la ragione va nel ' +
          'messaggio di commit.',
        _regola: '.codex/AGENTS.md §«Regola zero della lista»',
        // ⚠️ Si RIPORTA, non si ricalcola: la sezione `standard` e' una
        //    decisione scritta a mano (quali componenti SONO lo standard), e
        //    `--baseline` non deve poterla svuotare per distrazione.
        standard: leggiStandard(),
        ...adesso,
      },
      null,
      2,
    ) + '\n',
  )
  console.log(
    `[ok] registro riscritto: ${grezze.length} DataTable grezze, ` +
    `${senzaMotivazione.length} senza motivazione`,
  )
  process.exit(0)
}

if (!existsSync(REGISTRO)) {
  console.error(`[ko] registro assente (${REGISTRO}): crealo con --baseline`)
  process.exit(1)
}
const atteso = JSON.parse(readFileSync(REGISTRO, 'utf8'))

let rosso = false
for (const [chiave, etichetta] of [
  ['grezze', 'DataTable grezze'],
  ['senza_motivazione', 'senza il commento di motivazione'],
]) {
  const prima = new Set(atteso[chiave] ?? [])
  const ora = adesso[chiave]
  const nuovi = ora.filter((f) => !prima.has(f))
  const spariti = [...prima].filter((f) => !ora.includes(f))

  console.log(`${etichetta}: ${ora.length} (registro: ${prima.size})`)

  if (nuovi.length) {
    rosso = true
    console.error(
      `\n[ko] ${etichetta}: ${nuovi.length} in piu' rispetto al registro:\n` +
      nuovi.map((f) => `       + ${f}`).join('\n') +
      (chiave === 'grezze'
        ? '\n\n     Una lista si monta con `<ListaConfigurabile codice="...">`, e la\n' +
          '     configurazione e DATO (una riga in `ui.lista_definizione` piu N in\n' +
          '     `ui.lista_colonna`): si crea in-app o con `scripts/gen_seed_lista.py`,\n' +
          '     senza aspettare nessuno. Le uniche eccezioni sono le righe di un\n' +
          '     documento dentro il suo master e una tabella di anteprima in un dialog.\n' +
          '     ⛔ Non sono eccezioni: «e piccola», «e solo per l admin», «faccio prima».'
        : '\n\n     La regola chiede il MOTIVO scritto in un commento sopra l import.\n' +
          '     Se l eccezione e legittima, scrivi perche; se non lo e, la lista va\n' +
          '     su `<ListaConfigurabile>`.'),
    )
  }
  if (spariti.length) {
    rosso = true
    console.error(
      `\n[ko] ${etichetta}: ${spariti.length} in MENO — e una buona notizia, ma il\n` +
      '     registro va abbassato, altrimenti resta lo spazio per rimetterle:\n' +
      spariti.map((f) => `       - ${f}`).join('\n') +
      '\n\n     ⇒ node scripts/check-datatable-baseline.mjs --baseline\n' +
      '       (e la ragione nel messaggio di commit)',
    )
  }
}

if (rosso) process.exit(1)
console.log('[ok] registro `DataTable` invariato: nessuna lista fuori standard in piu')
