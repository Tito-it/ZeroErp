<script setup>
// Scopo: shell master-detail inline righe documento (B10 2026-06-05, regola del
//        2). Tabella sopra + form sotto nello stesso drawer (frontend-standards
//        §Master-detail inline). Possiede la macchina a stati identica fra
//        OrdiniRigheTable e PreventiviRigheTable: `formMode` null/create/edit,
//        `rigaSelezionata`/`selezione`, load/new/edit/chiudi/saved/
//        componentiChanged/delete, toolbar reload+nuovo, DataTable scaffold +
//        colonna azioni con elimina. Le colonne dati e il form di riga sono
//        slot (divergono per dominio: campo sconto, badge approvazione, ecc.).
//
// Lo standard frontend prescriveva di COPIARE questa struttura; B10 la promuove
// a BB → la duplicazione indotta dalla doc viene sanata (vedi frontend-standards
// §Master-detail inline, nota B10).
//
// Slot:
//   #columns                              → le <Column> dati (caller)
//   #form="{ riga, onSaved, onComponentiChanged, onCancel }" → il form di riga
//
// Uso:
//   <RigheMasterDetailTable
//     :parent-id="ordineId" :rows-loader="(id) => store.loadRighe(id)"
//     :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
//     :is-modificabile="isModificabile" title-key="..." new-tooltip-key="..."
//     confirm-delete-key="..." deleted-message-key="..."
//     new-label-key="..." edit-label-key="..." sort-field="riga_nr"
//     @changed="..." @form-aperto="...">
//     <template #columns> <Column .../> </template>
//     <template #form="{ riga, onSaved, onComponentiChanged, onCancel }">
//       <RigaForm :riga="riga" @saved="onSaved" @componenti-changed="onComponentiChanged" @cancel="onCancel" />
//     </template>
//   </RigheMasterDetailTable>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../composables/useApiHandler'
import { useConfirmAction } from '../composables/useConfirmAction'
import { MANAGE_ICONS } from '../constants'
import RowActionsMenu from './RowActionsMenu.vue'
import PageActionsBar from './PageActionsBar.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const { t } = useI18n()
const { execute } = useApiHandler()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  parentId: { type: Number, default: null },
  // (parentId) => Promise<rows[]> — store.loadRighe già unwrappato.
  rowsLoader: { type: Function, required: true },
  // (parentId, rigaId) => Promise — store.eliminaRiga.
  deleteAction: { type: Function, required: true },
  isModificabile: { type: Boolean, default: true },
  titleKey: { type: String, required: true },
  newTooltipKey: { type: String, required: true },
  confirmDeleteKey: { type: String, required: true },
  deletedMessageKey: { type: String, required: true },
  newLabelKey: { type: String, required: true },
  editLabelKey: { type: String, required: true },
  sortField: { type: String, default: 'riga_nr' },
  // (riga) => bool: disabilita elimina su righe specifiche (es. approvazione PENDING).
  deleteDisabled: { type: Function, default: () => false },
})

// Eventi:
//  - `changed`: dopo create/update/delete riga (parent ricarica detail/totali).
//  - `form-aperto`: il drawer parent nasconde il proprio FormFooter testata
//    durante l'edit-riga.
const emit = defineEmits(['changed', 'form-aperto'])

const righe = ref([])
const loadingRighe = ref(false)
// formMode: null (nessun form), 'create', 'edit'.
const formMode = ref(null)
watch(formMode, (m) => emit('form-aperto', m !== null))
const rigaSelezionata = ref(null)
const selezione = ref(null)

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: loadRighe,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t(props.newTooltipKey),
    icon: MANAGE_ICONS.ADD,
    visible: props.isModificabile,
    command: onNuovaRiga,
  },
])

async function loadRighe() {
  if (!props.parentId) return
  loadingRighe.value = true
  try {
    righe.value = await props.rowsLoader(props.parentId)
  } finally {
    loadingRighe.value = false
  }
}

watch(() => props.parentId, loadRighe, { immediate: true })

function onNuovaRiga() {
  rigaSelezionata.value = null
  selezione.value = null
  formMode.value = 'create'
}

function onEditRiga(riga) {
  rigaSelezionata.value = riga
  selezione.value = riga
  formMode.value = 'edit'
}

function chiudiForm() {
  formMode.value = null
  rigaSelezionata.value = null
  selezione.value = null
}

async function onRigaSaved() {
  chiudiForm()
  await loadRighe()
  emit('changed')
}

// Mutation su un componente BoM CASO A (PATCH prezzo o DELETE): ricarica le
// righe per riflettere il nuovo prezzo padre (SUM componenti via trigger DB),
// MA NON chiude il form. Risincronizza rigaSelezionata sull'oggetto fresco
// così il watcher del form ri-popola il prezzo corrente.
async function onComponentiChanged() {
  await loadRighe()
  if (formMode.value === 'edit' && rigaSelezionata.value?.id != null) {
    const id = rigaSelezionata.value.id
    const refreshed = righe.value.find((r) => r.id === id)
    if (refreshed) rigaSelezionata.value = refreshed
  }
  emit('changed')
}

function onDeleteRiga(riga) {
  confirmAction({
    message: t(props.confirmDeleteKey),
    onAccept: async () => {
      const result = await execute(
        () => props.deleteAction(props.parentId, riga.id),
        { successMessage: t(props.deletedMessageKey) },
      )
      if (rigaSelezionata.value?.id === riga.id) chiudiForm()
      await loadRighe()
      if (result !== null) emit('changed')
    },
  })
}

function buildRowActions(riga) {
  return [
    {
      key: 'elimina',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: props.isModificabile,
      disabled: props.deleteDisabled(riga),
      command: () => onDeleteRiga(riga),
    },
  ]
}

function onRowClick(event) {
  if (!props.isModificabile) return
  onEditRiga(event.data)
}

defineExpose({ loadRighe })
</script>

<template>
  <div>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h4 style="margin: 0;">{{ t(titleKey) }}</h4>
      </div>
      <PageActionsBar :actions="pageActions" />
    </div>

    <DataTable :value="righe" striped-rows size="small" class="app-datatable app-datatable--inner"
      data-key="id"
      :loading="loadingRighe"
      :row-hover="isModificabile"
      :selection-mode="isModificabile ? 'single' : null"
      v-model:selection="selezione"
      paginator
      :rows="10"
      :rows-per-page-options="[10, 25, 50]"
      paginator-position="top"
      :sort-field="sortField"
      :sort-order="1"
      removable-sort
      @row-click="onRowClick">
      <slot name="columns" />
      <Column v-if="isModificabile" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>

    <!-- Form master-detail inline: visibile SOLO quando attivo. Il form di riga
         espone già Salva/Annulla interni (no FormFooter: è una sezione). -->
    <div v-if="formMode" class="app-drawer-section" style="margin-top: 1rem;">
      <h4>{{ formMode === 'edit' ? t(editLabelKey) : t(newLabelKey) }}</h4>
      <slot
        name="form"
        :riga="rigaSelezionata"
        :on-saved="onRigaSaved"
        :on-componenti-changed="onComponentiChanged"
        :on-cancel="chiudiForm"
      />
    </div>
  </div>
</template>
