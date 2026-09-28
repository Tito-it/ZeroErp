<script>
// Scopo: rendering di una cella di <ListaConfigurabile>. Estratto 2026-06-02
// (regola del 2): lo stesso blocco "slot custom del caller `cell-{codice}`
// oppure formatter built-in da `formato`" era duplicato fra la Column #body e
// la riga di espansione (#expansion). Qui vive una volta sola.
//
// Render function (non template): permette di invocare DIRETTAMENTE la slot
// function del caller (`cellSlot`) passata come prop — cosa scomoda da fare in
// un `<template>` con slot dinamici — e di cadere sul formatter di default
// quando il caller non fornisce lo slot.
import { h } from 'vue'
import { displayDate, displayTimestamp } from '../utils/date'
import { formatCurrency, formatNumber } from '../utils/format'
import NaturaDocTag from './NaturaDocTag.vue'
import SiNoTag from './SiNoTag.vue'

// ⭐ `natura_doc` (2026-09-18, ok Tid — regola del 2 alla QUARTA lista): la
//    colonna «Natura» di un documento fiscale e' il BB `NaturaDocTag` in modo
//    `sempre`, come `yesno` e' `SiNoTag`. Lo stesso slot
//    `<NaturaDocTag :codice :descrizione sempre>` era scritto in quattro liste
//    (fatture, documenti del lotto, picker delle rate, rate fuori capienza):
//    *una natura in lista e' una riga di CSV, non uno slot*.
// ⚠️ Il Tag vuole DUE campi della riga: la descrizione e' il `campo_sorgente`
//    della colonna (il valore), il codice e' la GEMELLA `natura_doc_codice_interno`
//    — il nome con cui OGNI vista e funzione del DB proietta
//    `config.nature_doc_fiscale.codice_interno`. Non e' una stringa magica: e'
//    il contratto della colonna, e lo presidia `test_lista_proiezione_campo_sorgente`
//    (che LEGGE questa costante dal sorgente, via `campi_gemelli_per_formato`)
//    sulla proiezione di ogni lista che dichiara questo formato. Se la riga non la porta, il BB rende `—` su
//    ogni riga: un difetto che si VEDE, non una natura inventata.
const CAMPO_GEMELLO_NATURA_DOC = 'natura_doc_codice_interno'

// Formatter built-in da `formato` del catalogo. Il caller puo' sovrascrivere
// completamente via slot `cell-{codice}` (prop `cellSlot`).
// ⭐ `yesno` non e' piu' testo dal 2026-09-14 (ok Tid): e' il BB `SiNoTag`, la
//    stessa resa che tre liste si erano riscritte in uno slot — una delle tre
//    SOPRA una colonna che a catalogo aveva gia' `formato=yesno`. Un booleano
//    in lista e' una riga di `ui.lista_colonna`, non uno slot; il `null` resta
//    vuoto (lo decide il BB, non il formatter).
// ⚠️ E un `tipo_dato = boolean` SENZA formato prende la stessa resa: prima
//    cadeva su `String(value)`, cioe' «true»/«false» grezzi a video (la
//    `is_scaduta` delle offerte lo faceva davvero). Il `formato=yesno` nel
//    seed resta la dichiarazione; questo e' il ripiego per chi non l'ha scritta.
// ⚠️ `data` (la riga) serve al solo `natura_doc`, che legge la gemella.
function formatValue(value, formato, tipoDato, data = null) {
  if (formato === 'yesno' || (!formato && tipoDato === 'boolean')) {
    return h(SiNoTag, { value })
  }
  if (formato === 'natura_doc') {
    return h(NaturaDocTag, {
      codice: data?.[CAMPO_GEMELLO_NATURA_DOC] ?? null,
      descrizione: value ?? null,
      sempre: true,
    })
  }
  if (value == null) return ''
  switch (formato) {
    case 'date_short':
      return displayDate(value)
    case 'datetime':
    case 'datetime_short':
      return displayTimestamp(value)
    case 'currency_eur':
      return formatCurrency(value)
    // Il prezzo UNITARIO a 6 decimali dei listini (2026-09-28, righe dei
    // documenti di vendita): l'importo resta `currency_eur`. Gemello
    // dell'export: `locale_formatters.format_number`.
    case 'currency_eur_6':
      return formatCurrency(value, { minimumFractionDigits: 6, maximumFractionDigits: 6 })
    case 'number':
      return formatNumber(value)
    // ⭐ Il valore e' GIA' in percentuale (10 = 10%), come lo salva il modello
    //    (`sconto_percentuale`). E' questa la sede del significato: l'export
    //    (`locale_formatters`) lo leggeva come frazione fino al 2026-09-28 —
    //    lo stesso formato diceva due cose (decisione di Tid: vale questa).
    case 'percent_2':
      return formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' %'
    default:
      return String(value)
  }
}

// Scopo: il testo della cella cosi' come il formatter di default lo rende,
//        oppure `null` quando la cella non e' testo (booleano → Tag, slot del
//        caller). Serve a `ListaConfigurabile` per il `title` delle celle
//        troncate in ellissi: la stessa funzione del rendering, cosi' il
//        tooltip non puo' dire una cosa diversa da quella a video.
export function testoCella(col, data, cellSlot = null) {
  if (cellSlot) return null
  if (col.formato === 'yesno' || (!col.formato && col.tipo_dato === 'boolean')) return null
  // Un Tag, non testo: come `yesno`.
  if (col.formato === 'natura_doc') return null
  const value = data?.[col.campo_sorgente]
  if (value == null) return null
  const testo = formatValue(value, col.formato, col.tipo_dato)
  return typeof testo === 'string' && testo !== '' ? testo : null
}

export default {
  name: 'CellaConfigurabile',
  props: {
    // Descrittore colonna (codice, campo_sorgente, formato, ...).
    col: { type: Object, required: true },
    // Riga dati.
    data: { type: Object, required: true },
    // Slot function del caller per questa colonna (`$slots['cell-<codice>']`),
    // oppure null/undefined per usare il formatter di default.
    cellSlot: { type: Function, default: null },
  },
  setup(props) {
    return () => {
      const value = props.data?.[props.col.campo_sorgente]
      if (props.cellSlot) {
        return props.cellSlot({ data: props.data, value, col: props.col })
      }
      return formatValue(value, props.col.formato, props.col.tipo_dato, props.data)
    }
  },
}
</script>
