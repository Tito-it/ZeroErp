<script setup>
// Scopo: pannello "Le mie attività" — banner full-width collassabile in cima
// alla dashboard pratiche. Contatori per livello sempre visibili (mappa 1:1 la
// policy reparto-first dell'assegnazione flusso); espanso rende la coda lavoro
// (PraticheCodaLavoro) e ne ri-emette gli eventi.
//
// Presentazionale: riceve items/loading dal caller (lo store carica la coda),
// non fa fetch. L'unica logica propria è la detection operatore per l'empty-state
// e lo stato espanso/collassato. Riusabile (home/calendario futuri).
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import { useAuthStore } from '../../stores/auth'
import { MANAGE_ICONS } from '../../core/constants'
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

// Default collassato: non ruba spazio alla lista, l'operatore espande quando
// vuole lavorare la coda (brief §9).
const expanded = ref(false)

// Solo l'operatore con emittente 1-a-1 ha una coda lavoro. Admin globale /
// portali / shop → empty-state, nessun contenuto (il fetch è già guardato nello
// store via emittenteCorrente).
const isOperatore = computed(() => !!auth.emittenteCorrente?.id)

// Contatori per livello dalla config condivisa (ordine + severity coerenti con
// le sezioni espanse di PraticheCodaLavoro).
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
  if (!isOperatore.value) return
  expanded.value = !expanded.value
}
</script>

<template>
  <section class="mie-attivita">
    <header
      class="mie-attivita-bar"
      :class="{ 'is-clickable': isOperatore }"
      @click="toggle"
    >
      <div class="mie-attivita-title">
        <i class="pi pi-briefcase" />
        <span>{{ t('pratiche.mie_attivita_titolo') }}</span>
      </div>

      <!-- Contatori per livello (sempre visibili anche da collassato) -->
      <div v-if="isOperatore && totale" class="mie-attivita-counters">
        <span v-for="c in contatori" :key="c.key" class="mie-attivita-counter">
          <Badge :value="c.count" :severity="c.severity" />
          <span class="mie-attivita-counter-label">{{ c.label }}</span>
        </span>
      </div>
      <span v-else-if="isOperatore && loading" class="mie-attivita-empty">
        <i class="pi pi-spin pi-spinner" />
      </span>
      <span v-else class="mie-attivita-empty">{{ t('pratiche.mie_attivita_vuoto') }}</span>

      <Button
        v-if="isOperatore"
        :icon="expanded ? MANAGE_ICONS.COLLAPSE : MANAGE_ICONS.EXPAND"
        :aria-label="t(expanded ? 'pratiche.mie_attivita_comprimi' : 'pratiche.mie_attivita_espandi')"
        text
        rounded
        size="small"
        class="mie-attivita-toggle"
        @click.stop="toggle"
      />
    </header>

    <div v-if="isOperatore && expanded" class="mie-attivita-body">
      <PraticheCodaLavoro
        :items="items"
        :loading="loading"
        :selected-flusso-id="selectedFlussoId"
        @select-flusso="emit('select-flusso', $event)"
        @prendi-in-carico="emit('prendi-in-carico', $event)"
      />
    </div>
  </section>
</template>

<style scoped>
.mie-attivita {
  display: flex;
  flex-direction: column;
  flex: 0 0 auto;
  background: var(--surface-card);
  border-bottom: 2px solid var(--p-info-color, var(--p-primary-color));
  overflow: hidden;
}

/* Barra collassata: titolo a sinistra, contatori al centro, toggle a destra */
.mie-attivita-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0.75rem;
  background: var(--surface-ground);
  flex-wrap: wrap;
}

.mie-attivita-bar.is-clickable {
  cursor: pointer;
}

.mie-attivita-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--p-info-color, var(--p-primary-color));
}

.mie-attivita-counters {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  flex: 1 1 auto;
}

.mie-attivita-counter {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.78rem;
  color: var(--text-color-secondary);
}

.mie-attivita-empty {
  flex: 1 1 auto;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.mie-attivita-toggle {
  margin-left: auto;
  flex: 0 0 auto;
}

/* Corpo espanso: la coda scrolla internamente, altezza limitata per non
   spingere la lista pratiche sotto il fold. */
.mie-attivita-body {
  max-height: 340px;
  overflow-y: auto;
  border-top: 1px solid var(--surface-border);
}
</style>
