<script setup>
// Sotto-lista HANDLER-EVENTI di uno step (FE-3.3). Binding handler server-side
// per evento (IN_CORSO/COMPLETATO), esito-aware. Scaffold nello shell.
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { STEP_HANDLER_EVENTO, ESITO_RICHIESTO } from '../../core/constants'
import { useStepFigliCollection } from '../composables/useStepFigliCollection'
import CollectionEditorPanel from './CollectionEditorPanel.vue'

const props = defineProps({
  // Campi che il BACKEND indica come da correggere (envelope `error.fields`).
  // Arrivano dal padre: questo componente non chiama le API da solo.
  campiErrati: { type: Array, default: () => [] },
  definizioneId: { type: Number, required: true },
  stepId: { type: Number, required: true },
  rows: { type: Array, default: () => [] },
})
const emit = defineEmits(['changed'])

const { t } = useI18n()
const readonly = useInjectReadonly()

const coll = useStepFigliCollection({
  definizioneId: () => props.definizioneId,
  stepId: () => props.stepId,
  kind: 'handler-eventi',
  messages: {
    created: t('amministrazione.definizioni_workflow.ed_msg_figlio_creato'),
    saved: t('amministrazione.definizioni_workflow.ed_msg_figlio_salvato'),
    deleted: t('amministrazione.definizioni_workflow.ed_msg_figlio_eliminato'),
  },
  confirmDelete: (row) =>
    t('amministrazione.definizioni_workflow.ed_conferma_elimina_figlio', { nome: row.handler_key || row.evento }),
  onChanged: () => emit('changed'),
})

const eventoOptions = computed(() =>
  STEP_HANDLER_EVENTO.map((v) => ({ value: v, label: t(`amministrazione.definizioni_workflow.ed_evento_${v}`) })),
)
const esitoOptions = computed(() =>
  ESITO_RICHIESTO.map((v) => ({ value: v, label: t(`amministrazione.definizioni_workflow.ed_esito_${v}`) })),
)
function esitoLabel(v) {
  return v ? t(`amministrazione.definizioni_workflow.ed_esito_${v}`) : t('amministrazione.definizioni_workflow.ed_prereq_qualsiasi_esito')
}

const form = reactive({ evento: 'COMPLETATO', esito_richiesto: null, handler_id: null, sequenza: 0, attivo: true })
watch(
  [() => coll.formMode.value, () => coll.rowInForm.value?.id],
  () => {
    if (coll.formMode.value === 'create') {
      Object.assign(form, { evento: 'COMPLETATO', esito_richiesto: null, handler_id: null, sequenza: 0, attivo: true })
    } else if (coll.formMode.value === 'edit') {
      const r = coll.rowInForm.value
      Object.assign(form, {
        evento: r?.evento ?? 'COMPLETATO',
        esito_richiesto: r?.esito_richiesto ?? null,
        handler_id: r?.handler_id ?? null,
        sequenza: r?.sequenza ?? 0,
        attivo: r?.attivo ?? true,
      })
    }
  },
)
const canSave = computed(() => !!form.evento && !!form.handler_id)
function onSave() {
  coll.save({
    evento: form.evento,
    esito_richiesto: form.esito_richiesto || null,
    handler_id: form.handler_id,
    sequenza: form.sequenza ?? 0,
    attivo: form.attivo,
  })
}
</script>

<template>
  <CollectionEditorPanel
    :coll="coll"
    :rows="rows"
    :readonly="readonly"
    :add-label="t('amministrazione.definizioni_workflow.ed_aggiungi')"
    :empty-label="t('amministrazione.definizioni_workflow.ed_handler_eventi_vuoto')"
    :can-save="canSave"
    @save="onSave"
  >
    <template #columns>
      <Column :header="t('amministrazione.definizioni_workflow.ed_col_evento')" style="width: 140px;">
        <template #body="{ data }">{{ t(`amministrazione.definizioni_workflow.ed_evento_${data.evento}`) }}</template>
      </Column>
      <Column field="handler_key" :header="t('amministrazione.definizioni_workflow.ed_col_handler')" style="min-width: 180px;" />
      <Column :header="t('amministrazione.definizioni_workflow.ed_col_esito_richiesto')" style="width: 150px;">
        <template #body="{ data }">{{ esitoLabel(data.esito_richiesto) }}</template>
      </Column>
      <Column field="sequenza" :header="t('amministrazione.definizioni_workflow.ed_col_sequenza')" style="width: 80px;" />
      <Column :header="t('amministrazione.definizioni_workflow.ed_col_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <ToggleSwitch :model-value="data.attivo" :disabled="readonly" @update:model-value="coll.toggleAttivo(data)" />
        </template>
      </Column>
    </template>
    <template #form>
      <div class="form-field">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_evento') }} *</label>
        <Select v-model="form.evento" :options="eventoOptions" option-label="label" option-value="value" class="w-full" />
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_handler') }} *</label>
        <LookupSelect v-model="form.handler_id" rel="pratiche.handler_flussi" :placeholder="t('amministrazione.definizioni_workflow.ed_ph_seleziona')" show-code />
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_esito_richiesto') }}</label>
        <Select v-model="form.esito_richiesto" :options="esitoOptions" option-label="label" option-value="value" show-clear :placeholder="t('amministrazione.definizioni_workflow.ed_prereq_qualsiasi_esito')" class="w-full" />
      </div>
      <div class="form-field form-field--num">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_sequenza') }}</label>
        <InputNumber v-model="form.sequenza" :min="0" show-buttons class="w-full" />
      </div>
      <div class="form-field form-field--toggle">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo"
        :invalid="campiErrati.includes('attivo')" />
      </div>
    </template>
  </CollectionEditorPanel>
</template>
