<script setup>
// Scopo: Roadmap del percorso pratica = template_flussi del tipo_prestazione in
// ordine, ciascuno con lo stato di istanziazione. I flussi NON sono materializzati
// alla creazione (percorsi condizionali): la roadmap mostra il percorso suggerito
// e permette di creare/eseguire lo step (template-bound) o aprire quello esistente.
// Le regole di prerequisito (esito-aware) sono a DB: cliccare uno step non ancora
// abilitato → errore parlante (gestito dal parent via toast).
import { useI18n } from 'vue-i18n'
import { statoFlussoSeverity } from '../../core/utils/severity'
import { STATO_FLUSSO } from '../../core/constants'
import Tag from 'primevue/tag'

const { t } = useI18n()

const props = defineProps({
  percorso: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  praticaId: { type: Number, default: null },
  // Azione in corso (create/open): blocca i click per evitare doppia creazione.
  busy: { type: Boolean, default: false },
})

const emit = defineEmits(['open-flusso', 'create-flusso'])

function statoLabel(step) {
  return step.flusso_id ? step.stato_codice_interno : t('pratiche.percorso_da_creare')
}
function statoSev(step) {
  return step.flusso_id ? statoFlussoSeverity(step.stato_codice_interno) : 'secondary'
}
function onClick(step) {
  if (props.busy) return
  if (step.flusso_id) emit('open-flusso', step.flusso_id)
  else emit('create-flusso', step.template_flusso_id)
}
</script>

<template>
  <div class="percorso-panel">
    <div v-if="!praticaId" class="percorso-empty" />

    <div v-else-if="loading" class="percorso-loading">
      <i class="pi pi-spin pi-spinner" />
    </div>

    <template v-else>
      <div class="percorso-header">{{ t('pratiche.percorso_titolo') }}</div>
      <div class="percorso-steps">
        <template v-for="(step, i) in percorso" :key="step.template_flusso_id">
          <div
            class="percorso-step"
            :class="{
              'percorso-step-done': step.stato_codice_interno === STATO_FLUSSO.COMPLETATO,
              'percorso-step-todo': !step.flusso_id,
              'percorso-step-busy': busy,
            }"
            @click="onClick(step)"
          >
            <div class="percorso-step-top">
              <span class="percorso-step-seq">#{{ step.sequenza }}</span>
              <Tag :value="statoLabel(step)" :severity="statoSev(step)" size="small" />
            </div>
            <div class="percorso-step-title">
              {{ step.template_flusso_codice }}
              <i
                v-if="step.has_handler"
                class="pi pi-bolt percorso-handler"
                :title="t('pratiche.percorso_handler')"
              />
            </div>
            <div v-if="step.esito" class="percorso-step-esito">
              {{ t('pratiche.flusso_esito') }}: <strong>{{ step.esito }}</strong>
            </div>
            <div class="percorso-step-action">
              <i :class="step.flusso_id ? 'pi pi-folder-open' : 'pi pi-plus-circle'" />
              {{ step.flusso_id ? t('pratiche.percorso_apri') : t('pratiche.percorso_crea') }}
            </div>
          </div>
          <i v-if="i < percorso.length - 1" class="pi pi-angle-right percorso-arrow" />
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
.percorso-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--surface-card);
}

.percorso-empty,
.percorso-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

.percorso-header {
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

.percorso-steps {
  display: flex;
  align-items: stretch;
  gap: 0.25rem;
  padding: 0.6rem 0.75rem;
  overflow-x: auto;
  flex: 1;
}

.percorso-step {
  flex: 0 0 auto;
  min-width: 150px;
  max-width: 200px;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.5rem 0.6rem;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface-0);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.percorso-step:hover {
  background: var(--surface-hover);
  border-color: var(--p-primary-color);
}

.percorso-step-done { opacity: 0.8; }
.percorso-step-todo { border-style: dashed; }
.percorso-step-busy { pointer-events: none; opacity: 0.6; }

.percorso-step-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.percorso-step-seq {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-color-secondary);
}

.percorso-step-title {
  font-size: 0.82rem;
  font-weight: 600;
  line-height: 1.2;
}

.percorso-handler {
  font-size: 0.75rem;
  color: var(--p-warn-color, #f59e0b);
  margin-left: 0.2rem;
}

.percorso-step-esito {
  font-size: 0.74rem;
  color: var(--text-color-secondary);
}

.percorso-step-action {
  margin-top: auto;
  font-size: 0.74rem;
  color: var(--p-primary-color);
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.percorso-arrow {
  align-self: center;
  color: var(--text-color-secondary);
  font-size: 1rem;
  flex-shrink: 0;
}
</style>
