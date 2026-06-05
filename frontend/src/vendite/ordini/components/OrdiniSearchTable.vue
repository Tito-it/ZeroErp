<script setup>
// Scopo: Lista ordini di vendita configurabile (DEF-8). Nasce direttamente
// <ListaConfigurabile codice="vendite.ordini"> (niente lista grezza da
// rifattorizzare dopo — analisi-ordini-vendita.md §6.1): ritiro dinamico
// colonne (anti-scrollbar), personalizzazione colonne, export CSV/XLSX.
// Scaffolding (useSearchTable + ref lista + export + pageActions) centralizzato
// in useListaConfigurabilePage; qui restano filtri custom, slot e azioni di
// riga. Righe dalla vista canonica `vw_ordini_lista`:
// cliente=`ragione_sociale_completa`, id.fiscale=`id_fiscale_univoco_cf_piva`,
// ba_codice, fatturazione_trigger, agente_denominazione, documento_origine_*.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import ListaConfigurabile from '../../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../../core/components/ExportDialog.vue'
import OrdineNoteDrawer from './OrdineNoteDrawer.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { useDocumentiPerSorgenteStore } from '../../../documenti/stores/documentiPerSorgente'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { DATE_FORMAT, MANAGE_ICONS, TAB_ENTITIES, TIPO_RUOLO } from '../../../core/constants'
import { toDateString } from '../../../core/utils/date'
import { downloadBlob } from '../../../core/utils/download'
import { statoOrdineSeverity } from '../../../core/utils/severity'
import { exportOrdini } from '../api/ordiniApi'
import { STATI_ORDINE_ANTEPRIMA_PDF } from '../constants'
import { useOrdiniStore } from '../stores/ordini'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useOrdiniStore()
const docStore = useDocumentiPerSorgenteStore()
const isBlocked = useInjectBlocked()
const { execute } = useApiHandler()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  exportFn: exportOrdini,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'vendite.ordini.nuovo_ordine',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// --- Filtri custom (toolbar caller) ---
const statoFilter = ref(store.filters.stato_codice_interno ?? null)
const utilityFilter = ref(store.filters.utility_id ?? null)
const dataDaFilter = ref(store.filters.data_da ? new Date(`${store.filters.data_da}T00:00:00`) : null)
const dataAlFilter = ref(store.filters.data_a ? new Date(`${store.filters.data_a}T00:00:00`) : null)

// Params export: i filtri vivono in store.filters; `search` dal ref immediato.
// I filtri data BE sono data_da/data_a (sul campo `data` della testata).
function buildExportParams(format) {
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (store.filters.stato_codice_interno != null) p.stato_codice_interno = store.filters.stato_codice_interno
  if (store.filters.utility_id != null) p.utility_id = store.filters.utility_id
  if (store.filters.billing_account_id != null) p.billing_account_id = store.filters.billing_account_id
  if (store.filters.data_da) p.data_da = store.filters.data_da
  if (store.filters.data_a) p.data_a = store.filters.data_a
  if (store.filters.order_by) {
    p.order_by = store.filters.order_by
    p.order_dir = store.filters.order_dir || 'desc'
  }
  return p
}

function onStatoChange() { store.filters.stato_codice_interno = statoFilter.value; applyFilters() }
function onUtilityChange() { store.filters.utility_id = utilityFilter.value; applyFilters() }
function onDataDaChange() {
  store.filters.data_da = dataDaFilter.value ? toDateString(dataDaFilter.value) : null
  applyFilters()
}
function onDataAlChange() {
  store.filters.data_a = dataAlFilter.value ? toDateString(dataAlFilter.value) : null
  applyFilters()
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

// ── Drawer note (azione di riga) ──
const noteDrawerVisible = ref(false)
const noteDrawerOrdine = ref(null)

async function onPdfClick(row) {
  if (!row?.id) return
  docStore.setSorgente(SORGENTE_CODES.ORDINE_VENDITA, row.id)
  const result = await execute(() => docStore.anteprima({}))
  if (!result) return
  downloadBlob(result.blob, result.fileName)
}

function onNoteClick(row) {
  if (!row?.id) return
  noteDrawerOrdine.value = row
  noteDrawerVisible.value = true
}

// Scopo: costruisce le azioni contestuali di riga. Modifica = click riga.
// Conferma/push vivono nel drawer (dove sono caricate le capability), non in
// lista: la lista resta consultazione + stampa ordine + note.
function buildRowActions(data) {
  return [
    {
      key: 'stampa-ordine',
      label: t('vendite.ordini.pdf.label_anteprima'),
      icon: MANAGE_ICONS.PDF,
      severity: 'primary',
      disabled: !STATI_ORDINE_ANTEPRIMA_PDF.includes(data.stato_codice_interno),
      tooltip: t('vendite.ordini.pdf.tooltip_anteprima'),
      command: () => onPdfClick(data),
    },
    {
      key: 'gestisci-note',
      label: t('vendite.ordini.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => onNoteClick(data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.ORDINE)

// Lista con filtro data_da default anno-1: auto-load al mount (lo store guard
// hasFilters considera data_da come filtro attivo).
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- Toolbar UNICA esterna (pattern lista standard). -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="searchText" :placeholder="t('vendite.ordini.search_placeholder')" style="width: 260px;" />
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_ordini"
            value-field="codice_interno"
            :placeholder="t('vendite.ordini.filtro_stato')"
            show-clear
            style="width: 160px;"
            @change="onStatoChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.ordini.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
            :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
            @date-select="onDataDaChange" @clear-click="onDataDaChange" />
          <DatePicker v-model="dataAlFilter" :placeholder="t('common.data_a')"
            :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
            @date-select="onDataAlChange" @clear-click="onDataAlChange" />
        </div>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <ListaConfigurabile
        ref="listaRef"
        codice="vendite.ordini"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        @page="onPage"
        @sort="onSort"
        @row-click="onRowClick"
        @config-loaded="onConfigLoaded"
      >
        <!-- Stato: Tag severity (niente badge "scaduta": concetto offerta-specifico). -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoOrdineSeverity(data.stato_codice_interno)" />
        </template>

        <template #actions="{ data, compact }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" :force-compact="compact" />
        </template>
      </ListaConfigurabile>
    </template>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />

    <OrdineNoteDrawer
      v-if="noteDrawerOrdine?.id"
      v-model:visible="noteDrawerVisible"
      :ordine-id="noteDrawerOrdine.id"
    />
  </div>
</template>
