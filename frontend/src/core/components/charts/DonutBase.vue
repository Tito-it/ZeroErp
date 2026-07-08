<script setup>
// Scopo: Substrato riusabile dei donut delle card dashboard fatturazione
//        (regola del 2, ok Tid — estratto da DonutTransito quando è servito un
//        secondo donut, per fase). Possiede SOLO la macchina condivisa: unico
//        wrapper chart.js dell'app (via PrimeVue <Chart>), risoluzione delle
//        variabili tema in colori concreti con cache module-level per
//        (tema, variabile) — un solo getComputedStyle per toggle dark/light —,
//        anello neutro "nessun dato", options STATICHE (solo `data` reattivo →
//        niente destroy+reinit del <Chart>), mini-legenda dot+label+valore.
//        Le facciate (DonutTransito 2-spicchi, DonutFasi N-spicchi) gli passano
//        i segmenti già decisi e restano sottili.
//        Palette: SOLO variabili theme.css (--app-chart-* / --app-card-bg /
//        --app-chart-track), mai colori hardcoded (feedback_css_centralizzazione).
//        L'identità non è mai solo-colore: centro (%/totale) + mini-legenda con
//        etichetta e valore.
import { ref, computed, watch, onMounted } from 'vue'
import Chart from 'primevue/chart'
import { useUiStore } from '../../../stores/ui'

const props = defineProps({
  // Segmenti del donut: { label, cssVar, fallback, value, formatted }.
  //  - cssVar/fallback: variabile tema del colore spicchio (risolta qui);
  //  - value: numero per l'ampiezza dello spicchio;
  //  - formatted: stringa pronta per legenda/tooltip (la facciata formatta
  //    secondo la natura del dato — euro o conteggio).
  segments: { type: Array, required: true },
  // 'donut' (default) oppure 'fraction' (n/n, aree a conteggi di DonutTransito).
  mode: {
    type: String,
    default: 'donut',
    validator: (v) => ['donut', 'fraction'].includes(v),
  },
  // Testo al centro del donut (% transitato o totale area); null = centro vuoto.
  centerText: { type: String, default: null },
  // Testo grande della modalità fraction; null = '—'.
  fractionText: { type: String, default: null },
  // Diametro del donut / altezza della frazione, in px.
  size: { type: Number, default: 132 },
  // Rende `centerText` come didascalia SOTTO il donut invece che sovrapposto al
  // centro. Serve per i totali lunghi (euro/conteggi di DonutFasi): un numero
  // che sborda dal buco finirebbe sull'anello, illeggibile (testo scuro su
  // colore fase, es. APERTO grigio). DonutTransito lascia default (% corta,
  // sta nel buco → centro classico).
  centerBelow: { type: Boolean, default: false },
})

const ui = useUiStore()

// Variabili substrato comuni a tutte le facciate (non specifiche di una skin).
const _TRACK = { name: '--app-chart-track', fallback: '#52525b' }
// Bordo spicchi = colore card: crea il gap di 2px fra gli spicchi.
const _SURFACE = { name: '--app-card-bg', fallback: '#ffffff' }

// Cache module-level per (tema, variabile): N istanze/facciate condividono la
// risoluzione, e un solo getComputedStyle per toggle (le letture di più
// proprietà dallo stesso getComputedStyle sono cheap).
const _colorCache = new Map()

// Scopo: risolve un set di variabili tema in colori concreti (il canvas non
//        legge var(--...)), con cache per tema — chiama getComputedStyle solo
//        se almeno una variabile non è ancora in cache per quel tema.
function resolveVars(isDark, specs) {
  const theme = isDark ? 'dark' : 'light'
  const missing = specs.filter((s) => !_colorCache.has(`${theme}:${s.name}`))
  if (missing.length) {
    const style = getComputedStyle(document.documentElement)
    for (const s of missing) {
      const value = style.getPropertyValue(s.name).trim() || s.fallback
      _colorCache.set(`${theme}:${s.name}`, value)
    }
  }
  const out = {}
  for (const s of specs) out[s.name] = _colorCache.get(`${theme}:${s.name}`)
  return out
}

