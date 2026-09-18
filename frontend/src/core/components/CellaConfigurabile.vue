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
import SiNoTag from './SiNoTag.vue'

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
function formatValue(value, formato, tipoDato) {
  if (formato === 'yesno' || (!formato && tipoDato === 'boolean')) {
    return h(SiNoTag, { value })
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
    case 'number':
      return formatNumber(value)
    case 'percent_2':
      return formatNumber(value, { minimumFractionDigits: 2 }) + ' %'
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
      return formatValue(value, props.col.formato, props.col.tipo_dato)
    }
  },
}
</script>
