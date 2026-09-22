// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: IL CANCELLO DEI FILTRI DI LISTA — `<FiltriLista>` e' la sede dei
//        filtri, e le tre cose che, sbagliate, NON danno errore.
//
// 🔴 PERCHE' ESISTE (2026-09-22, lotto L4 del brief
//    `work-in-progress/brief-fe-filtri-lista-su-schermo-compatto.md`). Sotto i
//    1024px i filtri stanno in un drawer dal basso: da quel momento una lista
//    RISTRETTA e una lista VUOTA si assomigliano, e l'unica cosa che le
//    distingue e' il segno dei filtri attivi. Tutte e tre le regole qui sotto
//    proteggono proprio quel segno — e nessuna delle tre, se infranta, rompe
//    il build, accende un lint o fa fallire un test.
//
// ⭐ CINQUE CONTROLLI, e non hanno la stessa natura:
//
//   1. CRICCHETTO — i blocchi `app-page-filters` scritti a mano. Sono il
//      pregresso da convertire (lotto L2): un registro di debito che **puo'
//      solo calare**, stessa forma di `check-datatable-baseline.mjs`.
//   2. CANCELLO A ZERO — ogni `<FiltriLista>` dichiara `:store` o `:segno`.
//      Senza, il componente non ha da dove leggere i filtri: il segno resta
//      **spento su una lista che filtra**, cioe' esattamente la cosa che il
//      building block esiste per impedire. Il componente lo grida in console,
//      ma una console la guarda chi sta sviluppando quel pezzo.
//   3. CANCELLO A ZERO — la RICERCA sta nello slot `#sempre`, non tra i
//      filtri (decisione D2 di Tid). Nel drawer finirebbe dietro due tocchi
//      sul dispositivo in cui digitare costa di piu', e nessuno se ne
//      accorgerebbe da desktop: la' i due slot si rendono uno accanto
//      all'altro, identici.
//   4. CRICCHETTO — le larghezze scritte INLINE nei tag dei filtri
//      (`style="width: 150px"`). Nel drawer vincono su qualunque foglio e
//      tengono i filtri stretti in una riga larga (lotto L3). Il conto e' su
//      **tutti** i blocchi, convertiti o no: L2 non lo cambia, L3 lo fa calare.
//   5. CRICCHETTO — le COPPIE DI DATE scritte a mano (due `<DatePicker>` nello
//      stesso blocco filtri, invece di `<FiltroPeriodo>`). `data_da`/`data_a`
//      non sono due filtri: sono un filtro con due estremi, e nelle diciotto
//      liste che li scrivevano a mano il cablaggio degli eventi era
//      DIVERGENTE — `@date-select` + `@clear-click` in quasi tutte,
//      `@update:modelValue` nei contratti. Col primo una data **digitata** non
//      applica il filtro: l'operatore vede la data che ha scritto e una lista
//      che non l'ha ricevuta. ⛔ Nessun errore, in nessuno dei due casi.
//
// ⚠️ I due cricchetti sono rossi ANCHE QUANDO CALANO: una baseline stantia
//    riapre in silenzio lo spazio appena chiuso. Si riscrive con `--baseline`,
//    e la ragione va nel messaggio di commit.
//
//   Uso:
//     node scripts/check-filtri-lista.mjs             # confronto
//     node scripts/check-filtri-lista.mjs --baseline  # riscrive il registro
// ------------------------------------------------------------

import { readFileSync, writeFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, relative, sep } from 'node:path'
import process from 'node:process'

const QUI = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(QUI, '../src')
const REGISTRO = resolve(QUI, 'filtri-lista.baseline.json')
const riscrive = process.argv.includes('--baseline')

// ⭐ IL COMPONENTE CHE E' LO STANDARD NON E' IL DEBITO: `FiltriLista` la classe
//    `app-page-filters` DEVE renderla — e' lui che incarna la regola. Come nel
//    registro delle `DataTable`, l'elenco e' DICHIARATO (non derivato da
//    «sta in core/components») ed e' VERIFICATO sotto: una voce che non
//    corrisponde piu' a un file col blocco ferma il guard, invece di restare a
//    coprire il vuoto.
const STANDARD = {
  'core/components/FiltriLista.vue':
    'e\' il building block: rende `app-page-filters` nel ramo desktop',
}

