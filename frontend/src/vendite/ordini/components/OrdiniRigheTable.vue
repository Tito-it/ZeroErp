<script setup>
// Scopo: Sezione master-detail inline righe ordine. Tabella sopra + form sotto
//        nello stesso drawer, niente Dialog annidato (pattern coerente con
//        ContrattoRigheDrawer / PreventiviRigheTable, frontend-standards
//        §Master-detail inline). Modifica = click riga; azioni secondarie
//        (elimina) in RowActionsMenu kebab.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useOrdiniStore } from '../stores/ordini'
import { MANAGE_ICONS } from '../../../core/constants'
import { formatCurrency, formatNumber } from '../../../core/utils/format'
import OrdiniRigaForm from './OrdiniRigaForm.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const { t } = useI18n()
const store = useOrdiniStore()
const { execute } = useApiHandler()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  ordineId: { type: Number, required: true },
  isModificabile: { type: Boolean, default: true },
})

// Eventi:
//  - `changed`: dopo create/update/delete riga (parent ricarica detail/totali).
//  - `form-aperto`: il drawer parent (OrdiniDrawer) lo usa per nascondere il
//    proprio FormFooter Salva/Annulla testata durante l'edit-riga.
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
    tooltip: t('vendite.ordini.aggiungi_riga'),
    icon: MANAGE_ICONS.ADD,
    visible: props.isModificabile,
    command: onNuovaRiga,
  },
])

async function loadRighe() {
  if (!props.ordineId) return
  loadingRighe.value = true
  try {
    righe.value = await store.loadRighe(props.ordineId)
  } finally {
    loadingRighe.value = false
  }
}

watch(() => props.ordineId, loadRighe, { immediate: true })

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
// cosi' il watcher del form ri-popola il prezzo corrente.
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
    message: t('vendite.ordini.conferma_elimina_riga'),
    onAccept: async () => {
      const result = await execute(
        () => store.eliminaRiga(props.ordineId, riga.id),
        { successMessage: t('vendite.ordini.riga_eliminata') }
      )
      if (rigaSelezionata.value?.id === riga.id) chiudiForm()
      await loadRighe()
      if (result !== null) emit('changed')
    }
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
        <h4 style="margin: 0;">{{ t('vendite.ordini.section_righe') }}</h4>
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
      sort-field="riga_nr"
      :sort-order="1"
      removable-sort
      @row-click="onRowClick">
      <Column field="articolo_codice" :header="t('vendite.ordini.riga_articolo')" sortable style="width: 120px;" />
      <Column field="descrizione" :header="t('vendite.ordini.riga_descrizione')" sortable />
      <Column field="qta_operativa" :header="t('vendite.ordini.riga_quantita')" sortable style="width: 90px;">
        <template #body="{ data }">{{ formatNumber(data.qta_operativa) }}</template>
      </Column>
      <Column field="uom_codice" :header="t('vendite.ordini.riga_uom')" style="width: 70px;" />
      <Column field="prezzo_unitario" :header="t('vendite.ordini.riga_prezzo')" sortable style="width: 130px;">
        <template #body="{ data }">
          {{ formatCurrency(data.prezzo_unitario, { minimumFractionDigits: 6, maximumFractionDigits: 6 }) }}
        </template>
      </Column>
      <Column field="sconto_perc" :header="t('vendite.ordini.riga_sconto')" sortable style="width: 80px;">
        <template #body="{ data }">{{ data.sconto_perc ? `${data.sconto_perc}%` : '' }}</template>
      </Column>
      <Column field="importo_riga" :header="t('vendite.ordini.riga_importo')" sortable style="width: 120px;">
        <template #body="{ data }">{{ formatCurrency(data.importo_riga) }}</template>
      </Column>
      <Column field="iva_descrizione" :header="t('vendite.ordini.riga_iva')" sortable style="width: 80px;">
        <template #body="{ data }">{{ data.iva_descrizione || data.iva_codice || '' }}</template>
      </Column>
      <Column v-if="isModificabile" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>

    <!-- Form master-detail inline: visibile SOLO quando attivo. OrdiniRigaForm
         espone gia' Salva/Annulla interni (no FormFooter: e' una sezione). -->
    <div v-if="formMode" class="app-drawer-section" style="margin-top: 1rem;">
      <h4>{{ formMode === 'edit' ? t('vendite.ordini.modifica_riga') : t('vendite.ordini.nuova_riga') }}</h4>
      <OrdiniRigaForm
        :ordine-id="ordineId"
        :riga="rigaSelezionata"
        @saved="onRigaSaved"
        @componenti-changed="onComponentiChanged"
        @cancel="chiudiForm"
      />
    </div>
  </div>
</template>
