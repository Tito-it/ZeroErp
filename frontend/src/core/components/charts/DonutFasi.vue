<script setup>
// Scopo: Facciata donut a N spicchi per FASE del serbatoio pre-commessa
//        (Situazione aperta v2, DL-16): un segmento per fase con documenti,
//        colore dalla palette fase (allineata a faseDocumentoSeverity), centro
//        = totale area. Skin sottile su DonutBase. Misura mista (DL-11/16): la
//        facciata riceve i valori già decisi dal caller (euro o conteggi) e un
//        flag di formattazione — non ri-decide la misura (il BE la serve nel
//        payload, `valore_totale` null = area a conteggi).
//        Palette: variabili theme.css --app-chart-fase-* (mai colori
//        hardcoded, feedback_css_centralizzazione).
import { computed } from 'vue'
import DonutBase from './DonutBase.vue'
import { formatCurrency, formatNumber } from '../../utils/format'

const props = defineProps({
  // Segmenti-fase dell'area: [{ fase, label, value }] — le fasi con value > 0.
  //  - fase: codice normalizzato (mappa il colore);
  //  - label: etichetta i18n dal caller (la facciata resta i18n-agnostica);
  //  - value: valore_totale (aree euro) o n_documenti (aree a conteggi).
  fasi: { type: Array, required: true },
  // 'currency' (aree euro) | 'count' (aree a conteggi).
  format: { type: String, default: 'currency' },
  // Diametro del donut, in px.
  size: { type: Number, default: 132 },
})

// Fase → variabile colore tema, allineata a FASE_DOCUMENTO_MAP (severity.js):
// APERTO grigio, IN_ATTESA azzurro, IN_CORSO arancio, CHIUSO verde. Le fasi
// fuori mappa (accodate fail-visible dal BE) → colore neutro di default.
const FASE_CHART_VAR = {
  APERTO: { name: '--app-chart-fase-aperto', fallback: '#71717a' },
  IN_ATTESA: { name: '--app-chart-fase-in-attesa', fallback: '#2563eb' },
  IN_CORSO: { name: '--app-chart-fase-in-corso', fallback: '#ea580c' },
  CHIUSO: { name: '--app-chart-fase-chiuso', fallback: '#16a34a' },
}
const FASE_CHART_DEFAULT = { name: '--app-chart-fase-default', fallback: '#a1a1aa' }

// Scopo: formatta un valore per legenda/tooltip/centro secondo la natura del dato.
function formatValue(value) {
  return props.format === 'currency'
    ? formatCurrency(value)
    : formatNumber(value, { minimumFractionDigits: 0 })
}

const segments = computed(() =>
  props.fasi.map((f) => {
    const chartVar = FASE_CHART_VAR[f.fase] ?? FASE_CHART_DEFAULT
    const value = Number(f.value ?? 0)
    return {
      label: f.label,
      cssVar: chartVar.name,
      fallback: chartVar.fallback,
      value,
      formatted: formatValue(value),
    }
  })
)

const totale = computed(() => segments.value.reduce((acc, s) => acc + s.value, 0))
// Centro = totale area (lettura primaria non-colore); null se vuoto.
const centerText = computed(() =>
  totale.value <= 0 ? null : formatValue(totale.value)
)
</script>

<template>
  <DonutBase :segments="segments" :center-text="centerText" :size="size" />
</template>