// ⚠️ CRITERI DICHIARATI — i conteggi ci dipendono, e un registro il cui valore
//    dipende da un dettaglio non scritto non lo puo' riprodurre nessuno:
//    · il blocco grezzo si apre con `<div ... class="app-page-filters"` sulla
//      STESSA riga (nel repo sono tutti cosi') e si chiude al `</div>` pari;
//    · ⭐ un gruppo AUTO-CHIUSO (`<div class="app-page-filters" />`) e' un
//      gruppo VUOTO — uno spaziatore che spinge le azioni a destra su una lista
//      senza filtri. Sono sette al 2026-09-22 e NON sono debito: non c'e'
//      niente da portare nel drawer. Vengono contati a parte e stampati, non
//      taciuti; e il buco si chiude da se' — il giorno che qualcuno ci mette un
//      filtro dentro, il tag non e' piu' auto-chiuso e il file entra fra i
//      grezzi. ⚠️ Col building block non servono affatto: la spaziatura e' del
//      foglio, non del markup;
//    · la ricerca e' un `v-model` che comincia per `search` (`searchText` in 40
//      siti, piu' `searchTerm`, `searchTable`, `searchRecords`, `searchQuery`);
//    · una larghezza inline e' `style="… width: <n>px …"` dentro un blocco
//      filtri, quale che sia il widget.
const APRE_GREZZO = /<div[^>]*class="[^"]*\bapp-page-filters\b[^"]*"/
const APRE_BB = /<FiltriLista\b/
const RICERCA = /v-model="search[A-Za-z]*"/
const LARGHEZZA_INLINE = /style="[^"]*width:\s*\d+px/g
// ⚠️ Si contano i `<DatePicker>` NUDI nel blocco: quelli dentro
//    `<FiltroPeriodo>` non sono figli del blocco — il BB e' un componente, il
//    suo interno non compare qui. Due o piu' = una coppia scritta a mano.
//    ⭐ Perche' DUE e non uno: un solo DatePicker puo' essere un filtro a se'
//    (il «scadenza mese» dei contratti), e non e' un periodo.
const DATEPICKER_NUDO = /<DatePicker\b/g
const SEMPRE = /<template\s+#sempre\s*>/

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

// Scopo: la fine di un blocco, contando le aperture annidate dello STESSO tag.
// ⛔ Non si cerca la prima chiusura: un blocco filtri contiene `<div>` (e un
//    `<FiltriLista>` non ne contiene altri, ma il conteggio vale per entrambi e
//    non lascia un ramo che dipende da «tanto non capita»). Senza il conteggio
//    il blocco si chiuderebbe troppo presto e il guard diventerebbe cieco
//    proprio sui filtri piu' lunghi — quelli che hanno piu' bisogno di lui.
function fineBlocco(testo, dopoApertura, tagApre, tagChiude) {
  const re = new RegExp(`${tagApre}|${tagChiude}`, 'g')
  re.lastIndex = dopoApertura
  let profondita = 1
  let m
  while ((m = re.exec(testo)) !== null) {
    profondita += m[0].startsWith('</') ? -1 : 1
    if (profondita === 0) return m.index
  }
  return testo.length
}

// Scopo: i blocchi filtri di un file — grezzi (`app-page-filters` scritto a
//        mano) e del building block (`<FiltriLista>`), col loro testo.
function blocchiFiltri(sorgente) {
  const blocchi = []
  for (const [tipo, apre, tagApre, tagChiude] of [
    ['grezzo', APRE_GREZZO, '<div\\b', '</div>'],
    ['bb', APRE_BB, '<FiltriLista\\b', '</FiltriLista>'],
  ]) {
    const re = new RegExp(apre.source, 'g')
    let m
    while ((m = re.exec(sorgente)) !== null) {
      const apertura = sorgente.indexOf('>', m.index)
      if (apertura === -1) continue
      // Tag auto-chiuso = gruppo VUOTO (vedi i criteri in testa): si conta e
      // si stampa, non e' debito e non ha un corpo da guardare.
      if (sorgente[apertura - 1] === '/') { blocchi.push({ tipo: 'vuoto' }); continue }
      const fine = fineBlocco(sorgente, apertura + 1, tagApre, tagChiude)
      blocchi.push({
        tipo,
        tagApertura: sorgente.slice(m.index, apertura + 1),
        corpo: sorgente.slice(apertura + 1, fine),
      })
      re.lastIndex = fine
    }
  }
  return blocchi
}

