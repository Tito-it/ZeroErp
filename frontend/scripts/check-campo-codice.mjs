// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: Guard del campo `codice`: ogni input con `v-model="….codice"` porta la
//        classe `app-codice-input` (il codice si vede in maiuscolo mentre si
//        digita), oppure il suo file sta in ECCEZIONI col motivo.
//
//   Nasce dall'automazione DB CODICE_MAIUSCOLO (2026-11-04, decisione di Tid):
//   il DB salva ogni colonna `codice` in `upper(btrim())`, e la classe fa
//   vedere all'operatore la forma in cui il codice verra' salvato.
//   brief-be-codice-maiuscolo §4.
//
//   ⭐ LA REGOLA E' PER ESCLUSIONE, COME QUELLA DEL DB. Il DB monta il trigger su
//   ogni colonna `codice` dell'ambito e tiene a parte le eccezioni
//   (`dbops.automazione_codice_eccezioni`, motivo obbligatorio): una tabella
//   nuova nasce presidiata. Qui e' lo stesso: un drawer nuovo con un campo
//   codice o mette la classe o dichiara perche' no. Senza il guard la scelta
//   resterebbe alla memoria di chi scrive il drawer.
//
//   ⛔ La classe e' SOLO VISIVA (`text-transform`): il valore del form resta
//   come digitato e la regola vive nel DB. Non si ricopia in JavaScript.
//
//   ⚠️ Un'eccezione che non serve piu' (il file non ha piu' un campo codice, o
//   la classe ce l'ha) e' rossa anche lei: un elenco di eccezioni stantie
//   smette di dire qualcosa.
//
//   Uso:
//     node scripts/check-campo-codice.mjs
//   Exit 1 se un campo codice non ha la classe e il suo file non e' fra le
//   eccezioni, o se un'eccezione e' stantia.
// ------------------------------------------------------------

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))
const CLASSE = 'app-codice-input'

// I file in cui il campo codice scrive su una tabella che il DB lascia com'e'
// (in `dbops.automazione_codice_eccezioni`, o fuori dall'ambito). Il motivo e'
// obbligatorio: e' la ragione per cui il maiuscolo a video mentirebbe.
// L'elenco delle tabelle normalizzate: `dbops.fn_codice_maiuscolo_perimetro(NULL)`
// (`nel_perimetro AND NOT in_eccezione`).
const ECCEZIONI = {
  'ui/components/ListaDefinizioneDrawer.vue':
    'ui.lista_definizione: chiave tecnica letta per nome, in eccezione a DB',
  'ui/components/ListaPresetDrawer.vue':
    'ui.lista_preset: chiave tecnica letta per nome, in eccezione a DB',
  'ui/components/ListaColonnaDrawer.vue':
    'ui.lista_colonna: chiave tecnica letta per nome, in eccezione a DB',
  'core/components/CodiceSecondoFattoreInput.vue':
    'non e\' una colonna `codice`: e\' il codice usa-e-getta del secondo fattore (TOTP), non si salva',
}

// Scopo: sorgente senza commenti, perche' un campo citato in un commento non e'
//        un campo.
function senzaCommenti(testo) {
  return testo
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
}

function fileVue(dir, acc = []) {
  for (const voce of readdirSync(dir)) {
    const p = join(dir, voce)
    if (statSync(p).isDirectory()) fileVue(p, acc)
    else if (voce.endsWith('.vue')) acc.push(p)
  }
  return acc
}

const colpevoli = []
const conCampo = new Set()
let campi = 0

for (const percorso of fileVue(SRC)) {
  const rel = relative(SRC, percorso)
  // ⚠️ Si scorre il solo <template>: un `<` del codice JS (`a<b`, un generico)
  //    aprirebbe un falso tag che, con un apice sbilanciato, ingoia i tag veri.
  const sorgente = senzaCommenti(readFileSync(percorso, 'utf8'))
  const inizio = sorgente.indexOf('<template')
  const fine = sorgente.lastIndexOf('</template>')
  if (inizio < 0 || fine < inizio) continue
  const testo = sorgente.slice(inizio, fine)
  // ⚠️ Gli attributi si scorrono con le virgolette rispettate: un handler
  //    `@x="(v) => …"` contiene un `>` che con `[^>]*` chiuderebbe il tag
  //    (la stessa trappola di check-drawer-width).
  for (const t of testo.matchAll(/<([A-Za-z][\w-]*)\b((?:[^>"']|"[^"]*"|'[^']*')*)>/g)) {
    const attributi = t[2]
    // I modificatori (`v-model.trim`) sono lo stesso campo.
    if (!/\sv-model(?:\.\w+)*="(?:[\w$]+\.)*codice"/.test(attributi)) continue
    campi += 1
    conCampo.add(rel)
    const classe = attributi.match(/\sclass="([^"]*)"/)
    const haClasse = classe !== null && classe[1].split(/\s+/).includes(CLASSE)
    if (rel in ECCEZIONI) {
      if (haClasse) {
        colpevoli.push(`${rel}: e' fra le ECCEZIONI ma il campo ha ${CLASSE} — o l'una o l'altra`)
      }
    } else if (!haClasse) {
      colpevoli.push(`${rel}: <${t[1]} v-model="….codice"> senza class="${CLASSE}"`)
    }
  }
}

if (campi === 0) {
  console.error('[ko] nessun campo `v-model="….codice"` trovato: il rilevamento e\' rotto')
  process.exit(1)
}

for (const rel of Object.keys(ECCEZIONI)) {
  if (!conCampo.has(rel)) {
    colpevoli.push(`${rel}: eccezione stantia — il file non ha piu' un campo codice`)
  }
}

if (colpevoli.length > 0) {
  console.error(
    `[ko] campi codice fuori regola. Il DB salva il codice in maiuscolo: il campo `
    + `porta class="${CLASSE}", oppure il file va in ECCEZIONI col motivo `
    + '(scripts/check-campo-codice.mjs).',
  )
  for (const c of colpevoli) console.error(`     ${c}`)
  process.exit(1)
}

console.log(`[ok] ${campi} campi codice: tutti con ${CLASSE} o in eccezione dichiarata`)
