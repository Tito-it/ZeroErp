// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: Guard del chrome delle dialog modali (decisione di Tid, 2026-09-18):
//        il chrome vive in UN posto (`DIALOG_CHROME` + `AppDialog` +
//        `useConfirmAction`), e questo file impedisce che si ri-sparpagli.
//
//   Nasce da un difetto reale visto in-app: «alcune dialog hanno la X a
//   sinistra, altre a destra». Non erano due chrome: era un `Dialog` PrimeVue
//   SENZA TITOLO, la cui riga di testa (`justify-content: space-between`) mette
//   l'unico figlio — la X — a sinistra. Trenta `confirmAction({...})` su 66
//   non passavano il titolo, e sette lo passavano con la chiave SBAGLIATA
//   (`header:` mentre il composable leggeva `title`): ignorata in silenzio,
//   nessun errore, nessun lint. Uno l'aveva persino scoperto e annotato sul
//   sito invece di correggere la sorgente.
//
//   ⛔ E' la famiglia dei difetti che questo repo paga piu' cari: non rompe il
//   build, e si scopre solo perche' qualcuno guarda.
//
//   Sei regole, tutte statiche:
//     1. `primevue/dialog`        si importa SOLO in core/components/AppDialog.vue
//     2. `primevue/confirmdialog` si importa SOLO in App.vue
//     3. `primevue/useconfirm`    si importa SOLO in core/composables/useConfirmAction.js
//     4. ogni `<AppDialog` ha `header` e NON ha `closable` (la X e' andata per
//        decisione: rimetterla su un tag non e' un override, e' una seconda regola)
//     5. ogni `confirmAction({...})` ha `header:` e non ha `title:`
//     6. ogni `<AppDialog>` che contiene CAMPI passa `conferma-uscita`
//        (2026-10-03, D-14 di work-done/analisi-fe-chrome-drawer.md,
//        Tid: «nessuna eccezione»). Fino a quel giorno 44 dialog con campi si
//        chiudevano in silenzio — X, ESC, Annulla — buttando cio' che si era
//        scritto. ⚠️ Si guardano i campi scritti DENTRO il tag: un dialog che
//        delega il form a un componente figlio non si vede da qui.
//        ⭐ Un dialog i cui campi NON sono dati — una casella di ricerca, i
//        parametri di uno strumento di prova — lo DICHIARA subito sopra il tag:
//        `<!-- conferma-uscita: nessuna — <motivo> -->`. Il motivo e'
//        obbligatorio: uscire senza chiedere e' giusto solo se non si perde
//        niente, e chi legge deve poterlo verificare.
//
//   Uso:
//     node scripts/check-dialog-chrome.mjs
//   Exit 1 al primo file fuori regola (li elenca tutti).
// ------------------------------------------------------------

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))

// Le sedi uniche, come percorsi relativi a src/.
const SEDE_DIALOG = 'core/components/AppDialog.vue'
const SEDE_CONFIRMDIALOG = 'App.vue'
const SEDE_USECONFIRM = 'core/composables/useConfirmAction.js'

