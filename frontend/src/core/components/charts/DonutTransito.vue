<script setup>
// Scopo: Donut a 2 spicchi "transitato vs fermo" per le card della dashboard
//        fatturazione (brief-design-dashboard-fatturazione §7, decisione D-1:
//        chart.js via PrimeVue <Chart>). Unico punto dell'app che parla con
//        chart.js: le view usano solo questo wrapper.
//
//        Palette: SOLO variabili theme.css (--app-chart-transitato /
//        --app-chart-fermo / --app-chart-track), risolte a runtime con
//        getComputedStyle e ricalcolate al toggle dark/light — mai colori
//        hardcoded (feedback_css_centralizzazione). La coppia green-600 /
//        orange-600 e' validata CVD+contrasto su entrambe le superfici.
//        L'identita' non e' mai solo-colore: percentuale al centro +
//        mini-legenda con etichetta e valore per ogni spicchio.
import { ref, computed, watch, onMounted } from 'vue'
import Chart from 'primevue/chart'
import { useUiStore } from '../../../stores/ui'
import { formatCurrency, formatNumber } from '../../utils/format'

const props = defineProps({
  // Valore avanzato verso l'area successiva del funnel.
  transitato: { type: Number, required: true },
  // Valore ancora fermo nell'area (totale - transitato).
  fermo: { type: Number, required: true },
  // 'currency' per le aree in euro, 'count' per le aree a conteggi.
  format: { type: String, default: 'currency' },
  // Etichette tradotte fornite dal caller (il wrapper resta i18n-agnostico).
  labelTransitato: { type: String, required: true },
  labelFermo: { type: String, required: true },
  // Diametro del donut in px.
  size: { type: Number, default: 132 },
})

const ui = useUiStore()

// Colori risolti dalle variabili CSS. Ref (non computed) perche' il valore
// dipende dal DOM: ricalcolato esplicitamente al mount e al toggle tema.
const palette = ref({ transitato: '#888', fermo: '#888', track: '#888', surface: '#fff' })

// Scopo: risolve le variabili tema in colori concreti per chart.js
// (il canvas non sa leggere var(--...)).
function resolvePalette() {
  const style = getComputedStyle(document.documentElement)
  const read = (name, fallback) => style.getPropertyValue(name).trim() || fallback
  palette.value = {
    transitato: read('--app-chart-transitato', '#16a34a'),
    fermo: read('--app-chart-fermo', '#ea580c'),
    track: read('--app-chart-track', '#52525b'),
    // Bordo spicchi = colore card: crea il gap di 2px fra gli spicchi.
    surface: read('--app-card-bg', '#ffffff'),
  }
}

onMounted(resolvePalette)
watch(() => ui.isDark, () => resolvePalette(), { flush: 'post' })

const totale = computed(() => props.transitato + props.fermo)
const isEmpty = computed(() => totale.value <= 0)

const pctTransitato = computed(() => {
  if (isEmpty.value) return null
  return Math.round((props.transitato / totale.value) * 100)
})

// Scopo: formatta un valore per legenda/tooltip secondo la natura dell'area.
function formatValue(value) {
  return props.format === 'currency'
    ? formatCurrency(value)
    : formatNumber(value, { minimumFractionDigits: 0 })
}

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

const chartOptions = computed(() => ({
  cutout: '68%',
  responsive: false,
  plugins: {
    // La legenda vive sotto il donut (mini-legenda HTML con i valori).
    legend: { display: false },
    tooltip: {
      enabled: !isEmpty.value,
      callbacks: {
        label: (ctx) => ` ${ctx.label}: ${formatValue(ctx.parsed)}`,
      },
    },
  },
}))
</script>

<template>
  <div class="app-donut-transito">
    <div class="app-donut-transito-plot" :style="{ width: `${size}px`, height: `${size}px` }">
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
    <!-- Mini-legenda: dot colore + etichetta + valore per ogni spicchio. -->
    <div class="app-donut-transito-legend">
      <div class="app-donut-transito-legend-row">
        <span class="app-donut-transito-dot" :style="{ background: palette.transitato }" />
        <span class="app-donut-transito-label">{{ labelTransitato }}</span>
        <span class="app-donut-transito-value">{{ formatValue(transitato) }}</span>
      </div>
      <div class="app-donut-transito-legend-row">
        <span class="app-donut-transito-dot" :style="{ background: palette.fermo }" />
        <span class="app-donut-transito-label">{{ labelFermo }}</span>
        <span class="app-donut-transito-value">{{ formatValue(fermo) }}</span>
      </div>
    </div>
  </div>
</template>
