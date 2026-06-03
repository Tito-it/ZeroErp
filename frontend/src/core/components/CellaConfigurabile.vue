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
import { useI18n } from 'vue-i18n'
import { displayDate, displayTimestamp } from '../utils/date'
import { formatCurrency, formatNumber } from '../utils/format'

// Formatter built-in da `formato` del catalogo. Il caller puo' sovrascrivere
// completamente via slot `cell-{codice}` (prop `cellSlot`).
function formatValue(value, formato, t) {
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
    case 'yesno':
      return value ? t('common.yes') : t('common.no')
    default:
      return String(value)
  }
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
    const { t } = useI18n()
    return () => {
      const value = props.data?.[props.col.campo_sorgente]
      if (props.cellSlot) {
        return props.cellSlot({ data: props.data, value, col: props.col })
      }
      return formatValue(value, props.col.formato, t)
    }
  },
}
</script>
