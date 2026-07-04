<script setup>
// Scopo: Visualizzazione "transitato vs fermo" per le card della dashboard
//        fatturazione (brief-design-dashboard-fatturazione §7, decisione D-1:
//        chart.js via PrimeVue <Chart>). Unico punto dell'app che parla con
//        chart.js: le view usano solo questo wrapper.
//        Due modalita':
//          - mode="donut"    → donut a 2 spicchi con percentuale al centro
//                              (aree con valore in euro, D-4);
//          - mode="fraction" → frazione n/n al posto del grafico (aree a
//                              conteggi, D-2/D-3) — stessa altezza e stessa
//                              mini-legenda, cosi' le card restano allineate
//                              senza duplicare markup nei caller.
//
//        Palette: SOLO variabili theme.css (--app-chart-transitato /
//        --app-chart-fermo / --app-chart-track), risolte a runtime con
//        getComputedStyle e ricalcolate al toggle dark/light — mai colori
//        hardcoded (feedback_css_centralizzazione). La risoluzione e' cachata
//        a livello modulo per tema (un solo getComputedStyle per toggle,
//        non uno per istanza). L'identita' non e' mai solo-colore:
//        percentuale/frazione + mini-legenda con etichetta e valore.
import { ref, computed, watch, onMounted } from 'vue'
import Chart from 'primevue/chart'
import { useUiStore } from '../../../stores/ui'
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
  // Etichette tradotte fornite dal caller (il wrapper resta i18n-agnostico).
  labelTransitato: { type: String, required: true },
  labelFermo: { type: String, required: true },
  // Diametro del donut / altezza della frazione, in px.
  size: { type: Number, default: 132 },
})

const ui = useUiStore()

const _FALLBACK_PALETTE = {
  transitato: '#16a34a',
  fermo: '#ea580c',
  track: '#52525b',
  surface: '#ffffff',
}

// Cache modulo-level per tema: N istanze donut condividono UNA risoluzione
// getComputedStyle per toggle dark/light (evita style recalc moltiplicati).
const _paletteCache = new Map()

// Scopo: risolve le variabili tema in colori concreti per chart.js
// (il canvas non sa leggere var(--...)), con cache per tema.
function resolvePalette(isDark) {
  const key = isDark ? 'dark' : 'light'
  if (_paletteCache.has(key)) return _paletteCache.get(key)
  const style = getComputedStyle(document.documentElement)
  const read = (name, fallback) => style.getPropertyValue(name).trim() || fallback
  const resolved = {
    transitato: read('--app-chart-transitato', _FALLBACK_PALETTE.transitato),
    fermo: read('--app-chart-fermo', _FALLBACK_PALETTE.fermo),
    track: read('--app-chart-track', _FALLBACK_PALETTE.track),
    // Bordo spicchi = colore card: crea il gap di 2px fra gli spicchi.
    surface: read('--app-card-bg', _FALLBACK_PALETTE.surface),
  }
  _paletteCache.set(key, resolved)
  return resolved
}

const palette = ref(_FALLBACK_PALETTE)

onMounted(() => { palette.value = resolvePalette(ui.isDark) })
watch(() => ui.isDark, (isDark) => { palette.value = resolvePalette(isDark) }, { flush: 'post' })

const totale = computed(() => props.transitato + props.fermo)
const isEmpty = computed(() => totale.value <= 0)

const pctTransitato = computed(() => {
  if (isEmpty.value) return null
  return Math.round((props.transitato / totale.value) * 100)
})

// Scopo: formatta un valore per legenda/tooltip secondo la natura del dato.
function formatValue(value) {
  return props.format === 'currency'
    ? formatCurrency(value)
    : formatNumber(value, { minimumFractionDigits: 0 })
}

// Righe della mini-legenda (dot + etichetta + valore) — un solo markup
// per entrambe le modalita'.
const legendRows = computed(() => [
  { key: 'transitato', color: palette.value.transitato, label: props.labelTransitato, value: formatValue(props.transitato) },
  { key: 'fermo', color: palette.value.fermo, label: props.labelFermo, value: formatValue(props.fermo) },
])

const chartData = computed(() => {
  // Nessun dato: anello neutro pieno (nessun semaforo da comunicare).
  if (isEmpty.value) {
    return {
      labels: [''],
      datasets: [{ data: [1], backgroundColor: [palette.value.track], borderWidth: 0 }],
    }
  }
  return {
    labels: [props.labelTransitato, props.labelFermo],
    datasets: [{
      data: [props.transitato, props.fermo],
      backgroundColor: [palette.value.transitato, palette.value.fermo],
      // Gap 2px fra gli spicchi, colore superficie card.
      borderColor: palette.value.surface,
      borderWidth: 2,
    }],
  }
})

// Options STATICHE (non computed): PrimeVue <Chart> fa destroy+reinit a ogni
// cambio di riferimento di `options` — con l'oggetto stabile solo `data`
// triggera il redraw. Lo stato "vuoto" passa dal filter (closure su isEmpty).
const chartOptions = {
  cutout: '68%',
  responsive: false,
  plugins: {
    // La legenda vive sotto il donut (mini-legenda HTML con i valori).
    legend: { display: false },
    tooltip: {
      // Niente tooltip sull'anello neutro "nessun dato".
      filter: () => !isEmpty.value,
      callbacks: {
        label: (ctx) => ` ${ctx.label}: ${formatValue(ctx.parsed)}`,
      },
    },
  },
}
</script>

<template>
  <div class="app-donut-transito">
    <!-- Modalita' donut: grafico + percentuale al centro. -->
    <div
      v-if="mode === 'donut'"
      class="app-donut-transito-plot"
      :style="{ width: `${size}px`, height: `${size}px` }"
    >
      <Chart
        type="doughnut"
        :data="chartData"
        :options="chartOptions"
        :width="size"
        :height="size"
      />
      <!-- Percentuale al centro: la lettura primaria non dipende dal colore. -->
      <div class="app-donut-transito-center">
        <span v-if="pctTransitato !== null" class="app-donut-transito-pct">{{ pctTransitato }}%</span>
        <span v-else class="app-donut-transito-pct app-donut-transito-pct-empty">—</span>
      </div>
    </div>

    <!-- Modalita' fraction: n/n grande, stessa altezza del plot donut. -->
    <div
      v-else
      class="app-donut-transito-fraction"
      :style="{ height: `${size}px` }"
    >
      {{ isEmpty ? '—' : `${formatValue(transitato)}/${formatValue(totale)}` }}
    </div>

    <!-- Mini-legenda: dot colore + etichetta + valore per ogni voce. -->
    <div class="app-donut-transito-legend">
      <div v-for="row in legendRows" :key="row.key" class="app-donut-transito-legend-row">
        <span class="app-donut-transito-dot" :style="{ background: row.color }" />
        <span class="app-donut-transito-label">{{ row.label }}</span>
        <span class="app-donut-transito-value">{{ row.value }}</span>
      </div>
    </div>
  </div>
</template>
