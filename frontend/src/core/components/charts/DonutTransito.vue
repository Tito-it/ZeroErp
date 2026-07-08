<script setup>
// Scopo: Facciata "transitato vs fermo" a 2 spicchi (percentuale al centro) o
//        frazione n/n per le aree a conteggi. Skin sottile su DonutBase (che
//        possiede la macchina chart.js / risoluzione tema / legenda / options
//        statiche): qui vivono SOLO la semantica binaria e la formattazione per
//        natura del dato. API pubblica invariata (regola del 2, ok Tid):
//        consumer SituazioneApertaView (transito per area) e
//        DashboardCompetenzaView (copertura mese Lente 1).
//        Palette: variabili theme.css --app-chart-transitato/-fermo (mai
//        colori hardcoded, feedback_css_centralizzazione); i fallback esatti
//        restano allineati alla coppia green-600/orange-600.
import { computed } from 'vue'
import DonutBase from './DonutBase.vue'
import { formatCurrency, formatNumber } from '../../utils/format'

const props = defineProps({
  // Valore avanzato verso l'area successiva del funnel.
  transitato: { type: Number, required: true },
  // Valore ancora fermo nell'area (totale - transitato).
  fermo: { type: Number, required: true },
  // 'donut' (default) oppure 'fraction' (n/n, aree a conteggi).
  mode: {
    type: String,
    default: 'donut',
    validator: (v) => ['donut', 'fraction'].includes(v),
  },
  // 'currency' per le aree in euro, 'count' per le aree a conteggi.
  format: { type: String, default: 'currency' },
  // Etichette tradotte fornite dal caller (la facciata resta i18n-agnostica).
  labelTransitato: { type: String, required: true },
  labelFermo: { type: String, required: true },
  // Diametro del donut / altezza della frazione, in px.
  size: { type: Number, default: 132 },
})

// Scopo: formatta un valore per legenda/tooltip secondo la natura del dato.
function formatValue(value) {
  return props.format === 'currency'
    ? formatCurrency(value)
    : formatNumber(value, { minimumFractionDigits: 0 })
}

const totale = computed(() => props.transitato + props.fermo)

const segments = computed(() => [
  {
    label: props.labelTransitato,
    cssVar: '--app-chart-transitato',
    fallback: '#16a34a',
    value: props.transitato,
    formatted: formatValue(props.transitato),
  },
  {
    label: props.labelFermo,
    cssVar: '--app-chart-fermo',
    fallback: '#ea580c',
    value: props.fermo,
    formatted: formatValue(props.fermo),
  },
])

// Centro donut: % transitato (lettura primaria non-colore); null se vuoto
// (DonutBase mostra '—').
const centerText = computed(() => {
  if (totale.value <= 0) return null
  return `${Math.round((props.transitato / totale.value) * 100)}%`
})

// Modalità fraction: n/n grande; null se vuoto (DonutBase mostra '—').
const fractionText = computed(() =>
  totale.value <= 0
    ? null
    : `${formatValue(props.transitato)}/${formatValue(totale.value)}`
)
</script>

<template>
  <DonutBase
    :segments="segments"
    :mode="mode"
    :center-text="centerText"
    :fraction-text="fractionText"
    :size="size"
  />
</template>
