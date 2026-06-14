<script setup>
// Scopo: Roadmap del percorso pratica = template_flussi del tipo_prestazione in
// ordine, ciascuno con lo stato di istanziazione. I flussi NON sono materializzati
// alla creazione (percorsi condizionali): la roadmap mostra il percorso suggerito
// e permette di creare/eseguire lo step (template-bound) o aprire quello esistente.
// Le regole di prerequisito (esito-aware) sono a DB: cliccare uno step non ancora
// abilitato → errore parlante (gestito dal parent via toast).
import { useI18n } from 'vue-i18n'
import { statoFlussoSeverity } from '../../core/utils/severity'
import { RAMO_STEP, STATO_FLUSSO } from '../../core/constants'
import Tag from 'primevue/tag'

const { t } = useI18n()

const props = defineProps({
  percorso: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  praticaId: { type: Number, default: null },
  // Azione in corso (create/open): blocca i click per evitare doppia creazione.
  busy: { type: Boolean, default: false },
  // Pratica in stato terminale (CHIUSA/ANNULLATA): sola lettura. Gli step "da
  // creare" non sono cliccabili (niente nuovi flussi), i flussi esistenti
  // restano apribili ma il drawer li mostra in sola lettura.
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['open-flusso', 'create-flusso'])

function statoLabel(step) {
  return step.flusso_id ? step.stato_codice_interno : t('pratiche.percorso_da_creare')
}
function statoSev(step) {
  return step.flusso_id ? statoFlussoSeverity(step.stato_codice_interno) : 'secondary'
}
// Ramo morto (workflow v2 D4): il bivio ha preso l'altra strada. Solo resa
// visiva: il click resta possibile (il guard prerequisiti a DB risponde con
// errore parlante — nessuna regola duplicata lato FE).
function isRamoChiuso(step) {
  return step.ramo === RAMO_STEP.RAMO_CHIUSO
}
// Ripeti (workflow v2 D3): un'istanza esiste gia' E una nuova e' creabile
// ORA. La decisione e' interamente del DB (fn_check_ripetibilita_flusso:
// regola template + stato/esito dell'ultima istanza) — nessuna condizione
// sullo stato qui, coprirebbe male i casi ANNULLATO/ERRORE che il flag
// gia' considera.
function canRipeti(step) {
  // Pratica terminale: niente ripetizione (creerebbe un nuovo flusso).
  return !props.readonly && Boolean(step.flusso_id) && step.ripetibile_adesso === true
}
// Step "da creare" non cliccabile su pratica terminale: nessun nuovo flusso.
function isStepCliccabile(step) {
  return Boolean(step.flusso_id) || !props.readonly
}
function onClick(step) {
  if (props.busy) return
  if (step.flusso_id) { emit('open-flusso', step.flusso_id); return }
  if (props.readonly) return
  emit('create-flusso', step.template_flusso_id)
}
function onRipeti(step) {
  if (props.busy) return
  emit('create-flusso', step.template_flusso_id)
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
              'percorso-step-ramo-chiuso': isRamoChiuso(step),
              'percorso-step-disabled': !isStepCliccabile(step),
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
            <div v-if="isRamoChiuso(step)" class="percorso-step-action percorso-ramo-chiuso">
              <i class="pi pi-ban" :title="t('pratiche.percorso_ramo_chiuso_hint')" />
              {{ t('pratiche.percorso_ramo_chiuso') }}
            </div>
            <div v-else-if="!isStepCliccabile(step)" class="percorso-step-action">
              <i class="pi pi-lock" :title="t('pratiche.percorso_non_disponibile')" />
              {{ t('pratiche.percorso_non_disponibile') }}
            </div>
            <div v-else class="percorso-step-action">
              <i :class="step.flusso_id ? 'pi pi-folder-open' : 'pi pi-plus-circle'" />
              {{ step.flusso_id ? t('pratiche.percorso_apri') : t('pratiche.percorso_crea') }}
              <span
                v-if="canRipeti(step)"
                class="percorso-ripeti"
                :title="t('pratiche.percorso_ripeti_hint')"
                @click.stop="onRipeti(step)"
              >
                <i class="pi pi-replay" /> {{ t('pratiche.percorso_ripeti') }}
              </span>
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
/* Step "da creare" su pratica terminale: non cliccabile (niente nuovi flussi). */
.percorso-step-disabled { cursor: not-allowed; opacity: 0.5; }
.percorso-step-disabled:hover { background: var(--surface-0); border-color: var(--surface-border); }
/* Ramo morto (D4): attenuato e tratteggiato fitto — visivamente "fuori
   strada", ma resta cliccabile (guard parlante a DB). */
.percorso-step-ramo-chiuso { opacity: 0.5; border-style: dotted; }

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

.percorso-ramo-chiuso { color: var(--text-color-secondary); }

.percorso-ripeti {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-weight: 600;
}

.percorso-ripeti:hover { text-decoration: underline; }

.percorso-arrow {
  align-self: center;
  color: var(--text-color-secondary);
  font-size: 1rem;
  flex-shrink: 0;
}
</style>