// Scopo: il corpo di un blocco `<FiltriLista>` SENZA lo slot `#sempre`, per
//        poter dire se la ricerca e' finita tra i filtri.
// ⚠️ Si toglie dal primo `<template #sempre>` al suo `</template>` pari: gli
//    slot annidati (un `<template #option>` di un lookup dentro `#sempre`)
//    sono la ragione del conteggio anche qui.
function senzaSlotSempre(corpo) {
  const m = SEMPRE.exec(corpo)
  if (!m) return corpo
  const dopo = m.index + m[0].length
  const fine = fineBlocco(corpo, dopo, '<template\\b', '</template>')
  return corpo.slice(0, m.index) + corpo.slice(fine)
}

const grezzi = []
const senzaSorgente = []
const ricercaNeiFiltri = []
const larghezzeInline = {}
const coppieDateAMano = []
const standardTrovati = new Set()
// Informativo, non un cricchetto: un gruppo vuoto in piu' non e' un difetto da
// bloccare, ma nasconderlo farebbe sembrare il registro piu' piccolo del vero.
let gruppiVuoti = 0

for (const p of fileVue(SRC)) {
  const s = readFileSync(p, 'utf8')
  const rel = relative(SRC, p).split(sep).join('/')
  const blocchi = blocchiFiltri(s)
  if (!blocchi.length) continue

  let larghezze = 0
  for (const b of blocchi) {
    if (b.tipo === 'vuoto') { gruppiVuoti += 1; continue }
    larghezze += (b.corpo.match(LARGHEZZA_INLINE) ?? []).length
    if ((b.corpo.match(DATEPICKER_NUDO) ?? []).length >= 2 && !coppieDateAMano.includes(rel)) {
      coppieDateAMano.push(rel)
    }
    if (b.tipo === 'grezzo') {
      if (rel in STANDARD) standardTrovati.add(rel)
      else if (!grezzi.includes(rel)) grezzi.push(rel)
      continue
    }
    // Regole 2 e 3, solo sui blocchi del building block.
    if (!/[:\s](store|segno)=/.test(b.tagApertura) && !senzaSorgente.includes(rel)) {
      senzaSorgente.push(rel)
    }
    if (RICERCA.test(senzaSlotSempre(b.corpo)) && !ricercaNeiFiltri.includes(rel)) {
      ricercaNeiFiltri.push(rel)
    }
  }
  if (larghezze > 0) larghezzeInline[rel] = larghezze
}

// ⛔ L'ESENZIONE SI VERIFICA, o smette di essere un'esenzione e diventa un buco:
//    un file dichiarato standard che e' stato rinominato lascerebbe una riga che
//    non copre piu' niente, e il prossimo file con quel nome sarebbe esente per
//    caso.
const standardSpariti = Object.keys(STANDARD).filter((f) => !standardTrovati.has(f))
if (standardSpariti.length) {
  console.error(
    `[ko] ${standardSpariti.length} voci di STANDARD non corrispondono piu' a un file\n`
    + '     che rende `app-page-filters`:\n'
    + standardSpariti.map((f) => `       · ${f}`).join('\n')
    + '\n\n     O il file e stato rinominato, o ha smesso di renderlo: in entrambi i\n'
    + '     casi la voce va corretta, altrimenti esenta il vuoto.',
  )
  process.exit(2)
}

const totaleLarghezze = Object.values(larghezzeInline).reduce((a, b) => a + b, 0)