// Scopo: sorgente senza commenti, per non contare un esempio scritto in un
//        commento come un uso. ⚠️ I ritorni a capo restano, cosi' le righe
//        segnalate sono quelle del file vero.
function senzaCommenti(testo) {
  const soloRighe = (m) => m.replace(/[^\n]/g, '')
  return testo
    .replace(/<!--[\s\S]*?-->/g, soloRighe)
    .replace(/\/\*[\s\S]*?\*\//g, soloRighe)
    // ⚠️ `[ \t]*` e non `\s*` (2026-10-03): con il flag `m`, `\s*` consuma
    //    anche le righe VUOTE prima del commento, e il testo perdeva righe — i
    //    numeri di riga dei messaggi sbagliavano, e i marcatori letti dal testo
    //    grezzo per riga non si trovavano.
    .replace(/^[ \t]*\/\/.*$/gm, '')
}

function fileSorgente(dir, acc = []) {
  for (const voce of readdirSync(dir)) {
    const p = join(dir, voce)
    if (statSync(p).isDirectory()) fileSorgente(p, acc)
    else if (/\.(vue|js)$/.test(voce) && !/\.(spec|test)\.js$/.test(voce)) acc.push(p)
  }
  return acc
}

// Scopo: gli attributi di ogni tag `<AppDialog ...>`, con le virgolette
//        rispettate — un `>` dentro `v => emit(...)` non chiude il tag.
function* tagAppDialog(testo) {
  const re = /<AppDialog\b/g
  let m
  while ((m = re.exec(testo))) {
    let i = m.index + m[0].length
    let q = null
    while (i < testo.length) {
      const c = testo[i]
      if (q) { if (c === q) q = null }
      else if (c === '"' || c === "'") q = c
      else if (c === '>') break
      i++
    }
    const fine = testo.indexOf('</AppDialog>', i)
    yield {
      riga: testo.slice(0, m.index).split('\n').length,
      attrs: testo.slice(m.index, i),
      corpo: testo.slice(i, fine === -1 ? i : fine),
    }
  }
}

// Scopo: il corpo di ogni `confirmAction({ ... })`, a graffe bilanciate.
function* blocchiConfirmAction(testo) {
  const re = /confirmAction\(\s*\{/g
  let m
  while ((m = re.exec(testo))) {
    let i = m.index + m[0].length
    let depth = 1
    while (i < testo.length && depth > 0) {
      if (testo[i] === '{') depth++
      else if (testo[i] === '}') depth--
      i++
    }
    yield { riga: testo.slice(0, m.index).split('\n').length, corpo: testo.slice(m.index + m[0].length, i - 1) }
  }
}

// I campi che rendono un dialog «da non chiudere in silenzio»: i componenti di
// input, i lookup e i select di casa, e il campo file degli allegati.
const CAMPO = /<(InputText|InputNumber|Select|MultiSelect|DatePicker|Textarea|LookupSelect|AutoComplete|Checkbox|ToggleSwitch|RadioButton|SelectButton|[A-Z]\w*Lookup|[A-Z]\w*Select)\b|<input\b[^>]*type="file"/

// Scopo: il dialog alla riga `riga` e' dichiarato «senza dati da perdere»?
//        Il marcatore sta in un commento, quindi si legge dal testo GREZZO (le
//        righe coincidono: `senzaCommenti` lascia i ritorni a capo).
function marcatoSenzaDati(grezzo, riga) {
  return grezzo
    .slice(Math.max(0, riga - 6), riga - 1)
    .some((l) => /conferma-uscita: nessuna\s+—\s+\S/.test(l))
}

const colpevoli = []
let dialog = 0
let conferme = 0

for (const percorso of fileSorgente(SRC)) {
  const rel = relative(SRC, percorso)
  const grezzo = readFileSync(percorso, 'utf8').split('\n')
  const testo = senzaCommenti(grezzo.join('\n'))

  if (/from\s+['"]primevue\/dialog['"]/.test(testo) && rel !== SEDE_DIALOG) {
    colpevoli.push(`${rel}: importa primevue/dialog — si usa <AppDialog> (sede: ${SEDE_DIALOG})`)
  }
  if (/from\s+['"]primevue\/confirmdialog['"]/.test(testo) && rel !== SEDE_CONFIRMDIALOG) {
    colpevoli.push(`${rel}: importa primevue/confirmdialog — la ConfirmDialog e' solo globale (sede: ${SEDE_CONFIRMDIALOG})`)
  }
  if (/from\s+['"]primevue\/useconfirm['"]/.test(testo) && rel !== SEDE_USECONFIRM) {
    colpevoli.push(`${rel}: importa primevue/useconfirm — si usa useConfirmAction (sede: ${SEDE_USECONFIRM})`)
  }

  if (rel !== SEDE_DIALOG) {
    for (const { riga, attrs, corpo } of tagAppDialog(testo)) {
      dialog++
      if (!/(^|\s):?header(=|\s|$)/.test(attrs)) {
        colpevoli.push(`${rel}:${riga}: <AppDialog> senza \`header\` — senza titolo la testa resta vuota e la riga si rompe`)
      }
      if (/(^|\s):?closable(=|\s|$)/.test(attrs)) {
        colpevoli.push(`${rel}:${riga}: <AppDialog> con \`closable\` — la X e' andata per decisione (DIALOG_CHROME), non si rimette sul tag`)
      }
      if (CAMPO.test(corpo) && !/(^|\s):?conferma-uscita=/.test(attrs) && !marcatoSenzaDati(grezzo, riga)) {
        colpevoli.push(`${rel}:${riga}: <AppDialog> con dei campi senza \`conferma-uscita\` — uscendo si butterebbe cio' che si e' scritto senza chiedere (D-14)`)
      }
    }
  }

  if (rel !== SEDE_USECONFIRM) {
    for (const { riga, corpo } of blocchiConfirmAction(testo)) {
      conferme++
      if (/^\s*title\s*[:,]/m.test(corpo)) {
        colpevoli.push(`${rel}:${riga}: confirmAction con \`title:\` — la chiave e' \`header\` (come AppDialog e PrimeVue); \`title\` e' ignorata in silenzio`)
      } else if (!/^\s*header\s*[:,]/m.test(corpo)) {
        colpevoli.push(`${rel}:${riga}: confirmAction senza \`header\` — il titolo e' il nome dell'azione che apre la conferma`)
      }
    }
  }
}

if (dialog === 0 || conferme === 0) {
  console.error(`[ko] rilevamento rotto: ${dialog} <AppDialog> e ${conferme} confirmAction trovati — il guard non sta leggendo niente`)
  process.exit(1)
}

if (colpevoli.length > 0) {
  console.error('[ko] chrome delle dialog fuori sede — regole in frontend-standards.md §AppDialog «Chrome» e §Conferma azioni')
  for (const c of colpevoli) console.error(`     ${c}`)
  process.exit(1)
}
console.log(`[ok] chrome delle dialog in sede unica (${dialog} <AppDialog>, ${conferme} confirmAction, 3 import presidiati)`)
