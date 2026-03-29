<script setup>
// Scopo: Sidebar coda lavoro operatore su tre livelli (ASSEGNATO, COMPETENZA, REPARTO).
// Riutilizzabile: riceve items e emit eventi, non gestisce dati direttamente.
// Layout: desktop = sidebar verticale, tablet = toggle con badge contatore.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { statoFlussoSeverity, prioritaPraticaSeverity } from '../../core/utils/severity'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Button from 'primevue/button'

const { t } = useI18n()

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  selectedFlussoId: { type: Number, default: null },
})

const emit = defineEmits(['select-flusso', 'prendi-in-carico'])

// Raggruppamento per livello con configurazione label/severity
const sezioni = computed(() => [
  { key: 'ASSEGNATO', label: t('pratiche.coda_assegnati'), severity: 'danger',
    items: props.items.filter(i => i.livello === 'ASSEGNATO') },
  { key: 'COMPETENZA', label: t('pratiche.coda_competenza'), severity: 'warn',
    items: props.items.filter(i => i.livello === 'COMPETENZA') },
  { key: 'REPARTO', label: t('pratiche.coda_reparto'), severity: 'secondary',
    items: props.items.filter(i => i.livello === 'REPARTO') },
].filter(s => s.items.length > 0))

function onItemClick(item) {
  emit('select-flusso', item)
}

function onPrendiInCarico(item, event) {
  event.stopPropagation()
  emit('prendi-in-carico', item)
}
</script>

<template>
  <div class="coda-lavoro">
    <div class="coda-lavoro-header">
      <span class="coda-lavoro-title">{{ t('pratiche.coda_lavoro') }}</span>
      <Badge v-if="items.length" :value="items.length" severity="info" />
    </div>

    <div v-if="loading" class="coda-lavoro-loading">
      <i class="pi pi-spin pi-spinner" />
    </div>

    <div v-else-if="!items.length" class="coda-lavoro-empty">
      {{ t('pratiche.coda_vuota') }}
    </div>

    <template v-else>
      <div v-for="sezione in sezioni" :key="sezione.key" class="coda-section">
        <div class="coda-section-header">
          <span>{{ sezione.label }}</span>
          <Badge :value="sezione.items.length" :severity="sezione.severity" />
        </div>
        <div
          v-for="item in sezione.items" :key="item.flusso_id"
          class="coda-item"
          :class="{ 'coda-item-selected': item.flusso_id === selectedFlussoId }"
          @click="onItemClick(item)"
        >
          <div class="coda-item-title">{{ item.pratica_codice }}</div>
          <div class="coda-item-desc">{{ item.template_flusso_codice || item.template_flusso_desc }}</div>
          <div class="coda-item-meta">
            <Tag :value="item.stato_flusso_codice" :severity="statoFlussoSeverity(item.stato_flusso_codice)" size="small" />
            <!-- Azione specifica per livello -->
            <Tag v-if="item.livello === 'ASSEGNATO'" :value="item.priorita_codice" :severity="prioritaPraticaSeverity(item.priorita_codice)" size="small" />
            <Button
              v-else-if="item.livello === 'COMPETENZA'"
              :label="t('pratiche.prendi_in_carico')"
              icon="pi pi-user-plus" size="small" text
              @click="onPrendiInCarico(item, $event)"
            />
            <span v-else-if="item.risorsa_assegnata" class="coda-item-risorsa">{{ item.risorsa_assegnata }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.coda-lavoro {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  border-right: 1px solid var(--surface-border);
  background: var(--surface-card);
}

/* Header: titolo verde con sottolineatura corta sotto il testo */
.coda-lavoro-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem 0.4rem;
  background: var(--surface-ground);
  border-bottom: 1px solid var(--surface-border);
}

.coda-lavoro-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--p-info-color, var(--p-primary-color));
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding-bottom: 0.2rem;
  border-bottom: 2px solid var(--p-info-color, var(--p-primary-color));
}

.coda-lavoro-loading,
.coda-lavoro-empty {
  padding: 1rem;
  text-align: center;
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

/* Sezioni: separatore verde sottile tra gruppi */
.coda-section {
  padding: 0;
  border-bottom: 2px solid var(--p-info-color, var(--p-primary-color));
}

.coda-section:last-child { border-bottom: none; }

.coda-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.4rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-border);
}

.coda-item {
  padding: 0.4rem 0.75rem;
  cursor: pointer;
  border-bottom: 1px solid var(--surface-100);
  transition: background 0.15s;
}

.coda-item:hover { background: var(--surface-hover); }
.coda-item-selected { background: var(--highlight-bg); }

.coda-item-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-color);
}

.coda-item-desc {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-top: 0.1rem;
}

.coda-item-meta {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin-top: 0.25rem;
  flex-wrap: wrap;
}

.coda-item-risorsa {
  font-size: 0.72rem;
  color: var(--text-color-secondary);
  font-style: italic;
}
</style>
