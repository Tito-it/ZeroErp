<script setup>
// Scopo: Lista preventivi vendita configurabile (DEF-8). Migrazione 2026-06-03:
// <ListaConfigurabile codice="vendite.preventivi"> con ritiro dinamico colonne
// (anti-scrollbar), personalizzazione colonne, export CSV/XLSX. Scaffolding
// (useSearchTable + ref lista + export + pageActions) centralizzato in
// useListaConfigurabilePage; qui restano filtri custom, slot e azioni di riga.
// Righe dalla vista canonica `vw_preventivi_lista`: cliente=`ragione_sociale_completa`,
// id.fiscale=`id_fiscale_univoco_cf_piva` (nomi canonici, niente alias).
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreventiviStore } from '../stores/preventivi'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { exportPreventivi } from '../api/preventiviApi'
import { statoPreventiveSeverity } from '../../../core/utils/severity'
import { toDateString } from '../../../core/utils/date'
import { DATE_FORMAT, MANAGE_ICONS, TAB_ENTITIES, TIPO_RUOLO } from '../../../core/constants'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigurabile from '../../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../../core/components/ExportDialog.vue'
import PdfDocumentiSorgenteDialog from '../../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import PreventivoNoteDrawer from '../../components/PreventivoNoteDrawer.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = usePreventiviStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, configReady,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  exportFn: exportPreventivi,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'preventivi.nuovo_preventivo',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// --- Filtri custom (toolbar caller) ---
const statoFilter = ref(store.filters.stato ?? null)
const utilityFilter = ref(store.filters.utility_id ?? null)
const dataDaFilter = ref(store.filters.data_da ? new Date(store.filters.data_da + 'T00:00:00') : null)
const dataAlFilter = ref(store.filters.data_a ? new Date(store.filters.data_a + 'T00:00:00') : null)
// Toggle "mostra storico revisioni": negazione del filtro store
// (mostraStorico=ON ⇔ solo_attiva=false). computed get/set per restare
// allineato al filtro reale anche se cambia altrove (reset, logout,
// ripristino sessione): single source of truth = store.
const mostraStorico = computed({
  get: () => !store.filters.solo_attiva,
  set: (val) => { store.filters.solo_attiva = !val },
})

// Params export: i filtri vivono in store.filters (sincronizzati dagli handler
// onXxxChange); `search` dal ref immediato. Funzione lazy (chiamata solo al
// click export), puo' riferire `searchText` definito sopra.
function buildExportParams(format) {
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (store.filters.stato != null) p.stato = store.filters.stato
  if (store.filters.utility_id != null) p.utility_id = store.filters.utility_id
  if (store.filters.data_da) p.data_da = store.filters.data_da
  if (store.filters.data_a) p.data_al = store.filters.data_a
  p.solo_attiva = store.filters.solo_attiva ? 'true' : 'false'
  if (store.filters.order_by) {
    p.order_by = store.filters.order_by
    p.order_dir = store.filters.order_dir || 'desc'
  }
  return p
}

function onStatoChange() { store.filters.stato = statoFilter.value; applyFilters() }
function onUtilityChange() { store.filters.utility_id = utilityFilter.value; applyFilters() }
function onDataDaChange() {
  store.filters.data_da = dataDaFilter.value ? toDateString(dataDaFilter.value) : null
  applyFilters()
}
function onDataAlChange() {
  store.filters.data_a = dataAlFilter.value ? toDateString(dataAlFilter.value) : null
  applyFilters()
}
// Il setter del computed scrive gia' lo store; qui basta triggerare la fetch.
function onMostraStoricoChange() { applyFilters() }

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

// ── Sub-dialog PDF + drawer note (azioni di riga) ──
const pdfDialogVisible = ref(false)
const pdfDialogPreventivo = ref(null)
const noteDrawerVisible = ref(false)
const noteDrawerPreventivo = ref(null)

function onPdfClick(row) {
  if (!row || row.stato_codice_interno === 'DRAFT') return
  pdfDialogPreventivo.value = row
  pdfDialogVisible.value = true
}
function onNoteClick(row) {
  if (!row?.id) return
  noteDrawerPreventivo.value = row
  noteDrawerVisible.value = true
}

// Scopo: costruisce le azioni contestuali di riga. Modifica = click riga.
function buildRowActions(data) {
  return [
    {
      key: 'documenti-pdf',
      label: t('preventivi.pdf.label_scarica'),
      icon: MANAGE_ICONS.PDF,
      severity: 'primary',
      disabled: data.stato_codice_interno === 'DRAFT',
      tooltip: data.stato_codice_interno === 'DRAFT'
        ? t('preventivi.pdf.tooltip_lista_disabilitato')
        : t('preventivi.pdf.tooltip_lista'),
      command: () => onPdfClick(data),
    },
    {
      key: 'gestisci-note',
      label: t('preventivi.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => onNoteClick(data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.PREVENTIVO)

// Lista preventivi: ha filtro data_da con default anno-1 (frontend-standards
// "Filtro data standard"), quindi auto-load al mount. Lo store guard hasFilters
// considera data_da come filtro attivo: non rischiamo di tirar giu' "tutti i
// preventivi senza limiti" perche' il default e' di per se' un filtro temporale.
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- Toolbar UNICA esterna (pattern lista standard): filtri a sinistra,
           PageActionsBar a destra. -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="searchText" :placeholder="t('preventivi.search_placeholder')" style="width: 260px;" />
          <LookupSelect v-model="statoFilter" rel="config.stati_doc_preventivi" value-field="codice_interno"
            :placeholder="t('preventivi.filtro_stato')" show-clear @change="onStatoChange" style="width: 160px;" />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('preventivi.filtro_utility')"
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
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <ToggleSwitch v-model="mostraStorico" inputId="prev-mostra-storico"
              @change="onMostraStoricoChange" />
            <label for="prev-mostra-storico" style="font-size: 0.85rem; cursor: pointer;">
              {{ t('preventivi.filtro_mostra_storico') }}
            </label>
          </div>
        </div>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <Tag
              v-if="dirty"
              :value="t('lista_config.stato_temporanea')"
              severity="warn"
              v-tooltip.bottom="t('lista_config.stato_temporanea_tooltip')"
            />
            <Tag
              v-else-if="configReady"
              :value="t('lista_config.stato_salvata')"
              severity="success"
            />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <ListaConfigurabile
        ref="listaRef"
        codice="vendite.preventivi"
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
        <!-- Stato preventivo: Tag colorato per severity (legge stato_codice_interno). -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoPreventiveSeverity(data.stato_codice_interno)" />
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

    <!-- Dialog lista PDF per il preventivo selezionato. Riusa il building
         block `PdfDocumentiSorgenteDialog`. -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialogVisible"
      sorgente-code="PREVENTIVO"
      :sorgente-id="pdfDialogPreventivo?.id ?? null"
      :title="pdfDialogPreventivo
        ? t('preventivi.pdf.dialog_title', { numero: pdfDialogPreventivo.numero })
        : ''"
    />

    <PreventivoNoteDrawer
      v-if="noteDrawerPreventivo?.id"
      v-model:visible="noteDrawerVisible"
      :preventivo-id="noteDrawerPreventivo.id"
    />
  </div>
</template>
