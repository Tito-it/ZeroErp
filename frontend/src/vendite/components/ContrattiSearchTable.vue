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
import { defaultFiltroDataDa, toMeseString, oggiAziendale } from '../../core/utils/date'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import LookupSelect from '../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ContrattoCella, { CELLE_CONTRATTO } from './ContrattoCella.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import PdfDocumentiSorgenteDialog from '../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import ContrattoNoteDrawer from './ContrattoNoteDrawer.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MONTH_FORMAT, TIPO_RUOLO, MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { SORGENTE_CODES } from '../../documenti/constants'
import FiltroPeriodo from '../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'

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
const { bindSelect, bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_doc_contratto_id')
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
const { value: ambitoFilter, onChange: onAmbitoChange } = bindSelect('ambito')
// Il periodo e' UN filtro con due estremi: un binding, un componente.
// ⭐ `clearToDa`: questa lista vuole sempre un floor su `data_da` — svuotandola
//    torna lo stesso default dello store (regola unica in core/utils/date).
//    Ricalcolarlo qui significherebbe due formule da tenere allineate a mano.
// ⚠️ Il floor entra anche nell'invariante `da <= a`: `bindPeriodo` controlla il
//    valore RISOLTO, non quello emesso dal widget — altrimenti svuotare
//    `data_da` scriverebbe un floor che puo' cadere dopo `data_a`, e
//    l'intervallo resterebbe invertito proprio dove il `clearTo` esiste.
const periodo = bindPeriodo('data_da', 'data_a', { clearToDa: defaultFiltroDataDa })
// ⭐ `scadenza_mese` e' UN `computed` SULLO STORE, non un `ref` copiato, e la
//    ragione non e' lo stile: lo store tiene `YYYY-MM` e il widget una `Date`,
//    quindi qui c'e' un punto che TRADUCE. Un `ref` che spinge e basta
//    continuerebbe a mostrare il mese scelto dopo un «Pulisci filtri» del
//    drawer, su una lista che quel filtro non ce l'ha piu' — senza nessun
//    errore. Cosi' la sede del filtro resta una sola e la casella la legge.
// ⚠️ Non c'e' un `bindMese` nel BB dei binder: e' l'unica occorrenza del
//    prodotto, e la regola del 2 dice di estrarre alla seconda.
const scadenzaMeseFilter = computed({
  get: () => {
    const v = store.filters.scadenza_mese
    if (!v) return null
    const [anno, mese] = String(v).split('-')
    return new Date(Number(anno), Number(mese) - 1, 1)
  },
  set: (val) => {
    if (!val) {
      store.filters.scadenza_mese = null
      return
    }
    store.filters.scadenza_mese = toMeseString(val)
  },
})

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

// ⚠️ Nel template `v-model` PRECEDE `@update:model-value`: Vue accoda i
//    listener nell'ordine in cui sono scritti, quindi qui lo store e' gia'
//    scritto dal setter (stessa regola gia' in uso per `bindSelect`).
function onScadenzaMeseChange() {
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
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText class="app-filter-w-lg" v-model="searchText" :placeholder="t('vendite.contratti.search_placeholder')"  />
          </template>
          <LookupSelect
            v-model="statoFilter"
            class="app-filter-w-md"
            rel="config.stati_doc_contratti"
            :placeholder="t('vendite.contratti.filtro_stato')"
            show-clear
            @change="onStatoChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            class="app-filter-w-md"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.contratti.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <Select
            v-model="ambitoFilter"
            class="app-filter-w-md"
            :options="ambitoOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('vendite.contratti.filtro_ambito')"
            @change="onAmbitoChange"
          />
          <FiltroPeriodo :periodo="periodo" />
          <!-- ⚠️ Un DatePicker SOLO resta legittimo: «scadenza mese» e' un
               filtro a se', non un estremo di periodo. -->
          <DatePicker v-model="scadenzaMeseFilter" :placeholder="t('vendite.contratti.filtro_scadenza_mese')"
            class="app-filter-w-sm"
            view="month" :date-format="MONTH_FORMAT" show-icon show-button-bar
            :min-date="oggiAziendale()"
            @update:modelValue="onScadenzaMeseChange" />
        </FiltriLista>
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
        <!-- Stato e lineage: la cella e' il BB `ContrattoCella`, condiviso col
             drawer dei contratti del cliente. -->
        <template v-for="c in CELLE_CONTRATTO" :key="c" #[`cell-${c}`]="{ data }">
          <ContrattoCella :colonna="c" :data="data" />
        </template>

        <template #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
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
      :sorgente-code="SORGENTE_CODES.CONTRATTO"
      :sorgente-id="pdfDialogContratto?.id ?? null"
      :emittente-fiscale-id="pdfDialogContratto?.emittente_fiscale_id ?? null"
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