if (riscrive) {
  writeFileSync(
    REGISTRO,
    `${JSON.stringify(
      {
        _scopo:
          'Registro di debito dei filtri di lista. PUO SOLO CALARE: il guard e rosso '
          + 'sia se cresce (una lista nuova coi filtri scritti a mano, o una larghezza '
          + 'inline in piu) sia se cala senza che questo file sia stato riscritto (una '
          + 'baseline stantia riapre lo spazio appena chiuso). Si riscrive con '
          + '--baseline, e la ragione va nel messaggio di commit.',
        _regola:
          'docs/it/dev/frontend/frontend-standards.md §«Filtri della lista — FiltriLista»',
        _brief:
          'docs/it/dev/work-in-progress/brief-fe-filtri-lista-su-schermo-compatto.md',
        _lotti: {
          grezzi: 'L2 — adozione di <FiltriLista> (76 blocchi in 70 file al 2026-09-22)',
          larghezze_inline: 'L3 — le larghezze da numero nel tag a classe app-filter-w-*',
          coppie_date_a_mano: 'L2 — la coppia data_da/data_a passa da <FiltroPeriodo>',
        },
        grezzi,
        larghezze_inline: larghezzeInline,
        coppie_date_a_mano: coppieDateAMano,
      },
      null,
      2,
    )}\n`,
  )
  console.log(
    `[ok] registro riscritto: ${grezzi.length} file coi filtri a mano, `
    + `${totaleLarghezze} larghezze inline in ${Object.keys(larghezzeInline).length} file, `
    + `${coppieDateAMano.length} coppie di date a mano`
    + ` (piu' ${gruppiVuoti} gruppi vuoti, non debito)`,
  )
  process.exit(0)
}

if (!existsSync(REGISTRO)) {
  console.error(`[ko] registro assente (${REGISTRO}): crealo con --baseline`)
  process.exit(1)
}
const atteso = JSON.parse(readFileSync(REGISTRO, 'utf8'))
let rosso = false

// --- 1. Cricchetto dei blocchi grezzi --------------------------------------
{
  const prima = new Set(atteso.grezzi ?? [])
  const nuovi = grezzi.filter((f) => !prima.has(f))
  const spariti = [...prima].filter((f) => !grezzi.includes(f))
  console.log(`filtri scritti a mano: ${grezzi.length} file (registro: ${prima.size})`)
  console.log(`gruppi filtri vuoti (spaziatori, non debito): ${gruppiVuoti}`)
  if (nuovi.length) {
    rosso = true
    console.error(
      `\n[ko] ${nuovi.length} file in piu' scrivono i filtri a mano:\n`
      + nuovi.map((f) => `       + ${f}`).join('\n')
      + '\n\n     I filtri di una lista si montano con `<FiltriLista :store="store">`:\n'
      + '     la ricerca nello slot `#sempre`, gli altri filtri nello slot di\n'
      + '     default. Sotto i 1024px il building block li porta nel drawer dal\n'
      + '     basso e accende il segno dei filtri attivi — scritti a mano, quel\n'
      + '     segno non esiste e la lista non dice che sta filtrando.',
    )
  }
  if (spariti.length) {
    rosso = true
    console.error(
      `\n[ko] ${spariti.length} file in MENO — e' una buona notizia, ma il registro va\n`
      + '     abbassato, altrimenti resta lo spazio per rimetterli:\n'
      + spariti.map((f) => `       - ${f}`).join('\n')
      + '\n\n     ⇒ node scripts/check-filtri-lista.mjs --baseline',
    )
  }
}

// --- 1-bis. Cricchetto delle coppie di date scritte a mano -----------------
{
  const prima = new Set(atteso.coppie_date_a_mano ?? [])
  const nuovi = coppieDateAMano.filter((f) => !prima.has(f))
  const spariti = [...prima].filter((f) => !coppieDateAMano.includes(f))
  console.log(`coppie di date scritte a mano: ${coppieDateAMano.length} file (registro: ${prima.size})`)
  if (nuovi.length) {
    rosso = true
    console.error(
      `\n[ko] ${nuovi.length} file in piu' scrivono la coppia di date a mano:\n`
      + nuovi.map((f) => `       + ${f}`).join('\n')
      + '\n\n     `data_da`/`data_a` non sono due filtri: sono UN filtro con due\n'
      + '     estremi. Si montano con `bindPeriodo()` + `<FiltroPeriodo :periodo>`,\n'
      + '     che tiene in un posto solo anche il verso degli eventi — scritti a\n'
      + '     mano, una data DIGITATA nella casella non applica il filtro.',
    )
  }
  if (spariti.length) {
    rosso = true
    console.error(
      `\n[ko] ${spariti.length} file in MENO — buona notizia, registro da abbassare:\n`
      + spariti.map((f) => `       - ${f}`).join('\n')
      + '\n\n     ⇒ node scripts/check-filtri-lista.mjs --baseline',
    )
  }
}

