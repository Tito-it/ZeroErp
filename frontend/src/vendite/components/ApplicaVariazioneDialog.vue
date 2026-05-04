<script setup>
// Scopo: Dialog per applicare variazione percentuale massa ai prezzi
//        delle righe di una versione BOZZA. Step 1: input + preview (dry_run).
//        Step 2: conferma + applicazione reale.
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { applicaVariazionePercentuale } from '../api/listini'
import { MANAGE_ICONS } from '../../core/constants'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const notify = useNotify()

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
    { successMessage: t('listini.variazione_pct_successo', { count: previewCount.value }) }
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
  <Dialog :visible="visible" @update:visible="onHide" modal
    :header="t('listini.variazione_pct_titolo')" :style="{ width: '700px' }">

    <!-- Step 1: Input -->
    <template v-if="step === 'input'">
      <Message severity="info" :closable="false" class="mb-1">
        {{ t('listini.variazione_pct_help') }}
      </Message>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('listini.variazione_pct_campo') }} *</label>
          <InputNumber v-model="variazionePct" :minFractionDigits="1" :maxFractionDigits="4"
            suffix=" %" :min="-99" :max="1000" show-buttons />
        </div>
        <div class="form-field">
          <label>{{ t('listini.variazione_pct_arrotondamento') }}</label>
          <InputNumber v-model="decimali" :min="0" :max="10" show-buttons />
        </div>
      </div>

      <div class="flex justify-end gap-2 mt-1">
        <Button :label="t('common.cancel')" text @click="onHide" />
        <Button :label="t('listini.variazione_pct_preview')" icon="pi pi-eye"
          :disabled="!canPreview" :loading="loading" @click="loadPreview" />
      </div>
    </template>

    <!-- Step 2: Preview + conferma -->
    <template v-if="step === 'preview'">
      <Message severity="warn" :closable="false" class="mb-1">
        {{ t('listini.variazione_pct_righe_coinvolte', { count: previewCount }) }}
      </Message>

      <DataTable :value="preview" :loading="loading" striped-rows class="app-datatable"
        scrollable scroll-height="300px" data-key="riga_id">
        <Column field="articolo_codice" :header="t('listini.col_articolo')" style="width: 130px;" />
        <Column field="articolo_descrizione" :header="t('catalogo.col_descrizione')" style="min-width: 180px;" />
        <Column field="prezzo_attuale" :header="t('listini.variazione_pct_prezzo_attuale')" style="width: 130px;" />
        <Column field="prezzo_calcolato" :header="t('listini.variazione_pct_prezzo_nuovo')" style="width: 130px;" />
      </DataTable>

      <div class="flex justify-end gap-2 mt-1">
        <Button :label="t('common.back')" text icon="pi pi-arrow-left" @click="backToInput" />
        <Button :label="t('listini.variazione_pct_conferma')" :icon="MANAGE_ICONS.CONFIRM"
          severity="warn" :loading="loading" @click="applyVariazione" />
      </div>
    </template>
  </Dialog>
</template>
