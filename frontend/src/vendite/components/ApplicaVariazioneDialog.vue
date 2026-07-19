<script setup>
// Scopo: Dialog per applicare variazione percentuale massa ai prezzi
//        delle righe di una versione BOZZA. Step 1: input + preview (dry_run).
//        Step 2: conferma + applicazione reale.
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { applicaVariazionePercentuale } from '../api/listini'
import { MANAGE_ICONS } from '../../core/constants'
import AppDialog from '../../core/components/AppDialog.vue'
import InputNumber from 'primevue/inputnumber'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: Boolean,
  listinoId: { type: [Number, null], required: true },
  versioneId: { type: [Number, null], required: true }
})
const emit = defineEmits(['update:visible', 'applied'])

const variazionePct = ref(null)
const decimali = ref(4)
const preview = ref(null)
const previewCount = ref(0)
const step = ref('input')

function resetForm() {
  variazionePct.value = null
  decimali.value = 4
  preview.value = null
  previewCount.value = 0
  step.value = 'input'
}

function onHide() {
  emit('update:visible', false)
  resetForm()
}

const canPreview = computed(() =>
  variazionePct.value != null && variazionePct.value !== 0
)

// Larghezza dialog dipendente dallo step: 'md' per l'input (2 soli campi —
// 'xl' risulterebbe sproporzionato), 'xl' per la preview che mostra la
// tabella righe coinvolte.
const dialogWidth = computed(() => (step.value === 'input' ? 'md' : 'xl'))

async function loadPreview() {
  const res = await execute(
    () => applicaVariazionePercentuale(props.listinoId, props.versioneId, {
      variazione_percentuale: variazionePct.value,
      arrotondamento_decimali: decimali.value,
      dry_run: true
    })
  )
  if (res !== null) {
    preview.value = res.preview || []
    previewCount.value = res.righe_coinvolte || 0
    step.value = 'preview'
  }
}

async function applyVariazione() {
  if (loading.value) return
  const res = await execute(
    () => applicaVariazionePercentuale(props.listinoId, props.versioneId, {
      variazione_percentuale: variazionePct.value,
      arrotondamento_decimali: decimali.value,
      dry_run: false
    }),
    { successMessage: t('vendite.listini.variazione_pct_successo', { count: previewCount.value }) }
  )
  if (res !== null) {
    emit('applied')
    onHide()
  }
}

function backToInput() {
  step.value = 'input'
  preview.value = null
}
</script>

<template>
  <!-- Wizard 2-step (Input -> Preview -> Conferma): i bottoni cambiano per
       step ma vivono nel chrome standard di AppDialog (slot #footer), con
       container .app-form-footer (allineamento a destra + collapse
       responsive) e classe .app-form-footer-btn condivisa col FormFooter:
       nessun CSS duplicato. Non e' il pattern fisso Annulla/Salva, quindi
       lo slot override sostituisce il FormFooter di default. -->
  <AppDialog :visible="visible" @update:visible="onHide"
    :header="t('vendite.listini.variazione_pct_titolo')" :width="dialogWidth">

    <!-- Step 1: Input -->
    <template v-if="step === 'input'">
      <Message severity="info" :closable="false" class="mb-1">
        {{ t('vendite.listini.variazione_pct_help') }}
      </Message>

      <!-- Griglia asimmetrica: la percentuale prende lo spazio, i decimali
           restano stretti (campo 0-10). Gap ampio per separare le celle.
           `min-width: 0` sulle celle: senza, la colonna 1fr non scende sotto
           la larghezza intrinseca dell'InputNumber (show-buttons) e sfora
           spingendo fuori i decimali → scrollbar orizzontale. -->
      <div class="variazione-grid">
        <div class="form-field">
          <label>{{ t('vendite.listini.variazione_pct_campo') }} *</label>
          <InputNumber v-model="variazionePct" :minFractionDigits="1" :maxFractionDigits="4"
            suffix=" %" :min="-99" :max="1000" show-buttons />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.listini.variazione_pct_arrotondamento') }}</label>
          <InputNumber v-model="decimali" :min="0" :max="10" show-buttons />
        </div>
      </div>
    </template>

    <!-- Step 2: Preview + conferma -->
    <template v-if="step === 'preview'">
      <Message severity="warn" :closable="false" class="mb-1">
        {{ t('vendite.listini.variazione_pct_righe_coinvolte', { count: previewCount }) }}
      </Message>

      <DataTable :value="preview" :loading="loading" striped-rows class="app-datatable"
        scrollable scroll-height="300px" data-key="riga_id">
        <Column field="articolo_codice" :header="t('vendite.listini.col_articolo')" style="width: 130px;" />
        <Column field="articolo_descrizione" :header="t('catalogo.col_descrizione')" style="min-width: 180px;" />
        <Column field="prezzo_attuale" :header="t('vendite.listini.variazione_pct_prezzo_attuale')" style="width: 130px;" />
        <Column field="prezzo_calcolato" :header="t('vendite.listini.variazione_pct_prezzo_nuovo')" style="width: 130px;" />
      </DataTable>
    </template>

    <!-- Footer wizard nel chrome standard AppDialog: bottoni per step,
         allineati a destra (.app-form-footer) con stile condiviso FormFooter
         (.app-form-footer-btn). Annulla/Indietro = secondary (.app-escape);
         Conferma = verde standard di conferma (come il Salva del FormFooter). -->
    <template #footer>
      <div v-if="step === 'input'" class="app-form-footer">
        <Button :label="t('common.cancel')" :icon="MANAGE_ICONS.CANCEL"
          severity="secondary" class="app-escape app-form-footer-btn"
          v-tooltip.top="t('common.cancel')" @click="onHide" />
        <Button :label="t('vendite.listini.variazione_pct_preview')" icon="pi pi-eye"
          class="app-form-footer-btn" v-tooltip.top="t('vendite.listini.variazione_pct_preview')"
          :disabled="!canPreview" :loading="loading" @click="loadPreview" />
      </div>
      <div v-else class="app-form-footer">
        <Button :label="t('common.back')" :icon="MANAGE_ICONS.BACK"
          severity="secondary" class="app-escape app-form-footer-btn"
          v-tooltip.top="t('common.back')" @click="backToInput" />
        <Button :label="t('vendite.listini.variazione_pct_conferma')" :icon="MANAGE_ICONS.CONFIRM"
          class="app-form-footer-btn"
          v-tooltip.top="t('vendite.listini.variazione_pct_conferma')"
          :loading="loading" @click="applyVariazione" />
      </div>
    </template>
  </AppDialog>
</template>

<style scoped>
/* Griglia asimmetrica: percentuale elastica, decimali stretti (campo 0-10).
   `min-width: 0` sulle celle + width:100%/min-width:0 sull'InputNumber e sul
   suo input interno: senza, la colonna 1fr non scende sotto la larghezza
   intrinseca dell'InputNumber (show-buttons) e i decimali finiscono fuori dal
   dialog con scrollbar orizzontale. */
.variazione-grid {
  display: grid;
  grid-template-columns: 1fr 130px;
  gap: 1.5rem;
  align-items: end;
}
.variazione-grid .form-field {
  min-width: 0;
}
.variazione-grid :deep(.p-inputnumber) {
  width: 100%;
  min-width: 0;
}
.variazione-grid :deep(.p-inputnumber-input) {
  width: 100%;
  min-width: 0;
}
</style>
