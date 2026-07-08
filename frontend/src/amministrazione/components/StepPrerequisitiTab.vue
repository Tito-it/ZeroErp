<script setup>
// Prerequisiti (arco entrante) dello step selezionato — FE-3.4, anello BE 5.
// «questo step richiede [step] con esito [esito]». template_flusso_id è fisso =
// stepId; prerequisito_id sceglie un altro step. Insert-only: niente attivo.
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import Select from 'primevue/select'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { ESITO_RICHIESTO } from '../../core/constants'
import { useArchiCollection } from '../composables/useArchiCollection'
import { useStepOptions } from '../composables/useStepOptions'
import CollectionEditorPanel from './CollectionEditorPanel.vue'

const props = defineProps({
  definizioneId: { type: Number, required: true },
  stepId: { type: Number, required: true },
  rows: { type: Array, default: () => [] },
  steps: { type: Array, default: () => [] },
})
const emit = defineEmits(['changed'])

const { t } = useI18n()
const readonly = useInjectReadonly()
const { stepCodice } = useStepOptions(() => props.steps)

const coll = useArchiCollection({
  definizioneId: () => props.definizioneId,
  kind: 'prerequisiti',
  messages: {
    created: t('definizioni_workflow.ed_msg_figlio_creato'),
    saved: t('definizioni_workflow.ed_msg_figlio_salvato'),
    deleted: t('definizioni_workflow.ed_msg_figlio_eliminato'),
  },
  confirmDelete: (row) =>
    t('definizioni_workflow.ed_conferma_elimina_figlio', { nome: stepCodice(row.prerequisito_id) }),
  onChanged: () => emit('changed'),
})

// Opzioni prerequisito: step dell'edizione, escluso lo step corrente
// (auto-prerequisito = ciclo banale → escluso per feedback immediato).
const prereqOptions = computed(() =>
  props.steps.filter((s) => s.id !== props.stepId).map((s) => ({ value: s.id, label: s.codice })),
)
const esitoOptions = computed(() =>
  ESITO_RICHIESTO.map((v) => ({ value: v, label: t(`definizioni_workflow.ed_esito_${v}`) })),
)
function esitoLabel(v) {
  return v ? t(`definizioni_workflow.ed_esito_${v}`) : t('definizioni_workflow.ed_prereq_qualsiasi_esito')
}

const form = reactive({ prerequisito_id: null, esito_richiesto: null })
watch(
  [() => coll.formMode.value, () => coll.rowInForm.value?.id],
  () => {
    if (coll.formMode.value === 'create') {
      form.prerequisito_id = null
      form.esito_richiesto = null
    } else if (coll.formMode.value === 'edit') {
      form.prerequisito_id = coll.rowInForm.value?.prerequisito_id ?? null
      form.esito_richiesto = coll.rowInForm.value?.esito_richiesto ?? null
    }
  },
)
const canSave = computed(() => !!form.prerequisito_id)
function onSave() {
  coll.save({
    template_flusso_id: props.stepId,
    prerequisito_id: form.prerequisito_id,
    esito_richiesto: form.esito_richiesto || null,
  })
}
</script>

<template>
  <CollectionEditorPanel
    :coll="coll"
    :rows="rows"
    :readonly="readonly"
    :add-label="t('definizioni_workflow.ed_aggiungi')"
    :empty-label="t('definizioni_workflow.ed_prerequisiti_vuoto')"
    :can-save="canSave"
    @save="onSave"
  >
    <template #columns>
      <Column :header="t('definizioni_workflow.ed_col_prerequisito')" style="min-width: 180px;">
        <template #body="{ data }">{{ stepCodice(data.prerequisito_id) }}</template>
      </Column>
      <Column :header="t('definizioni_workflow.ed_col_esito_richiesto')" style="min-width: 150px;">
        <template #body="{ data }">{{ esitoLabel(data.esito_richiesto) }}</template>
      </Column>
    </template>
    <template #form>
      <div class="form-field">
        <label>{{ t('definizioni_workflow.ed_col_prerequisito') }} *</label>
        <Select v-model="form.prerequisito_id" :options="prereqOptions" option-label="label" option-value="value" filter :placeholder="t('definizioni_workflow.ed_ph_seleziona')" class="w-full" />
      </div>
      <div class="form-field">
        <label>{{ t('definizioni_workflow.ed_col_esito_richiesto') }}</label>
        <Select v-model="form.esito_richiesto" :options="esitoOptions" option-label="label" option-value="value" show-clear :placeholder="t('definizioni_workflow.ed_prereq_qualsiasi_esito')" class="w-full" />
      </div>
    </template>
  </CollectionEditorPanel>
</template>
