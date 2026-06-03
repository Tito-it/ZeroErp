<script setup>
// Scopo: Lista contratti v5 con filtri (stato, utility, ambito, date,
// scadenza mese). Migrazione DEF-8 (2026-06-02): <ListaConfigurabile
// codice="vendite.contratti"> con ritiro dinamico colonne (anti-scrollbar).
// Scaffolding (useSearchTable + ref lista + export + pageActions) centralizzato
// in useListaConfigurabilePage; qui restano solo filtri, slot e azioni di riga.
// Righe dalla vista `vw_contratti_lista`: cliente=`ragione_sociale_completa`,
// id.fiscale=`id_fiscale_univoco_cf_piva` (nomi canonici, niente alias).
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContrattiStore } from '../stores/contratti'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { exportContratti } from '../api/contratti'
import { toDateString } from '../../core/utils/date'
import { statoContrattoSeverity } from '../../core/utils/severity'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import LookupSelect from '../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import PdfDocumentiSorgenteDialog from '../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import ContrattoNoteDrawer from './ContrattoNoteDrawer.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TIPO_RUOLO, MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['new', 'row-click', 'open-righe'])
const { t } = useI18n()
const store = useContrattiStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  exportFn: exportContratti,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'contratti.nuovo_contratto',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'valido_dal' },
})

// Filtri custom (toolbar caller).
const statoFilter = ref(null)
const utilityFilter = ref(null)
const ambitoFilter = ref(null)
const dataDaFilter = ref(store.filters.data_da ? new Date(store.filters.data_da) : null)
const dataAFilter = ref(null)
const scadenzaMeseFilter = ref(null)

const ambitoOptions = computed(() => [
  { value: null, label: t('common.all') },
  { value: 'COMMODITY', label: t('contratti.ambito_commodity') },
  { value: 'COMMERCIO', label: t('contratti.ambito_commercio') },
])

// Params export: i filtri vivono in store.filters (sincronizzati dagli handler
// onXxxChange); `search` dal ref immediato. Funzione lazy (chiamata solo al
// click export), quindi puo' riferire `searchText` definito sopra.
function buildExportParams(format) {
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (store.filters.stato_doc_contratto_id != null) p.stato_doc_contratto_id = store.filters.stato_doc_contratto_id
  if (store.filters.utility_id != null) p.utility_id = store.filters.utility_id
  if (store.filters.ambito != null) p.ambito = store.filters.ambito
  if (store.filters.data_da) p.data_da = store.filters.data_da
  if (store.filters.data_a) p.data_a = store.filters.data_a
  if (store.filters.scadenza_mese) p.scadenza_mese = store.filters.scadenza_mese
  return p
}

function onStatoChange() { store.filters.stato_doc_contratto_id = statoFilter.value; applyFilters() }
function onUtilityChange() { store.filters.utility_id = utilityFilter.value; applyFilters() }
function onAmbitoChange() { store.filters.ambito = ambitoFilter.value; applyFilters() }
function onDataDaChange(val) {
  if (val) {
    store.filters.data_da = toDateString(val)
  } else {
    // Ripristina default anno-1: la lista ha sempre bisogno di un floor.
    const defaultVal = `${new Date().getFullYear() - 1}-01-01`
    dataDaFilter.value = new Date(defaultVal)
    store.filters.data_da = defaultVal
  }
  applyFilters()
}
function onDataAChange(val) {
  store.filters.data_a = val ? toDateString(val) : null
  applyFilters()
}
function onScadenzaMeseChange(val) {
  if (val) {
    const d = val instanceof Date ? val : new Date(val)
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    store.filters.scadenza_mese = `${yyyy}-${mm}`
  } else {
    store.filters.scadenza_mese = null
  }
  applyFilters()
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

// Sub-dialog PDF + drawer note (azioni di riga).
const pdfDialogVisible = ref(false)
const pdfDialogContratto = ref(null)
const noteDrawerVisible = ref(false)
const noteDrawerContratto = ref(null)

function onPdfClick(row) {
  if (!row || row.stato_codice === 'DRAFT') return
  pdfDialogContratto.value = row
  pdfDialogVisible.value = true
}
function onNoteClick(row) {
  if (!row?.id) return
  noteDrawerContratto.value = row
  noteDrawerVisible.value = true
}

// Azioni contestuali di riga (kebab). La modifica e' il click riga.
function buildRowActions(data) {
  return [
    {
      key: 'documenti-pdf',
      label: t('contratti.pdf.label_scarica'),
      icon: MANAGE_ICONS.PDF,
      severity: 'primary',
      disabled: data.stato_codice === 'DRAFT',
      tooltip: data.stato_codice === 'DRAFT'
        ? t('contratti.pdf.tooltip_lista_disabilitato')
        : t('contratti.pdf.tooltip_lista'),
      command: () => onPdfClick(data),
    },
    {
      key: 'gestisci-righe',
      label: t('contratti.gestisci_righe'),
      icon: MANAGE_ICONS.RIGHE,
      command: () => emit('open-righe', data),
    },
    {
      key: 'gestisci-note',
      label: t('contratti.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => onNoteClick(data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.CONTRATTO)
// data_da ha sempre un default (anno-1): la lista si carica subito.
onMounted(() => {
  store.fetchList()
})
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- Toolbar UNICA esterna (pattern lista standard): filtri a sinistra,
           PageActionsBar a destra. -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="searchText" :placeholder="t('contratti.search_placeholder')" style="width: 320px;" />
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_contratti"
            :placeholder="t('contratti.filtro_stato')"
            show-clear
            @change="onStatoChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('contratti.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <Select
            v-model="ambitoFilter"
            :options="ambitoOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('contratti.filtro_ambito')"
            @change="onAmbitoChange"
            style="min-width: 160px;"
          />
          <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
            date-format="dd/mm/yy" show-icon show-button-bar style="width: 150px;"
            @update:modelValue="onDataDaChange" />
          <DatePicker v-model="dataAFilter" :placeholder="t('common.data_a')"
            date-format="dd/mm/yy" show-icon show-button-bar style="width: 150px;"
            @update:modelValue="onDataAChange" />
          <DatePicker v-model="scadenzaMeseFilter" :placeholder="t('contratti.filtro_scadenza_mese')"
            view="month" date-format="mm/yy" show-icon show-button-bar style="width: 160px;"
            :min-date="new Date()"
            @update:modelValue="onScadenzaMeseChange" />
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
        codice="vendite.contratti"
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
        <!-- Stato contratto: Tag colorato per severity. -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoContrattoSeverity(data.stato_codice)" />
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

    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialogVisible"
      sorgente-code="CONTRATTO"
      :sorgente-id="pdfDialogContratto?.id ?? null"
      :title="pdfDialogContratto
        ? t('contratti.pdf.dialog_title', { numero: pdfDialogContratto.numero })
        : ''"
    />

    <ContrattoNoteDrawer
      v-if="noteDrawerContratto?.id"
      v-model:visible="noteDrawerVisible"
      :contratto-id="noteDrawerContratto.id"
    />
  </div>
</template>
