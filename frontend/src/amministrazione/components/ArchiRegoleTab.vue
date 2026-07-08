<script setup>
// Regole-generazione (arco livello edizione) — FE-3.4, anello BE 5. Alla
// transizione di uno step origine a COMPLETATO, genera/propone una pratica di un
// tipo destinazione (eventualmente su uno step dest). Il dest può essere
// cross-edizione: il tipo è obbligatorio, lo step dest è opzionale e scelto fra
// gli step dell'edizione corrente (il targeting cross-edizione per step non è
// esposto in questa UI — un valore esistente si preserva se non lo si tocca).
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useLookup } from '../../core/composables/useLookup'
import { lookupCodici } from '../../core/apiCore'
import { ESITO_REGOLA } from '../../core/constants'
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
  kind: 'regole-generazione',
  messages: {
    created: t('definizioni_workflow.ed_msg_figlio_creato'),
    saved: t('definizioni_workflow.ed_msg_figlio_salvato'),
    deleted: t('definizioni_workflow.ed_msg_figlio_eliminato'),
  },
  confirmDelete: (row) =>
    t('definizioni_workflow.ed_conferma_elimina_figlio', {
      nome: `${stepCodice(row.template_flusso_origine_id)} → ${tipoLabel(row.tipo_prestazione_dest_id)}`,
    }),
  onChanged: () => emit('changed'),
})

// Catalogo tipi prestazione per il display del tipo destinazione in colonna
// (nel form lo seleziona LookupSelect, che condivide il fetch via cache).
const tipi = useLookup(() => lookupCodici('pratiche.tipi_prestazione'), { immediate: true })
const tipoMap = computed(() => new Map(tipi.items.value.map((tp) => [tp.id, tp.descrizione])))
function tipoLabel(id) {
  return tipoMap.value.get(id) ?? (id != null ? `#${id}` : '—')
}

const esitoOptions = computed(() =>
  ESITO_REGOLA.map((v) => ({ value: v, label: t(`definizioni_workflow.ed_esito_regola_${v}`) })),
)
function esitoLabel(v) {
  return v ? t(`definizioni_workflow.ed_esito_regola_${v}`) : t('definizioni_workflow.ed_prereq_qualsiasi_esito')
}

const form = reactive({
  template_flusso_origine_id: null,
  tipo_prestazione_dest_id: null,
  template_flusso_dest_id: null,
  esito_richiesto: null,
  auto: false,
  attivo: true,
  descrizione: '',
})
watch(
  [() => coll.formMode.value, () => coll.rowInForm.value?.id],
  () => {
    if (coll.formMode.value === 'create') {
      Object.assign(form, {
        template_flusso_origine_id: null,
        tipo_prestazione_dest_id: null,
        template_flusso_dest_id: null,
        esito_richiesto: null,
        auto: false,
        attivo: true,
        descrizione: '',
      })
    } else if (coll.formMode.value === 'edit') {
      const r = coll.rowInForm.value
      Object.assign(form, {
        template_flusso_origine_id: r?.template_flusso_origine_id ?? null,
        tipo_prestazione_dest_id: r?.tipo_prestazione_dest_id ?? null,
        template_flusso_dest_id: r?.template_flusso_dest_id ?? null,
        esito_richiesto: r?.esito_richiesto ?? null,
        auto: r?.auto ?? false,
        attivo: r?.attivo ?? true,
        descrizione: r?.descrizione ?? '',
      })
    }
  },
)
const canSave = computed(
  () => !!form.template_flusso_origine_id && !!form.tipo_prestazione_dest_id,
)
function onSave() {
  coll.save({
    template_flusso_origine_id: form.template_flusso_origine_id,
    tipo_prestazione_dest_id: form.tipo_prestazione_dest_id,
    template_flusso_dest_id: form.template_flusso_dest_id || null,
    esito_richiesto: form.esito_richiesto || null,
    auto: form.auto,
    attivo: form.attivo,
    descrizione: form.descrizione?.trim() || null,
  })
}
</script>

<template>
  <CollectionEditorPanel
    :coll="coll"
    :rows="rows"
    :readonly="readonly"
    :add-label="t('definizioni_workflow.ed_aggiungi')"
    :empty-label="t('definizioni_workflow.ed_regole_generazione_vuoto')"
    :can-save="canSave"
    @save="onSave"
  >
    <template #columns>
      <Column :header="t('definizioni_workflow.ed_col_origine')" style="min-width: 150px;">
        <template #body="{ data }">{{ stepCodice(data.template_flusso_origine_id) }}</template>
      </Column>
      <Column :header="t('definizioni_workflow.ed_col_tipo_dest')" style="min-width: 160px;">
        <template #body="{ data }">{{ tipoLabel(data.tipo_prestazione_dest_id) }}</template>
      </Column>
      <Column :header="t('definizioni_workflow.ed_col_dest')" style="min-width: 130px;">
        <template #body="{ data }">{{ stepCodice(data.template_flusso_dest_id) }}</template>
      </Column>
      <Column :header="t('definizioni_workflow.ed_col_esito_richiesto')" style="width: 130px;">
        <template #body="{ data }">{{ esitoLabel(data.esito_richiesto) }}</template>
      </Column>
      <Column :header="t('definizioni_workflow.ed_col_auto')" style="width: 80px;">
        <template #body="{ data }">
          <ToggleSwitch :model-value="data.auto" disabled />
        </template>
      </Column>
      <Column :header="t('definizioni_workflow.ed_col_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <ToggleSwitch :model-value="data.attivo" :disabled="readonly" @update:model-value="coll.toggleAttivo(data)" />
        </template>
      </Column>
    </template>
    <template #form>
      <div class="form-field">
        <label>{{ t('definizioni_workflow.ed_col_origine') }} *</label>
        <Select v-model="form.template_flusso_origine_id" :options="stepOptions" option-label="label" option-value="value" filter :placeholder="t('definizioni_workflow.ed_ph_seleziona')" class="w-full" />
      </div>
      <div class="form-field">
        <label>{{ t('definizioni_workflow.ed_col_tipo_dest') }} *</label>
        <LookupSelect v-model="form.tipo_prestazione_dest_id" rel="pratiche.tipi_prestazione" :placeholder="t('definizioni_workflow.ed_ph_seleziona')" />
      </div>
      <div class="form-field">
        <label>{{ t('definizioni_workflow.ed_col_dest') }}</label>
        <Select v-model="form.template_flusso_dest_id" :options="stepOptions" option-label="label" option-value="value" filter show-clear :placeholder="t('definizioni_workflow.ed_ph_seleziona')" class="w-full" />
      </div>
      <div class="form-field">
        <label>{{ t('definizioni_workflow.ed_col_esito_richiesto') }}</label>
        <Select v-model="form.esito_richiesto" :options="esitoOptions" option-label="label" option-value="value" show-clear :placeholder="t('definizioni_workflow.ed_prereq_qualsiasi_esito')" class="w-full" />
      </div>
      <div class="form-field form-field--wide">
        <label>{{ t('definizioni_workflow.ed_col_descrizione') }}</label>
        <InputText v-model="form.descrizione" class="w-full" />
      </div>
      <div class="form-field form-field--toggle">
        <label>{{ t('definizioni_workflow.ed_col_auto') }}</label>
        <ToggleSwitch v-model="form.auto" />
      </div>
      <div class="form-field form-field--toggle">
        <label>{{ t('definizioni_workflow.ed_col_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" />
      </div>
    </template>
  </CollectionEditorPanel>
</template>
