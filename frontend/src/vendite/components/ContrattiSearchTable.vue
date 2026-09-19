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
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { statoContrattoSeverity } from '../../core/utils/severity'
import { defaultFiltroDataDa } from '../../core/utils/date'
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
import LineagePraticaCell from '../_shared/lineage/LineagePraticaCell.vue'
import LineageFaseTag from '../_shared/lineage/LineageFaseTag.vue'
import LineageFrontieraChip from '../_shared/lineage/LineageFrontieraChip.vue'
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
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportContratti,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'vendite.contratti.nuovo_contratto',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'valido_dal' },
})

// Filtri custom (toolbar caller) — binding store via BB (B14).
const { bindSelect, bindDate } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_doc_contratto_id')
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
const { value: ambitoFilter, onChange: onAmbitoChange } = bindSelect('ambito')
// data_da: la lista vuole sempre un floor → `clearTo` ripristina lo stesso
// default dello store (regola unica in core/utils/date). Ricalcolarlo qui
// significherebbe due formule da tenere allineate a mano.
const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da', {
  clearTo: defaultFiltroDataDa,
})
const { value: dataAFilter, onChange: onDataAChange } = bindDate('data_a')
// scadenza_mese: cast a YYYY-MM da Date → resta custom.
const scadenzaMeseFilter = ref(null)

const ambitoOptions = computed(() => [
  { value: null, label: t('common.all') },
  { value: 'COMMODITY', label: t('vendite.contratti.ambito_commodity') },
  { value: 'COMMERCIO', label: t('vendite.contratti.ambito_commercio') },
])

// Params export: la lista che stai guardando, dalla sede unica dello store
// (`paramsFiltro`: ricerca, filtri di dominio, ORDINAMENTO). ⚠️ Fino al
// 2026-09-18 questo file si ricostruiva i filtri a mano dai ref della toolbar
// e non mandava l'ordinamento: il file usciva sempre nell'ordine di default
// del backend, qualunque colonna l'operatore avesse cliccato. E la ricerca
// viene dallo store (debounced), non dal ref immediato: e' quella con cui la
// lista a video e' stata davvero interrogata.
function buildExportParams(format) {
  return { formato: format, ...store.paramsFiltro() }
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
  if (!row || row.stato_codice_interno === 'DRAFT') return
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
      label: t('vendite.contratti.pdf.label_scarica'),
      icon: MANAGE_ICONS.PDF,
      severity: 'primary',
      disabled: data.stato_codice_interno === 'DRAFT',
      tooltip: data.stato_codice_interno === 'DRAFT'
        ? t('vendite.contratti.pdf.tooltip_lista_disabilitato')
        : t('vendite.contratti.pdf.tooltip_lista'),
      command: () => onPdfClick(data),
    },
    {
      key: 'gestisci-righe',
      label: t('vendite.contratti.gestisci_righe'),
      icon: MANAGE_ICONS.RIGHE,
      command: () => emit('open-righe', data),
    },
    {
      key: 'gestisci-note',
      label: t('vendite.contratti.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => onNoteClick(data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.CONTRATTO)
// data_da ha sempre un default (floor standard): la lista si carica subito.
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
        <div class="app-page-filters" :inert="perimetroBloccato">
          <InputText v-model="searchText" :placeholder="t('vendite.contratti.search_placeholder')" style="width: 320px;" />
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_contratti"
            :placeholder="t('vendite.contratti.filtro_stato')"
            show-clear
            @change="onStatoChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.contratti.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <Select
            v-model="ambitoFilter"
            :options="ambitoOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('vendite.contratti.filtro_ambito')"
            @change="onAmbitoChange"
            style="min-width: 160px;"
          />
          <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
            date-format="dd/mm/yy" show-icon show-button-bar style="width: 150px;"
            @update:modelValue="onDataDaChange" />
          <DatePicker v-model="dataAFilter" :placeholder="t('common.data_a')"
            date-format="dd/mm/yy" show-icon show-button-bar style="width: 150px;"
            @update:modelValue="onDataAChange" />
          <DatePicker v-model="scadenzaMeseFilter" :placeholder="t('vendite.contratti.filtro_scadenza_mese')"
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
          <Tag :value="data.stato_descrizione" :severity="statoContrattoSeverity(data.stato_codice_interno)" />
        </template>

        <!-- Colonne lineage (Fase B): pratica cliccabile, fase, chip transito. -->
        <template #cell-pratica="{ data }">
          <LineagePraticaCell :pratica-id="data.pratica_id" :pratica-numero="data.pratica_numero" :n-pratiche="data.n_pratiche" />
        </template>
        <template #cell-fase="{ data }">
          <LineageFaseTag :fase="data.fase" />
        </template>
        <template #cell-transito="{ data }">
          <LineageFrontieraChip :is-transitato="data.is_transitato" :tipo-codice="data.frontiera_tipo_codice_interno"
            :natura-codice="data.frontiera_natura_doc_codice_interno"
            :codice="data.frontiera_codice" :stato="data.frontiera_stato_codice_interno"
            :fase="data.frontiera_fase" :n-attivi="data.n_discendenti_attivi" />
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
        ? t('vendite.contratti.pdf.dialog_title', { numero: pdfDialogContratto.numero })
        : ''"
    />

    <ContrattoNoteDrawer
      v-if="noteDrawerContratto?.id"
      v-model:visible="noteDrawerVisible"
      :contratto-id="noteDrawerContratto.id"
    />
  </div>
</template>