// --- 2. Cancello: ogni <FiltriLista> ha una sorgente per il segno -----------
if (senzaSorgente.length) {
  rosso = true
  console.error(
    `\n[ko] ${senzaSorgente.length} <FiltriLista> senza \`:store\` ne' \`:segno\`:\n`
    + senzaSorgente.map((f) => `       · ${f}`).join('\n')
    + '\n\n     Senza una sorgente il componente non ha da dove leggere i filtri: il\n'
    + '     segno resta SPENTO su una lista che filtra, e non fallisce niente.\n'
    + '     Chi ha uno store-lista passa `:store="store"`; le superfici senza\n'
    + '     (cruscotti, giornale) passano `:segno` gia\' calcolato con\n'
    + '     `segnoFiltri(...)`.',
  )
}

// --- 3. Cancello: la ricerca sta nello slot `#sempre` ----------------------
if (ricercaNeiFiltri.length) {
  rosso = true
  console.error(
    `\n[ko] ${ricercaNeiFiltri.length} file hanno la RICERCA tra i filtri invece che`
    + ' nello slot `#sempre`:\n'
    + ricercaNeiFiltri.map((f) => `       · ${f}`).join('\n')
    + '\n\n     La ricerca non e\' un filtro: e\' il gesto principale della lista, e\n'
    + '     resta sempre a video (decisione D2). Nello slot di default finisce\n'
    + '     dentro il drawer, cioe\' dietro due tocchi proprio sul dispositivo in\n'
    + '     cui digitare costa di piu\'. ⚠️ Da desktop non si vede: i due slot si\n'
    + '     rendono uno accanto all\'altro.\n'
    + '     ⇒ <template #sempre><InputText v-model="searchText" … /></template>',
  )
}

// --- 4. Cricchetto delle larghezze inline ---------------------------------
{
  const prima = atteso.larghezze_inline ?? {}
  const primaTot = Object.values(prima).reduce((a, b) => a + b, 0)
  console.log(
    `larghezze inline nei filtri: ${totaleLarghezze} (registro: ${primaTot})`,
  )
  const cresciuti = Object.entries(larghezzeInline)
    .filter(([f, n]) => n > (prima[f] ?? 0))
    .map(([f, n]) => `       + ${f}: ${prima[f] ?? 0} → ${n}`)
  const calati = Object.entries(prima)
    .filter(([f, n]) => (larghezzeInline[f] ?? 0) < n)
    .map(([f, n]) => `       - ${f}: ${n} → ${larghezzeInline[f] ?? 0}`)
  if (cresciuti.length) {
    rosso = true
    console.error(
      `\n[ko] larghezze inline in piu' rispetto al registro:\n${cresciuti.join('\n')}`
      + '\n\n     Una larghezza scritta nel tag vince su qualunque foglio di stile:\n'
      + '     nel drawer dal basso il filtro resta stretto in una riga larga, e non\n'
      + '     da\' nessun errore. La larghezza va in una classe (`app-filter-w-*`).',
    )
  }
  if (calati.length) {
    rosso = true
    console.error(
      `\n[ko] larghezze inline in MENO — buona notizia, registro da abbassare:\n${calati.join('\n')}`
      + '\n\n     ⇒ node scripts/check-filtri-lista.mjs --baseline',
    )
  }
}

if (rosso) process.exit(1)
console.log('[ok] filtri di lista: registro invariato, nessun segno spento, ricerca al suo posto')
