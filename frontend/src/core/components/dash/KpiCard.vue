<script setup>
// Scopo: Card KPI riusabile per le dashboard configurabili — numero,
//        etichetta, semaforo da soglia e deep-link al target.
//
// Stati resi, in ordine di precedenza:
//   1. caricamento  -> skeleton al posto del numero (la card c'e' gia')
//   2. degradato    -> contatore fallito lato BE (`ok:false`): trattino
//                      e hint, MAI uno zero. Uno zero inventato e' una
//                      bugia: "nessun documento fermo" e "non lo so"
//                      sono informazioni opposte.
//   3. senza numero -> widget informativo senza contatore_key (es. card
//                      di benvenuto): solo etichetta e hint
//   4. normale      -> numero + semaforo
//
// SOGLIA (grammatica FE, il DB la conserva opaca — brief DB §3f):
//   { "warn": 10, "danger": 30, "dir": "asc" }
//   dir 'asc'  (default): piu' alto = peggio  (es. documenti fermi)
//   dir 'desc'          : piu' basso = peggio (es. giorni di copertura)
// In v1 la soglia e' vuota su tutti i widget seedati -> semaforo neutro.
// La valutazione esiste comunque dal giorno uno: quando le soglie
// verranno tarate sui dati reali bastera' popolare il campo a DB, senza
// toccare il frontend (sviluppo concentrico).

import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  // Widget risolto dalla fn DB: {codice, etichetta, etichetta_i18n_key,
  // tipo_widget, deep_link, contatore_key, soglia, ordine, visibile}
  widget: { type: Object, required: true },
  // Contatore {valore, ok} dall'endpoint batch, o null se il widget non
  // ha contatore_key / il valore non e' ancora arrivato.
  contatore: { type: Object, default: null },
  // TRUE mentre la fetch dei contatori e' in volo.
  loading: { type: Boolean, default: false },
  // FALSE quando il deep-link non e' risolvibile: la card resta visibile
  // ma non cliccabile (nessun vicolo cieco).
  cliccabile: { type: Boolean, default: true },
})

const emit = defineEmits(['apri'])

const { t, te } = useI18n()

// Etichetta: chiave i18n se risolvibile, altrimenti l'etichetta di
// catalogo. `te()` evita di stampare la chiave grezza quando la
// traduzione non e' ancora stata scritta.
const label = computed(() => {
  const key = props.widget?.etichetta_i18n_key
  if (key && te(key)) return t(key)
  return props.widget?.etichetta || props.widget?.codice || ''
})

// Il widget ha un numero da mostrare?
const haContatore = computed(() => Boolean(props.widget?.contatore_key))

// Contatore non disponibile: fallito lato BE (`ok:false`) oppure MAI
// arrivato (fetch batch fallita: `contatore` resta null a caricamento
// finito). Entrambi degradano la card — senza il secondo caso una fetch
// contatori fallita lascerebbe un riquadro muto, indistinguibile da una
// card informativa senza numero.
const degradato = computed(
  () =>
    haContatore.value &&
    !props.loading &&
    (props.contatore === null || props.contatore.ok === false),
)

const valore = computed(() => {
  if (!haContatore.value || degradato.value) return null
  return props.contatore?.valore ?? null
})

// Semaforo: 'neutro' | 'warn' | 'danger'. Neutro anche quando la soglia
// e' assente/vuota (caso v1) o il valore non e' noto.
const severita = computed(() => {
  const soglia = props.widget?.soglia
  const v = valore.value
  if (!soglia || typeof soglia !== 'object' || v === null) return 'neutro'

  const { warn, danger, dir = 'asc' } = soglia
  const peggioSopra = dir !== 'desc'

  if (typeof danger === 'number' && _supera(v, danger, peggioSopra)) return 'danger'
  if (typeof warn === 'number' && _supera(v, warn, peggioSopra)) return 'warn'
  return 'neutro'
})

// Scopo: confronto direzionale del valore contro una soglia.
function _supera(valore, soglia, peggioSopra) {
  return peggioSopra ? valore >= soglia : valore <= soglia
}

function onClick() {
  if (!props.cliccabile) return
  emit('apri', props.widget)
}

// Accessibilita': la card e' interattiva solo quando ha davvero un
// target, altrimenti resta un riquadro informativo non focusabile.
function onKeydown(event) {
  if (!props.cliccabile) return
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    onClick()
  }
}
</script>

<template>
  <div
    class="app-dash-card kpi-card"
    :class="[`kpi-sev-${severita}`, { 'is-clickable': cliccabile }]"
    :role="cliccabile ? 'button' : null"
    :tabindex="cliccabile ? 0 : null"
    @click="onClick"
    @keydown="onKeydown"
  >
    <div class="app-dash-card-title kpi-title">{{ label }}</div>

    <!-- 1. caricamento: la card esiste gia', manca solo il numero -->
    <div v-if="haContatore && loading && contatore === null" class="kpi-skeleton" />

    <!-- 2. degradato: mai uno zero inventato -->
    <template v-else-if="degradato">
      <div class="app-dash-stat-n kpi-degradato">—</div>
      <div class="app-dash-card-hint">{{ t('home.kpi_non_disponibile') }}</div>
    </template>

    <!-- 4. normale -->
    <div v-else-if="haContatore && valore !== null" class="app-dash-stat-n">
      {{ valore }}
    </div>

    <!-- 3. widget informativo senza contatore: nessun numero -->
  </div>
</template>

<style scoped>
.kpi-card {
  /* Il layout di base (bordo, radius, hover) arriva da .app-dash-card in
     main.css: qui solo cio' che e' specifico della card KPI. */
  justify-content: flex-start;
  gap: 0.35rem;
}

.kpi-card.is-clickable {
  cursor: pointer;
}

.kpi-card.is-clickable:focus-visible {
  outline: 2px solid var(--app-focus-ring, var(--p-primary-color));
  outline-offset: 2px;
}

.kpi-title {
  /* L'etichetta non deve spingere il numero fuori card su titoli lunghi. */
  overflow-wrap: anywhere;
}

/* Semaforo: bordo sinistro colorato, non riempimento — resta leggibile
   in dark mode e non compete col numero. Neutro = nessuna decorazione. */
.kpi-sev-warn {
  border-left: 3px solid var(--app-severity-warn, var(--p-orange-500));
}

.kpi-sev-danger {
  border-left: 3px solid var(--app-severity-danger, var(--p-red-500));
}

.kpi-degradato {
  color: var(--app-text-muted, var(--p-text-muted-color));
}

.kpi-skeleton {
  height: 1.6rem; /* pari a .app-dash-stat-n: nessun salto al load */
  width: 3.5rem;
  border-radius: 4px;
  background: var(--app-card-border, var(--p-content-border-color));
  opacity: 0.5;
  animation: kpi-pulse 1.2s ease-in-out infinite;
}

@keyframes kpi-pulse {
  50% { opacity: 0.2; }
}

@media (prefers-reduced-motion: reduce) {
  .kpi-skeleton { animation: none; }
}
</style>
