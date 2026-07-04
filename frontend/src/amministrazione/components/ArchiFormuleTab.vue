<script setup>
// Formule-tempo (arco livello edizione) — FE-3.4, anello BE 5. Collega due step
// (da → a) con le soglie tempo. Mirror del vincolo DB (il DB resta l'autorità):
// 0 < giorni_critico < giorni_warning < giorni_esecuzione. tipo_prestazione_id
// è auto-impostato dal BE (non inviato).
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useArchiCollection } from '../composables/useArchiCollection'
import { useStepOptions } from '../composables/useStepOptions'
import CollectionEditorPanel from './CollectionEditorPanel.vue'

const props = defineProps({
  definizioneId: { type: Number, required: true },
  rows: { type: Array, default: () => [] },
  steps: { type: Array, default: () => [] },
})
const emit = defineEmits(['changed'])

const { t } = useI18n()
const readonly = useInjectReadonly()
const { stepOptions, stepCodice } = useStepOptions(() => props.steps)

const coll = useArchiCollection({
  definizioneId: () => props.definizioneId,
  kind: 'formule-tempo',
  messages: {
    created: t('definizioni_workflow.ed_msg_figlio_creato'),
    saved: t('definizioni_workflow.ed_msg_figlio_salvato'),
    deleted: t('definizioni_workflow.ed_msg_figlio_eliminato'),
  },
  confirmDelete: (row) =>
    t('definizioni_workflow.ed_conferma_elimina_figlio', {
      nome: `${stepCodice(row.template_flusso_da_id)} → ${stepCodice(row.template_flusso_a_id)}`,
    }),
  onChanged: () => emit('changed'),
})

const form = reactive({
  template_flusso_da_id: null,
  template_flusso_a_id: null,
  giorni_esecuzione: null,
  giorni_warning: null,
  giorni_critico: null,
  descrizione: '',
  attivo: true,
})
watch(
  [() => coll.formMode.value, () => coll.rowInForm.value?.id],
  () => {
    if (coll.formMode.value === 'create') {
      Object.assign(form, {
        template_flusso_da_id: null,
        template_flusso_a_id: null,
        giorni_esecuzione: null,
        giorni_warning: null,
        giorni_critico: null,
        descrizione: '',
        attivo: true,
      })
    } else if (coll.formMode.value === 'edit') {
      const r = coll.rowInForm.value
      Object.assign(form, {
        template_flusso_da_id: r?.template_flusso_da_id ?? null,
        template_flusso_a_id: r?.template_flusso_a_id ?? null,
        giorni_esecuzione: r?.giorni_esecuzione ?? null,
        giorni_warning: r?.giorni_warning ?? null,
        giorni_critico: r?.giorni_critico ?? null,
        descrizione: r?.descrizione ?? '',
        attivo: r?.attivo ?? true,
      })
    }
  },
)

// Mirror del vincolo DB: tutti > 0 e critico < warning < esecuzione.
const giorniValidi = computed(() => {
  const { giorni_critico: c, giorni_warning: w, giorni_esecuzione: e } = form
  if (c == null || w == null || e == null) return false
  return c > 0 && c < w && w < e
})
// Avviso solo quando i tre valori sono presenti ma l'ordine è errato.
const giorniOrdineErrato = computed(() => {
  const { giorni_critico: c, giorni_warning: w, giorni_esecuzione: e } = form
  return c != null && w != null && e != null && !giorniValidi.value
})
const canSave = computed(
  () => !!form.template_flusso_da_id && !!form.template_flusso_a_id && giorniValidi.value,
)
function onSave() {
  coll.save({
    template_flusso_da_id: form.template_flusso_da_id,
    template_flusso_a_id: form.template_flusso_a_id,
    giorni_esecuzione: form.giorni_esecuzione,
    giorni_warning: form.giorni_warning,
    giorni_critico: form.giorni_critico,
    descrizione: form.descrizione?.trim() || null,
    attivo: form.attivo,
  })
}
</script>

<template>
  <CollectionEditorPanel
    :coll="coll"
    :rows="rows"
    :readonly="readonly"
    :add-label="t('definizioni_workflow.ed_aggiungi')"
    :empty-label="t('definizioni_workflow.ed_formule_tempo_vuoto')"
    :can-save="canSave"
    @save="onSave"
  >
    <template #columns>
      <Column :header="t('definizioni_workflow.ed_col_da')" style="min-width: 150px;">
        <template #body="{ data }">{{ stepCodice(data.template_flusso_da_id) }}</template>
      </Column>
      <Column :header="t('definizioni_workflow.ed_col_a')" style="min-width: 150px;">
        <template #body="{ data }">{{ stepCodice(data.template_flusso_a_id) }}</template>
      </Column>
      <Column field="giorni_esecuzione" :header="t('definizioni_workflow.ed_col_giorni_esecuzione')" style="width: 120px;" />
      <Column field="giorni_warning" :header="t('definizioni_workflow.ed_col_giorni_warning')" style="width: 110px;" />
      <Column field="giorni_critico" :header="t('definizioni_workflow.ed_col_giorni_critico')" style="width: 110px;" />
      <Column :header="t('definizioni_workflow.ed_col_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <ToggleSwitch :model-value="data.attivo" :disabled="readonly" @update:model-value="coll.toggleAttivo(data)" />
        </template>
      </Column>
    </template>
    <template #form>
      <div class="form-field">
        <label>{{ t('definizioni_workflow.ed_col_da') }} *</label>
        <Select v-model="form.template_flusso_da_id" :options="stepOptions" option-label="label" option-value="value" filter :placeholder="t('definizioni_workflow.ed_ph_seleziona')" class="w-full" />
      </div>
      <div class="form-field">
        <label>{{ t('definizioni_workflow.ed_col_a') }} *</label>
        <Select v-model="form.template_flusso_a_id" :options="stepOptions" option-label="label" option-value="value" filter :placeholder="t('definizioni_workflow.ed_ph_seleziona')" class="w-full" />
      </div>
      <div class="form-field form-field--num">
        <label>{{ t('definizioni_workflow.ed_col_giorni_critico') }} *</label>
        <InputNumber v-model="form.giorni_critico" :min="1" show-buttons class="w-full" />
      </div>
      <div class="form-field form-field--num">
        <label>{{ t('definizioni_workflow.ed_col_giorni_warning') }} *</label>
        <InputNumber v-model="form.giorni_warning" :min="1" show-buttons class="w-full" />
      </div>
      <div class="form-field form-field--num">
        <label>{{ t('definizioni_workflow.ed_col_giorni_esecuzione') }} *</label>
        <InputNumber v-model="form.giorni_esecuzione" :min="1" show-buttons class="w-full" />
      </div>
      <div class="form-field form-field--wide">
        <label>{{ t('definizioni_workflow.ed_col_descrizione') }}</label>
        <InputText v-model="form.descrizione" class="w-full" />
      </div>
      <div class="form-field form-field--toggle">
        <label>{{ t('definizioni_workflow.ed_col_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" />
      </div>
      <Message v-if="giorniOrdineErrato" severity="warn" :closable="false" size="small" class="form-field--full">
        {{ t('definizioni_workflow.ed_giorni_ordine') }}
      </Message>
    </template>
  </CollectionEditorPanel>
</template>
