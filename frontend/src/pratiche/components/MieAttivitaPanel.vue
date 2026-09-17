<script setup>
// Scopo: "Le mie attività" — rail verticale collassabile a sinistra della
// dashboard pratiche. Contiene la coda lavoro operatore (PraticheCodaLavoro,
// inbox cross-pratica su tre livelli). Sta a lato della lista: espandendosi NON
// spinge più la lista (era un banner full-width in cima).
//
//   collassato → striscia stretta con i contatori per livello (badge)
//   espanso    → rail largo con la coda lavoro scrollabile
//
// Presentazionale: riceve items/loading dal caller (lo store carica la coda),
// non fa fetch. Logica propria: detection operatore (empty-state) e stato
// espanso/collassato. Gate: solo l'operatore con emittente 1-a-1 ha una coda.
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Badge from 'primevue/badge'
import { useAuthStore } from '../../stores/auth'
import { CODA_LAVORO_LIVELLI } from '../codaLavoroLivelli'
import PraticheCodaLavoro from './PraticheCodaLavoro.vue'

const { t } = useI18n()
const auth = useAuthStore()

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  selectedFlussoId: { type: Number, default: null },
})

const emit = defineEmits(['select-flusso', 'prendi-in-carico'])

// Default collassato: non ruba larghezza alla lista; l'operatore espande quando
// vuole lavorare la coda.
const expanded = ref(false)

// Solo l'operatore con emittente 1-a-1 ha una coda lavoro. Admin globale /
// portali / shop → nessun rail (il fetch è già guardato nello store).
const isOperatore = computed(() => !!auth.emittenteCorrente?.id)

// Contatori per livello dalla config condivisa (ordine + severity coerenti con
// le sezioni di PraticheCodaLavoro).
const contatori = computed(() =>
  CODA_LAVORO_LIVELLI
    .map(l => ({
      key: l.key,
      label: t(l.labelKey),
      severity: l.severity,
      count: props.items.filter(i => i.livello === l.key).length,
    }))
    .filter(l => l.count > 0),
)

const totale = computed(() => props.items.length)

function toggle() {
  expanded.value = !expanded.value
}
</script>

<template>
  <aside
    v-if="isOperatore"
    class="mie-attivita-rail"
    :class="{ 'is-collapsed': !expanded }"
  >
    <!-- Testata rail: titolo (solo espanso) + toggle collassa/espandi -->
    <header class="rail-head">
      <span v-if="expanded" class="rail-title">
        <i class="pi pi-briefcase" />
        <span>{{ t('pratiche.mie_attivita_titolo') }}</span>
      </span>
      <!-- Toggle orizzontale: angle-left/right (direzione del rail), non la
           coppia MANAGE_ICONS.EXPAND/COLLAPSE che e' verticale (apri/chiudi). -->
      <button
        type="button"
        class="app-collapse-toggle"
        :aria-label="t(expanded ? 'pratiche.mie_attivita_comprimi' : 'pratiche.mie_attivita_espandi')"
        :aria-expanded="expanded"
        @click="toggle"
      >
        <i :class="expanded ? 'pi pi-angle-left' : 'pi pi-angle-right'" />
      </button>
    </header>

    <!-- Collassato: contatori per livello, verticali. Click → espande. -->
    <div v-if="!expanded" class="rail-counters" @click="toggle">
      <i class="pi pi-briefcase rail-counters-icon" :title="t('pratiche.mie_attivita_titolo')" />
      <template v-if="totale">
        <span v-for="c in contatori" :key="c.key" class="rail-counter" :title="c.label">
          <Badge :value="c.count" :severity="c.severity" />
        </span>
      </template>
      <i
        v-else-if="loading"
        class="pi pi-spin pi-spinner rail-counters-empty"
      />
      <i
        v-else
        class="pi pi-inbox rail-counters-empty"
        :title="t('pratiche.mie_attivita_vuoto')"
      />
    </div>

    <!-- Espanso: coda lavoro scrollabile -->
    <div v-else class="rail-body">
      <PraticheCodaLavoro
        :items="items"
        :loading="loading"
        :selected-flusso-id="selectedFlussoId"
        @select-flusso="emit('select-flusso', $event)"
        @prendi-in-carico="emit('prendi-in-carico', $event)"
      />
    </div>
  </aside>
</template>

<style scoped>
.mie-attivita-rail {
  display: flex;
  flex-direction: column;
  flex: 0 0 auto;
  width: 270px;
  height: 100%;
  background: var(--surface-card);
  border-right: 2px solid var(--p-info-color, var(--p-primary-color));
  overflow: hidden;
  transition: width var(--app-transition-normal, 0.2s);
}

.mie-attivita-rail.is-collapsed {
  width: 46px;
}

.rail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  padding: 0.4rem 0.5rem;
  background: var(--surface-ground);
  border-bottom: 1px solid var(--surface-border);
  flex: 0 0 auto;
}

.is-collapsed .rail-head {
  justify-content: center;
}

.rail-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--p-info-color, var(--p-primary-color));
  white-space: nowrap;
  overflow: hidden;
}

/* Toggle collassa/espandi: classe condivisa .app-collapse-toggle (main.css). */

/* Collassato: colonna di contatori, cliccabile per espandere */
.rail-counters {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0;
  cursor: pointer;
  flex: 1;
}

.rail-counters-icon {
  color: var(--p-info-color, var(--p-primary-color));
  font-size: 1rem;
}

.rail-counter {
  display: flex;
}

.rail-counters-empty {
  color: var(--app-text-muted);
  font-size: 0.9rem;
}

/* Espanso: la coda scrolla internamente */
.rail-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
}
.rail-body > :deep(*) {
  flex: 1;
  min-height: 0;
}

/* Tablet/mobile: il rail diventa una fascia full-width in cima (la dashboard
   impila e scrolla per intero). */
@media (max-width: 1279px) {
  .mie-attivita-rail,
  .mie-attivita-rail.is-collapsed {
    width: 100%;
    height: auto;
    border-right: none;
    border-bottom: 2px solid var(--p-info-color, var(--p-primary-color));
  }
  .rail-counters {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: flex-start;
    padding: 0.5rem 0.75rem;
  }
  .rail-body {
    max-height: 300px;
  }
}
</style>