// Tutte le variabili da risolvere: quelle dei segmenti + track + surface.
const varSpecs = computed(() => [
  ...props.segments.map((s) => ({ name: s.cssVar, fallback: s.fallback })),
  _TRACK,
  _SURFACE,
])

const colors = ref({})
// Scopo: (ri)risolve i colori concreti per il tema corrente.
function refreshColors(isDark) {
  colors.value = resolveVars(isDark, varSpecs.value)
}
onMounted(() => refreshColors(ui.isDark))
watch(() => ui.isDark, (isDark) => refreshColors(isDark), { flush: 'post' })
// Segmenti con cssVar diverse (skin/area diversa) → ri-risolve i nuovi colori.
watch(varSpecs, () => refreshColors(ui.isDark))

const totale = computed(() => props.segments.reduce((acc, s) => acc + (s.value || 0), 0))
const isEmpty = computed(() => totale.value <= 0)

const segmentColors = computed(() =>
  props.segments.map((s) => colors.value[s.cssVar] || s.fallback)
)

// Righe della mini-legenda (dot + etichetta + valore) — un solo markup.
const legendRows = computed(() =>
  props.segments.map((s, i) => ({
    key: `${s.label}-${i}`,
    color: segmentColors.value[i],
    label: s.label,
    value: s.formatted,
  }))
)

const chartData = computed(() => {
  const track = colors.value[_TRACK.name] || _TRACK.fallback
  // Nessun dato: anello neutro pieno (nessun semaforo da comunicare).
  if (isEmpty.value) {
    return {
      labels: [''],
      datasets: [{ data: [1], backgroundColor: [track], borderWidth: 0 }],
    }
  }
  return {
    labels: props.segments.map((s) => s.label),
    datasets: [{
      data: props.segments.map((s) => s.value),
      backgroundColor: segmentColors.value,
      // Gap 2px fra gli spicchi, colore superficie card.
      borderColor: colors.value[_SURFACE.name] || _SURFACE.fallback,
      borderWidth: 2,
    }],
  }
})

// Formatted per indice, letto a runtime dal closure delle options (che restano
// STATICHE per non forzare destroy+reinit del <Chart>).
const formattedByIndex = computed(() => props.segments.map((s) => s.formatted))

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
        label: (ctx) => ` ${ctx.label}: ${formattedByIndex.value[ctx.dataIndex] ?? ''}`,
      },
    },
  },
}
</script>

<template>
  <div class="app-donut">
    <!-- Modalità donut: grafico + centro (%/totale). -->
    <div
      v-if="mode === 'donut'"
      class="app-donut-plot"
      :style="{ width: `${size}px`, height: `${size}px` }"
    >
      <Chart
        type="doughnut"
        :data="chartData"
        :options="chartOptions"
        :width="size"
        :height="size"
      />
      <!-- Centro: lettura primaria non-colore (— se vuoto, altrimenti il testo
           deciso dalla facciata). -->
      <div class="app-donut-center">
        <span v-if="isEmpty" class="app-donut-center-value app-donut-center-value--empty">—</span>
        <span v-else-if="centerText !== null" class="app-donut-center-value">{{ centerText }}</span>
      </div>
    </div>

    <!-- Modalità fraction: testo grande, stessa altezza del plot donut. -->
    <div
      v-else
      class="app-donut-fraction"
      :style="{ height: `${size}px` }"
    >
      {{ fractionText ?? '—' }}
    </div>

    <!-- Mini-legenda: dot colore + etichetta + valore per ogni segmento. -->
    <div class="app-donut-legend">
      <div v-for="row in legendRows" :key="row.key" class="app-donut-legend-row">
        <span class="app-donut-dot" :style="{ background: row.color }" />
        <span class="app-donut-label">{{ row.label }}</span>
        <span class="app-donut-value">{{ row.value }}</span>
      </div>
    </div>
  </div>
</template>
