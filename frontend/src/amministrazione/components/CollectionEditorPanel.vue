<script setup>
// Shell presentazionale per le sotto-liste editabili inline dell'editor
// definizioni (figli step + archi). Estratto nel controllo qualità Fase 3
// (regola del 2): rimuove la duplicazione di toolbar «Aggiungi» + tabella con
// colonna azioni + contenitore form + pulsanti Salva/Annulla, presente in 6
// tab. La macchina CRUD arriva già pronta come `coll` (useEditableCollection);
// le colonne dati e i campi form restano slot per-tab (divergono legittimamente).
//
// Uso:
//   <CollectionEditorPanel :coll="coll" :rows="rows" :readonly="readonly"
//     :add-label="t('...')" :empty-label="t('...')" :can-save="canSave" @save="onSave">
//     <template #columns> <Column .../> ... </template>
//     <template #form> <div class="form-field"> ... </div> </template>
//   </CollectionEditorPanel>
import { useI18n } from 'vue-i18n'
// ⛔ DEBITO, non eccezione: le sotto-collezioni di step e archi (6 tab) sono
// master-detail inline; questa e' la sede unica della loro tabella, quindi la
// conversione si fa qui, una volta per tutti e sei.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { MANAGE_ICONS } from '../../core/constants'

defineProps({
  // Istanza di useEditableCollection (espone formMode/saving/nuovaRiga/
  // chiudiForm/buildRowActions).
  coll: { type: Object, required: true },
  rows: { type: Array, default: () => [] },
  readonly: { type: Boolean, default: false },
  addLabel: { type: String, required: true },
  emptyLabel: { type: String, required: true },
  canSave: { type: Boolean, default: true },
})
defineEmits(['save'])

const { t } = useI18n()
</script>

<template>
  <div>
    <div v-if="!readonly" class="coll-toolbar">
      <Button :label="addLabel" :icon="MANAGE_ICONS.ADD" size="small" text @click="coll.nuovaRiga()" />
    </div>
    <DataTable :value="rows" data-key="id" striped-rows size="small" class="app-datatable app-datatable--inner">
      <template #empty>{{ emptyLabel }}</template>
      <slot name="columns" />
      <Column v-if="!readonly" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="coll.buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>

    <div v-if="coll.formMode.value" :ref="coll.ancoraForm" class="app-drawer-section coll-form">
      <slot name="form" />
      <div class="coll-form__actions">
        <Button :label="t('common.cancel')" severity="secondary" text @click="coll.chiudiForm()" />
        <Button :label="t('common.save')" :disabled="!canSave" :loading="coll.saving.value" @click="$emit('save')" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.coll-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.25rem;
}
.coll-form {
  margin-top: 0.75rem;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.75rem 1rem;
}
.coll-form :deep(.form-field) {
  min-width: 200px;
}
.coll-form :deep(.form-field--num) {
  min-width: 130px;
}
.coll-form :deep(.form-field--wide) {
  min-width: 240px;
  flex: 1;
}
.coll-form :deep(.form-field--full) {
  flex-basis: 100%;
}
.coll-form :deep(.form-field--toggle) {
  min-width: auto;
}
.coll-form__actions {
  display: flex;
  gap: 0.5rem;
  margin-left: auto;
}
</style>
