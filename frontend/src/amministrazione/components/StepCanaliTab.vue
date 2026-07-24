<script setup>
// Sotto-lista CANALI di uno step (FE-3.3). Attach/detach + toggle attivo.
// Scaffold (toolbar/tabella/azioni/form) nello shell CollectionEditorPanel;
// macchina CRUD nel composable; qui solo colonne + campo canale_id.
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import ToggleSwitch from 'primevue/toggleswitch'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useStepFigliCollection } from '../composables/useStepFigliCollection'
import CollectionEditorPanel from './CollectionEditorPanel.vue'

const props = defineProps({
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
  kind: 'canali',
  messages: {
    created: t('amministrazione.definizioni_workflow.ed_msg_figlio_creato'),
    saved: t('amministrazione.definizioni_workflow.ed_msg_figlio_salvato'),
    deleted: t('amministrazione.definizioni_workflow.ed_msg_figlio_eliminato'),
  },
  confirmDelete: (row) =>
    t('amministrazione.definizioni_workflow.ed_conferma_elimina_figlio', { nome: row.canale_codice }),
  onChanged: () => emit('changed'),
})

const form = reactive({ canale_id: null, attivo: true })
// Ri-popola il form su qualsiasi apertura/cambio riga (anche edit→edit su una
// riga diversa: rowInForm.id cambia pur restando in 'edit').
watch(
  [() => coll.formMode.value, () => coll.rowInForm.value?.id],
  () => {
    if (coll.formMode.value === 'create') {
      form.canale_id = null
      form.attivo = true
    } else if (coll.formMode.value === 'edit') {
      form.canale_id = coll.rowInForm.value?.canale_id ?? null
      form.attivo = coll.rowInForm.value?.attivo ?? true
    }
  },
)
const canSave = computed(() => !!form.canale_id)
function onSave() {
  coll.save({ canale_id: form.canale_id, attivo: form.attivo })
}
</script>

<template>
  <CollectionEditorPanel
    :coll="coll"
    :rows="rows"
    :readonly="readonly"
    :add-label="t('amministrazione.definizioni_workflow.ed_aggiungi')"
    :empty-label="t('amministrazione.definizioni_workflow.ed_canali_vuoto')"
    :can-save="canSave"
    @save="onSave"
  >
    <template #columns>
      <Column field="canale_codice" :header="t('amministrazione.definizioni_workflow.ed_col_canale')" style="width: 140px;" />
      <Column field="canale_descrizione" :header="t('amministrazione.definizioni_workflow.ed_col_descrizione')" style="min-width: 180px;" />
      <Column field="canale_codice_interno" :header="t('amministrazione.definizioni_workflow.ed_col_canale_interno')" style="width: 150px;" />
      <Column :header="t('amministrazione.definizioni_workflow.ed_col_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <ToggleSwitch :model-value="data.attivo" :disabled="readonly" @update:model-value="coll.toggleAttivo(data)" />
        </template>
      </Column>
    </template>
    <template #form>
      <div class="form-field">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_canale') }} *</label>
        <LookupSelect v-model="form.canale_id" rel="config.canali_pratiche" :placeholder="t('amministrazione.definizioni_workflow.ed_ph_seleziona')" show-code />
      </div>
      <div class="form-field form-field--toggle">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" />
      </div>
    </template>
  </CollectionEditorPanel>
</template>
