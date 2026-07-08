<script setup>
// Sotto-lista COMPETENZE di uno step (FE-3.3): unità organizzativa + risorsa
// umana. La risorsa è scelta dall'elenco operatori (amm-software `operatori/`
// espone risorsa_umana_id + cognome/nome). Scaffold nello shell.
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import ToggleSwitch from 'primevue/toggleswitch'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { listOperatori } from '../api/amministrazione'
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
  kind: 'competenze',
  messages: {
    created: t('definizioni_workflow.ed_msg_figlio_creato'),
    saved: t('definizioni_workflow.ed_msg_figlio_salvato'),
    deleted: t('definizioni_workflow.ed_msg_figlio_eliminato'),
  },
  confirmDelete: (row) =>
    t('definizioni_workflow.ed_conferma_elimina_figlio', { nome: row.risorsa_umana_display }),
  onChanged: () => emit('changed'),
})

// Risorse umane dalla lista operatori: value = risorsa_umana_id, label =
// "cognome nome". Filtra chi non ha una risorsa umana e deduplica per id.
function risorseFetcher() {
  return listOperatori({ page_size: 200 })
}
function risorseTransform(res) {
  const seen = new Set()
  const out = []
  for (const o of res.data.data.results) {
    if (!o.risorsa_umana_id || seen.has(o.risorsa_umana_id)) continue
    seen.add(o.risorsa_umana_id)
    out.push({
      id: o.risorsa_umana_id,
      descrizione: `${o.soggetto_cognome || ''} ${o.soggetto_nome || ''}`.trim() || o.username,
    })
  }
  return out
}

const form = reactive({ unita_organizzativa_id: null, risorsa_umana_id: null, attivo: true })
watch(
  [() => coll.formMode.value, () => coll.rowInForm.value?.id],
  () => {
    if (coll.formMode.value === 'create') {
      form.unita_organizzativa_id = null
      form.risorsa_umana_id = null
      form.attivo = true
    } else if (coll.formMode.value === 'edit') {
      const r = coll.rowInForm.value
      form.unita_organizzativa_id = r?.unita_organizzativa_id ?? null
      form.risorsa_umana_id = r?.risorsa_umana_id ?? null
      form.attivo = r?.attivo ?? true
    }
  },
)
const canSave = computed(() => !!form.unita_organizzativa_id && !!form.risorsa_umana_id)
function onSave() {
  coll.save({
    unita_organizzativa_id: form.unita_organizzativa_id,
    risorsa_umana_id: form.risorsa_umana_id,
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
    :empty-label="t('definizioni_workflow.ed_competenze_vuoto')"
    :can-save="canSave"
    @save="onSave"
  >
    <template #columns>
      <Column field="unita_organizzativa_descrizione" :header="t('definizioni_workflow.ed_col_unita')" style="min-width: 200px;" />
      <Column field="risorsa_umana_display" :header="t('definizioni_workflow.ed_col_risorsa')" style="min-width: 200px;" />
      <Column :header="t('definizioni_workflow.ed_col_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <ToggleSwitch :model-value="data.attivo" :disabled="readonly" @update:model-value="coll.toggleAttivo(data)" />
        </template>
      </Column>
    </template>
    <template #form>
      <div class="form-field">
        <label>{{ t('definizioni_workflow.ed_col_unita') }} *</label>
        <LookupSelect v-model="form.unita_organizzativa_id" rel="config.unita_organizzative" :placeholder="t('definizioni_workflow.ed_ph_seleziona')" />
      </div>
      <div class="form-field">
        <label>{{ t('definizioni_workflow.ed_col_risorsa') }} *</label>
        <LookupSelect v-model="form.risorsa_umana_id" :fetcher="risorseFetcher" lookup-key="amm.operatori.risorse" :transform="risorseTransform" :placeholder="t('definizioni_workflow.ed_ph_seleziona')" />
      </div>
      <div class="form-field form-field--toggle">
        <label>{{ t('definizioni_workflow.ed_col_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" />
      </div>
    </template>
  </CollectionEditorPanel>
</template>
