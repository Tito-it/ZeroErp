<script setup>
// Scopo: Pannello flussi di una pratica, diviso in "da fare" e "completati".
// Riutilizzabile: riceve flussi via props, emette eventi per azioni.
// Usato nella dashboard (area inferiore) e potenzialmente nel drawer.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { STATO_FLUSSO } from '../../core/constants'
import { statoFlussoSeverity } from '../../core/utils/severity'
import { displayDate } from '../../core/utils/date'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const { t } = useI18n()

const props = defineProps({
  flussi: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  praticaId: { type: Number, default: null },
})

const emit = defineEmits(['open-flusso', 'avvia-flusso', 'completa-flusso'])

// Flussi da fare: DA_ESEGUIRE, IN_CORSO, SOSPESO, ERRORE
const flussiDaFare = computed(() =>
  props.flussi.filter(f => [
    STATO_FLUSSO.DA_ESEGUIRE, STATO_FLUSSO.IN_CORSO,
    STATO_FLUSSO.SOSPESO, STATO_FLUSSO.ERRORE
  ].includes(f.stato_codice_interno))
)

// Flussi completati: COMPLETATO, ANNULLATO
const flussiCompletati = computed(() =>
  props.flussi.filter(f => [
    STATO_FLUSSO.COMPLETATO, STATO_FLUSSO.ANNULLATO
  ].includes(f.stato_codice_interno))
)

function onClickFlusso(flusso) {
  emit('open-flusso', flusso)
}
</script>

<template>
  <div class="flussi-panel">
    <div v-if="!praticaId" class="flussi-panel-empty" />

    <div v-else-if="loading" class="flussi-panel-loading">
      <i class="pi pi-spin pi-spinner" />
    </div>

    <template v-else>
      <div class="flussi-panel-split">
        <!-- Da fare -->
        <div class="flussi-col">
          <div class="flussi-col-header">
            <span>{{ t('pratiche.flussi_da_fare') }}</span>
            <Tag :value="String(flussiDaFare.length)" severity="warn" rounded />
          </div>
          <div v-if="!flussiDaFare.length" class="flussi-col-empty">
            {{ t('pratiche.flussi_nessuno_da_fare') }}
          </div>
          <div
            v-for="f in flussiDaFare" :key="f.id"
            class="flusso-card flusso-card-todo"
            @click="onClickFlusso(f)"
          >
            <div class="flusso-card-header">
              <span class="flusso-card-seq">#{{ f.sequenza }}</span>
              <Tag :value="f.stato_codice_interno" :severity="statoFlussoSeverity(f.stato_codice_interno)" size="small" />
            </div>
            <div class="flusso-card-title">{{ f.template_flusso_codice || t('pratiche.flusso_generico') }}</div>
            <div v-if="f.template_flusso_descrizione" class="flusso-card-desc">{{ f.template_flusso_descrizione }}</div>
            <div v-if="f.data_scadenza" class="flusso-card-meta">
              <i class="pi pi-calendar" /> {{ displayDate(f.data_scadenza) }}
            </div>
          </div>
        </div>

        <!-- Completati -->
        <div class="flussi-col">
          <div class="flussi-col-header">
            <span>{{ t('pratiche.flussi_completati') }}</span>
            <Tag :value="String(flussiCompletati.length)" severity="success" rounded />
          </div>
          <div v-if="!flussiCompletati.length" class="flussi-col-empty">
            {{ t('pratiche.flussi_nessuno_completato') }}
          </div>
          <div
            v-for="f in flussiCompletati" :key="f.id"
            class="flusso-card flusso-card-done"
          >
            <div class="flusso-card-header">
              <span class="flusso-card-seq">#{{ f.sequenza }}</span>
              <Tag :value="f.stato_codice_interno" :severity="statoFlussoSeverity(f.stato_codice_interno)" size="small" />
            </div>
            <div class="flusso-card-title">{{ f.template_flusso_codice || t('pratiche.flusso_generico') }}</div>
            <div v-if="f.esito" class="flusso-card-esito">
              {{ t('pratiche.flusso_esito') }}: <strong>{{ f.esito }}</strong>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.flussi-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.flussi-panel-empty,
.flussi-panel-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

.flussi-panel-split {
  display: flex;
  gap: 1px;
  height: 100%;
  background: var(--surface-border);
}

.flussi-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background: var(--surface-card);
}

.flussi-col-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-color-secondary);
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-50);
  flex-shrink: 0;
}

.flussi-col-empty {
  padding: 1rem;
  text-align: center;
  color: var(--text-color-secondary);
  font-size: 0.8rem;
}

.flusso-card {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--surface-100);
  transition: background 0.15s;
}

.flusso-card-todo { cursor: pointer; }
.flusso-card-todo:hover { background: var(--surface-hover); }
.flusso-card-done { opacity: 0.75; }

.flusso-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.2rem;
}

.flusso-card-seq {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-color-secondary);
}

.flusso-card-title {
  font-size: 0.85rem;
  font-weight: 600;
}

.flusso-card-desc {
  font-size: 0.78rem;
  color: var(--text-color-secondary);
}

.flusso-card-meta {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-top: 0.2rem;
}

.flusso-card-esito {
  font-size: 0.78rem;
  margin-top: 0.2rem;
}

/* Tablet: stack verticale */
@media (max-width: 1024px) {
  .flussi-panel-split { flex-direction: column; }
}
</style>
