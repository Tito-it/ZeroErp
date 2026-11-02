// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript (Node, standalone — nessuna dipendenza)
// Scopo: IL CANCELLO DEI FILTRI DI LISTA — `<FiltriLista>` e' la sede dei
//        filtri, e le cose che, sbagliate, NON danno errore.
//
// 🔴 PERCHE' ESISTE (2026-09-22, lotto L4 del brief
//    `work-done/brief-fe-filtri-lista-su-schermo-compatto.md`). Sotto i
//    1024px i filtri stanno in un drawer dal basso: da quel momento una lista
//    RISTRETTA e una lista VUOTA si assomigliano, e l'unica cosa che le
//    distingue e' il segno dei filtri attivi. Tutte le regole qui sotto
//    proteggono proprio quel segno — e nessuna di esse, se infranta, rompe il
//    build, accende un lint o fa fallire un test.
//
// ⭐ SETTE CONTROLLI, e non hanno la stessa natura:
//
//   1. CRICCHETTO — i blocchi `app-page-filters` scritti a mano. Sono il
//      pregresso da convertire (lotto L2): un registro di debito che **puo'
//      solo calare**, stessa forma di `check-datatable-baseline.mjs`.
//   2. CANCELLO A ZERO — ogni `<FiltriLista>` dichiara `:store` o `:segno`.
//      Senza, il componente non ha da dove leggere i filtri: il segno resta
//      **spento su una lista che filtra**, cioe' esattamente la cosa che il
//      building block esiste per impedire. Il componente lo grida in console,
//      ma una console la guarda chi sta sviluppando quel pezzo.
//   2-bis. CANCELLO A ZERO — lo store nominato da `:store` OFFRE davvero il
//      contratto dei filtri. ⛔ Il controllo 2 guarda che l'attributo sia
//      SCRITTO, non che dietro ci sia qualcosa: uno store a mano che non passa
//      da `useContrattoFiltriLista` supera il 2 e lascia il segno spento
//      identico. Il componente lo grida in console — ma solo a chi apre quella
//      lista con la console aperta, cioe' non in CI.
//      ⚠️ Il buco che RESTA e' dichiarato: se il `:store` non si risolve a
//      una sola sorgente leggibile (alias, store passato come prop), il file
//      finisce fra i «non verificabili» e viene STAMPATO. Un cancello che tace
//      su cio' che non sa guardare fa credere di averlo guardato.
//   3. CANCELLO A ZERO — la RICERCA sta nello slot `#sempre`, non tra i
//      filtri (decisione D2 di Tid). Nel drawer finirebbe dietro due tocchi
//      sul dispositivo in cui digitare costa di piu', e nessuno se ne
//      accorgerebbe da desktop: la' i due slot si rendono uno accanto
//      all'altro, identici.
//   3-bis. CANCELLO A ZERO — `app-page-toolbar-start` non contiene FILTRI.
//      ⭐ E' la classe nata il 2026-09-23 per la zona sinistra della toolbar
//      che filtri non porta (un titolo, un pulsante «torna alla lista»). Serve
//      perche' nove blocchi usavano `app-page-filters` per quello — ma proprio
//      per questo diventerebbe la porta di servizio del cancello 1: chi ha
//      fretta rinomina la classe e il registro non se ne accorge. Il controllo
//      guarda il PERCORSO REALE, non il nome.
//   4. CRICCHETTO — le larghezze scritte INLINE nei tag dei filtri
//      (`style="width: 150px"`, ma anche `rem`/`%` e `input-style`: l'unita'
//      non cambia il difetto, e un criterio che ne guarda una sola e' cieco
//      sull'altra — stesso stampo di `feedback_whitelist_dal_percorso_reale`). Nel drawer vincono su qualunque foglio e
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
//    · ⛔ SI GUARDA SOLO LA SEZIONE `<template>` del file, e questa riga e'
//      costata un falso allarme il 2026-09-23: le intestazioni di questi
//      componenti NOMINANO i tag di cui parlano («si monta con
//      `<DrawerTabLista>`»), e un criterio che legge il file intero prende quel
//      testo per markup. Il tag «aperto» diventava `<DrawerTabLista>` senza
//      attributi — quindi «senza `:store`» — e la ricerca della chiusura
//      inghiottiva mezzo file, tirando dentro DatePicker che coi filtri non
//      c'entravano. ⭐ Le regole qui sono regole di MARKUP: leggerle fuori dal
//      template e' leggere la cosa sbagliata;
//    · la ricerca e' un `v-model` che comincia per `search` (`searchText` in 40
//      siti, piu' `searchTerm`, `searchTable`, `searchRecords`, `searchQuery`);
//    · una larghezza inline e' `style="… width: <n>px …"` dentro un blocco
//      filtri, quale che sia il widget.
const APRE_GREZZO = /<div[^>]*class="[^"]*\bapp-page-filters\b[^"]*"/
const APRE_BB = /<FiltriLista\b/
// ⭐ Il tab-lista dentro un drawer passa da `<DrawerTabLista>`, che i filtri li
//    gira a `FiltriLista` per conto del caller: i suoi due slot sono
//    `#filtri-sempre` (la ricerca) e `#filtri` (gli altri). Senza questa riga i
//    controlli 2 e 3 sarebbero ciechi su TREDICI liste — quelle dentro un
//    drawer, cioe' proprio le piu' difficili da guardare a video.
const APRE_TAB = /<DrawerTabLista\b/
const RICERCA = /v-model="search[A-Za-z]*"/
const LARGHEZZA_INLINE = /(?:input-)?style="[^"]*width:\s*[\d.]+(?:px|rem|em|ch|%)/g
// ⚠️ Si contano i `<DatePicker>` NUDI nel blocco: quelli dentro
//    `<FiltroPeriodo>` non sono figli del blocco — il BB e' un componente, il
//    suo interno non compare qui. Due o piu' = una coppia scritta a mano.
//    ⭐ Perche' DUE e non uno: un solo DatePicker puo' essere un filtro a se'
//    (il «scadenza mese» dei contratti), e non e' un periodo.
const DATEPICKER_NUDO = /<DatePicker\b/g
const SEMPRE = /<template\s+#sempre\s*>/
const SEMPRE_TAB = /<template[^>]*\s#filtri-sempre\s*>/
const FILTRI_TAB = /<template[^>]*\s#filtri\s*>/
// I widget che sono FILTRI: se uno di questi compare nella zona sinistra della
// toolbar, quella zona e' un gruppo filtri e il suo posto e' `<FiltriLista>`.
// ⚠️ `Auto[Cc]omplete` con le DUE grafie, ed era un buco: PrimeVue scrive
//    `<AutoComplete>` (C maiuscola), i nostri wrapper `<ComuneAutocomplete>`.
//    Un criterio case-sensitive su una sola delle due vede meta' dei lookup —
//    lo stampo di `feedback_whitelist_dal_percorso_reale`: una whitelist si
//    verifica dal percorso che la attraversa, non dal nome che ci si aspetta.
const WIDGET_FILTRO = /<(Select|LookupSelect|DatePicker|InputNumber|FiltroToggle|FiltroPeriodo|SelectButton|MultiSelect|ToggleSwitch|Checkbox|UtilityPerRuoloSelect|[A-Za-z]*Lookup|[A-Za-z]*Auto[Cc]omplete)\b|<InputText[^>]*v-model/
const APRE_ZONA_SX = /<div[^>]*class="[^"]*\bapp-page-toolbar-start\b[^"]*"/

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

// Scopo: la sola sezione `<template>` di un Single File Component — il posto
//        dove il markup e' markup. Fuori di li' i tag compaiono nei COMMENTI di
//        intestazione, che parlano dei building block invece di usarli.
// ⚠️ Si cerca il `<template>` a colonna zero: e' la convenzione SFC, e dentro
//    la sezione ce ne sono altri (gli slot), tutti indentati.
function sezioneTemplate(sorgente) {
  const inizio = sorgente.search(/^<template>/m)
  if (inizio === -1) return ''
  const fine = sorgente.search(/^<\/template>/m)
  return fine === -1 ? sorgente.slice(inizio) : sorgente.slice(inizio, fine)
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
    ['tab', APRE_TAB, '<DrawerTabLista\\b', '</DrawerTabLista>'],
    ['zona-sx', APRE_ZONA_SX, '<div\\b', '</div>'],
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

// Scopo: il corpo di un blocco SENZA lo slot della ricerca, per poter dire se
//        la ricerca e' finita tra i filtri.
// ⚠️ Si toglie dal primo `<template #sempre>` (o `#filtri-sempre`, nei tab di
//    drawer) al suo `</template>` pari: gli slot annidati (un
//    `<template #option>` di un lookup dentro la ricerca) sono la ragione del
//    conteggio anche qui.
// ⚠️ Si toglie anche il `</template>` di chiusura: `fineBlocco` restituisce il
//    suo INDICE, e lasciarlo dentro fa sembrare «pieno» un blocco che ha la
//    sola ricerca — cioe' fa scattare la regola 2 su liste che un segno non ce
//    l'hanno affatto (falso allarme del 2026-09-23 su tre pannelli).
const CHIUDE_TEMPLATE = '</template>'
function senzaSlotSempre(corpo, apre = SEMPRE) {
  const m = new RegExp(apre.source).exec(corpo)
  if (!m) return corpo
  const dopo = m.index + m[0].length
  const fine = fineBlocco(corpo, dopo, '<template\\b', '</template>')
  // ⚠️ Chiusura NON trovata: `fineBlocco` ripiega sulla lunghezza del testo, e
  //    tagliare a `fine + 11` restituirebbe la stringa VUOTA — cioe' un blocco
  //    che sembra non avere filtri, e due controlli che si spengono in
  //    silenzio. Meglio il blocco intero: al massimo segnala di piu'.
  if (fine >= corpo.length) return corpo
  return corpo.slice(0, m.index) + corpo.slice(fine + CHIUDE_TEMPLATE.length)
}

// Scopo: il CONTENUTO di uno slot nominato (`<template #filtri> ... </template>`),
//        senza il `<template>` che lo apre ne' quello che lo chiude.
// ⛔ SERVE A NON GUARDARE PIU' DI QUEL CHE SI DEVE, ed e' la correzione del
//    2026-09-23. I blocchi `<DrawerTabLista>` venivano letti PER INTERO, quindi
//    le regole dei filtri cadevano su cose che filtri non sono: una
//    `<Column style="width: 120px">` diventava una «larghezza inline nei
//    filtri» (controllo 4) e due `<DatePicker>` dentro `#testata` — che quel
//    componente documenta come «il posto della form di inserimento» —
//    diventavano una «coppia di date scritta a mano» (controllo 5).
//    ⚠️ Un cancello che boccia a caso e' peggio di uno assente: dopo due
//    blocchi sbagliati qualcuno lo spegne, ed e' il criterio gia' scritto per il
//    rubinetto degli accumulatori.
function contenutoSlot(corpo, apre) {
  const m = new RegExp(apre.source).exec(corpo)
  if (!m) return ''
  const dopo = m.index + m[0].length
  const fine = fineBlocco(corpo, dopo, '<template\\b', '</template>')
  return corpo.slice(dopo, Math.min(fine, corpo.length))
}

// Scopo: le due PARTI di un blocco che le regole dei filtri devono guardare —
//        la ricerca (`#sempre` / `#filtri-sempre`) e i filtri veri.
// ⚠️ Le due forme non sono simmetriche, e non per scelta: `<FiltriLista>` mette
//    i filtri nel suo slot di DEFAULT (quindi «tutto cio' che non e' la
//    ricerca»), `<DrawerTabLista>` li vuole in uno slot NOMINATO `#filtri`
//    (quindi solo quello — il resto del tag sono colonne, testata, empty state).
function partiFiltri(corpo, diTab) {
  if (diTab) {
    return {
      ricerca: contenutoSlot(corpo, SEMPRE_TAB),
      filtri: contenutoSlot(corpo, FILTRI_TAB),
    }
  }
  return {
    ricerca: contenutoSlot(corpo, SEMPRE),
    filtri: senzaSlotSempre(corpo, SEMPRE),
  }
}

// Scopo: dire se un blocco ha davvero dei FILTRI, cioe' contenuto nello slot di
//        default — quello che in modalita' compatta finisce nel drawer.
// ⭐ Serve alla regola 2: una lista con la SOLA ricerca non ha segno da
//    mostrare (la ricerca non e' un filtro, D2), quindi `FiltriLista` non rende
//    ne' l'icona ne' il drawer, e pretendere una sorgente per il conteggio
//    sarebbe un cancello che chiede di alimentare una cosa che non esiste.
// ⚠️ Si guarda cio' che resta tolti lo slot della ricerca, i commenti e gli
//    spazi: uno slot di default DICHIARATO con `<template #default>` conta.
function haFiltri(soloFiltri) {
  return soloFiltri.replace(/<!--[\s\S]*?-->/g, '').trim().length > 0
}

// ⭐ I MARCATORI DEL CONTRATTO: uno store offre `chiaviFiltro`/`filtriDefault`/
//    `azzeraFiltri` se passa da una di queste sedi. L'elenco e' DICHIARATO e
//    non dedotto: sono le uniche quattro porte, e aggiungerne una quinta deve
//    costare una riga qui.
const CONTRATTO = /useListaStoreCore|createListaStore|createCrudStore|useContrattoFiltriLista/

// Scopo: da un file `.vue` e dal nome scritto in `:store="..."`, i file degli
//        store che quella variabile puo' contenere.
// ⚠️ Si legge SOLO l'espressione che inizializza quella variabile, comprese le
//    righe di continuazione indentate: cosi' un ternario
//    (`perMagazzino ? useA() : useB()`) da' due sorgenti, e un `useAuthStore`
//    che sta altrove nel file non entra per sbaglio.
function sorgentiStore(fileVue, sorgente, nome) {
  const m = new RegExp(`const ${nome} = ([^\\n]*(?:\\n[ \\t]+[^\\n]*)*)`).exec(sorgente)
  if (!m) return null
  const usi = [...m[1].matchAll(/\b(use\w*Store)\s*\(/g)].map((u) => u[1])
  if (!usi.length) return null
  const file = []
  for (const uso of usi) {
    const imp = new RegExp(`import \\{[^}]*\\b${uso}\\b[^}]*\\} from '([^']+)'`).exec(sorgente)
    if (!imp) return null
    const risolto = resolve(dirname(fileVue), `${imp[1]}.js`)
    if (!existsSync(risolto)) return null
    file.push(risolto)
  }
  return file
}

const grezzi = []
const senzaSorgente = []
const storeSenzaContratto = []
const storeNonVerificabili = []
const ricercaNeiFiltri = []
const filtriInZonaSinistra = []
const larghezzeInline = {}
const coppieDateAMano = []
const standardTrovati = new Set()
// Informativo, non un cricchetto: un gruppo vuoto in piu' non e' un difetto da
// bloccare, ma nasconderlo farebbe sembrare il registro piu' piccolo del vero.
let gruppiVuoti = 0

for (const p of fileVue(SRC)) {
  const s = readFileSync(p, 'utf8')
  const rel = relative(SRC, p).split(sep).join('/')
  const blocchi = blocchiFiltri(sezioneTemplate(s))
  if (!blocchi.length) continue

  let larghezze = 0
  for (const b of blocchi) {
    if (b.tipo === 'vuoto') { gruppiVuoti += 1; continue }

    // Regola 3-bis: la zona sinistra della toolbar non e' un gruppo filtri.
    // ⛔ Si guarda il CONTENUTO, non il nome: e' l'unica cosa che impedisce a
    //    quella classe di diventare la porta di servizio del cricchetto 1.
    if (b.tipo === 'zona-sx') {
      if (WIDGET_FILTRO.test(b.corpo) && !filtriInZonaSinistra.includes(rel)) {
        filtriInZonaSinistra.push(rel)
      }
      continue
    }

    // Un tab-lista di drawer gira i propri slot a `FiltriLista`: le regole
    // valgono identiche, coi nomi che quel contenitore dichiara.
    const diTab = b.tipo === 'tab'
    const { ricerca, filtri } = partiFiltri(b.corpo, diTab)
    // ⛔ Le regole 4 e 5 guardano SOLO le due parti dei filtri, non il blocco
    //    intero: fuori di li' una larghezza o una data non sono un filtro.
    //    Su un blocco grezzo le due parti coincidono col blocco.
    const zonaFiltri = `${ricerca}\n${filtri}`
    larghezze += (zonaFiltri.match(LARGHEZZA_INLINE) ?? []).length
    if ((zonaFiltri.match(DATEPICKER_NUDO) ?? []).length >= 2 && !coppieDateAMano.includes(rel)) {
      coppieDateAMano.push(rel)
    }
    if (b.tipo === 'grezzo') {
      if (rel in STANDARD) standardTrovati.add(rel)
      else if (!grezzi.includes(rel)) grezzi.push(rel)
      continue
    }

    // Regola 2 — solo dove c'e' davvero un segno da accendere.
    if (haFiltri(filtri)
      && !/[:\s](store|segno)=/.test(b.tagApertura)
      && !senzaSorgente.includes(rel)) {
      senzaSorgente.push(rel)
    }
    // Regola 2-bis — e dietro quel `:store` c'e' davvero il contratto?
    const rifStore = /[:\s]store="([A-Za-z_$][\w$]*)"/.exec(b.tagApertura)
    if (haFiltri(filtri) && rifStore) {
      const sorgenti = sorgentiStore(p, s, rifStore[1])
      if (!sorgenti) {
        if (!storeNonVerificabili.includes(rel)) storeNonVerificabili.push(rel)
      } else if (sorgenti.some((f) => !CONTRATTO.test(readFileSync(f, 'utf8')))
        && !storeSenzaContratto.includes(rel)) {
        storeSenzaContratto.push(rel)
      }
    }
    // Regola 3 — la ricerca sta nello slot che resta sempre a video.
    if (RICERCA.test(filtri) && !ricercaNeiFiltri.includes(rel)) {
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
          'docs/it/dev/work-done/brief-fe-filtri-lista-su-schermo-compatto.md',
        _lotti: {
          grezzi:
            'L2 CHIUSO il 2026-09-23: zero. Erano 76 blocchi in 70 file il 22-09, di cui '
            + 'nove non erano filtri affatto (un titolo, un pulsante, spaziatori vuoti) e '
            + 'sono passati a `app-page-toolbar-start`, presidiata dal controllo 3-bis. '
            + 'Da qui in avanti il registro dice una cosa sola: una lista NUOVA coi filtri '
            + 'scritti a mano lo fa risalire.',
          larghezze_inline:
            'L3 CHIUSO il 2026-09-23: zero. Erano 114 in 42 file; il criterio ora guarda '
            + 'anche rem/%/input-style, perche\' l\'unita\' non cambia il difetto.',
          coppie_date_a_mano:
            'L2 CHIUSO il 2026-09-23: zero. Erano 17 file. ⭐ Con l\'ultima coppia sparisce '
            + 'anche l\'ultimo buco dell\'invariante D8 («da > a non puo\' esistere»), che '
            + 'vive in `bindPeriodo`.',
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

// --- 2-bis. Cancello: dietro `:store` c'e' il contratto dei filtri ---------
if (storeSenzaContratto.length) {
  rosso = true
  console.error(
    `\n[ko] ${storeSenzaContratto.length} file passano uno \`:store\` che NON offre il`
    + ' contratto dei filtri:\n'
    + storeSenzaContratto.map((f) => `       \u00b7 ${f}`).join('\n')
    + '\n\n     `chiaviFiltro`, `filtriDefault` e `azzeraFiltri` arrivano da\n'
    + '     `useListaStoreCore` (o `createListaStore` / `createCrudStore`). Uno\n'
    + '     store scritto a mano li adotta in tre righe con\n'
    + '     `useContrattoFiltriLista({ filters, filterDefaults, fetchList })`.\n'
    + '     \u26a0\ufe0f Senza, il segno resta SPENTO su una lista che filtra: l\'attributo\n'
    + '     c\'e\' e non porta niente.',
  )
}
if (storeNonVerificabili.length) {
  console.log(
    `store non verificabili staticamente (buco DICHIARATO): ${storeNonVerificabili.length}\n`
    + storeNonVerificabili.map((f) => `       \u00b7 ${f}`).join('\n'),
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

// --- 3-bis. Cancello: la zona sinistra della toolbar non porta filtri ------
if (filtriInZonaSinistra.length) {
  rosso = true
  console.error(
    `\n[ko] ${filtriInZonaSinistra.length} file mettono un FILTRO in`
    + ' `app-page-toolbar-start`:\n'
    + filtriInZonaSinistra.map((f) => `       · ${f}`).join('\n')
    + '\n\n     Quella classe e\' la zona sinistra della toolbar per cio\' che filtri NON\n'
    + '     e\': un titolo, un pulsante «torna alla lista». Un filtro messo li\' non\n'
    + '     scende nel drawer sotto i 1024px e non conta nel segno — e nessuno se ne\n'
    + '     accorge, perche\' da desktop la resa e\' identica.\n'
    + '     ⇒ il posto di un filtro e\' `<FiltriLista :store="store">`.',
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
