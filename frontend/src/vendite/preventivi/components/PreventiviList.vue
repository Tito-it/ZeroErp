<script setup>
// Scopo: Lista preventivi vendita configurabile (DEF-8). Migrazione 2026-06-03:
// <ListaConfigurabile codice="vendite.preventivi"> con ritiro dinamico colonne
// (anti-scrollbar), personalizzazione colonne, export CSV/XLSX. Scaffolding
// (useSearchTable + ref lista + export + pageActions) centralizzato in
// useListaConfigurabilePage; qui restano filtri custom, slot e azioni di riga.
// Righe dalla vista canonica `vw_preventivi_lista`: cliente=`ragione_sociale_completa`,
// id.fiscale=`id_fiscale_univoco_cf_piva` (nomi canonici, niente alias).
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreventiviStore } from '../stores/preventivi'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { exportPreventivi } from '../api/preventiviApi'
import { statoPreventiveSeverity } from '../../../core/utils/severity'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { MANAGE_ICONS, TAB_ENTITIES, TIPO_RUOLO } from '../../../core/constants'
import { SORGENTE_CODES } from '../../../documenti/constants'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigurabile from '../../../core/components/ListaConfigurabile.vue'
import LineagePraticaCell from '../../_shared/lineage/LineagePraticaCell.vue'
import LineageFaseTag from '../../_shared/lineage/LineageFaseTag.vue'
import LineageFrontieraChip from '../../_shared/lineage/LineageFrontieraChip.vue'
import ExportDialog from '../../../core/components/ExportDialog.vue'
import FiltroToggle from '../../../core/components/FiltroToggle.vue'
import PdfDocumentiSorgenteDialog from '../../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import PreventivoNoteDrawer from '../../components/PreventivoNoteDrawer.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import FiltroPeriodo from '../../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../../core/components/FiltriLista.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = usePreventiviStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportPreventivi,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'vendite.preventivi.nuovo_preventivo',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// --- Filtri custom (toolbar caller) — binding store via BB (B14) ---
const { bindSelect, bindToggle, bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato')
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
// Il periodo e' UN filtro con due estremi: un binding, un componente.
const periodo = bindPeriodo()
// Toggle «mostra storico revisioni»: la NEGAZIONE del filtro dello store —
// acceso ⇔ `solo_ultima_revisione = false`, spento ⇔ `true` (il default).
// `bindToggle` con i due valori dichiarati: il widget resta un booleano.
const { value: mostraStorico, onChange: onMostraStoricoChange } = bindToggle(
  'solo_ultima_revisione', { on: false, off: true },
)

// Scopo: i parametri dell'export = QUELLI DELLA LISTA a video, dalla sede
//        unica dello store (`paramsFiltro`: ricerca, filtri di dominio col nome
//        sul filo, ordinamento). ⛔ Fino al 2026-09-18 questo blocco ricostruiva i
//        filtri a mano, e ne aveva perso uno (`billing_account_id`) — e ricopiava
//        il nome sul filo della data di fine (`data_al`), che ora e' `paramNames`
//        dello store. Un export che se li ricostruisce esporta un insieme DIVERSO
//        da quello a video appena se ne aggiunge uno, e nessuno se ne accorge
//        finche' qualcuno non confronta il file con la schermata.
function buildExportParams(format) {
  return { formato: format, ...store.paramsFiltro() }
}

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
      label: t('vendite.preventivi.pdf.label_scarica'),
      icon: MANAGE_ICONS.PDF,
      severity: 'primary',
      disabled: data.stato_codice_interno === 'DRAFT',
      tooltip: data.stato_codice_interno === 'DRAFT'
        ? t('vendite.preventivi.pdf.tooltip_lista_disabilitato')
        : t('vendite.preventivi.pdf.tooltip_lista'),
      command: () => onPdfClick(data),
    },
    {
      key: 'gestisci-note',
      label: t('vendite.preventivi.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => onNoteClick(data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.PREVENTIVO)

// Lista preventivi: ha filtro data_da con default standard (frontend-standards
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
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText class="app-filter-w-lg" v-model="searchText" :placeholder="t('vendite.preventivi.search_placeholder')"  />
          </template>
          <LookupSelect v-model="statoFilter" rel="config.stati_doc_preventivi" value-field="codice_interno"
            class="app-filter-w-md"
            :placeholder="t('vendite.preventivi.filtro_stato')" show-clear @change="onStatoChange"  />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            class="app-filter-w-md"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.preventivi.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <FiltroPeriodo :periodo="periodo" />
          <FiltroToggle
            v-model="mostraStorico"
            :label="t('vendite.preventivi.filtro_mostra_storico')"
            @change="onMostraStoricoChange"
          />
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

    <!-- Dialog lista PDF per il preventivo selezionato. Riusa il building
         block `PdfDocumentiSorgenteDialog`. -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialogVisible"
      :sorgente-code="SORGENTE_CODES.PREVENTIVO"
      :sorgente-id="pdfDialogPreventivo?.id ?? null"
      :emittente-fiscale-id="pdfDialogPreventivo?.emittente_fiscale_id ?? null"
      :title="pdfDialogPreventivo
        ? t('vendite.preventivi.pdf.dialog_title', { numero: pdfDialogPreventivo.numero })
        : ''"
    />

    <PreventivoNoteDrawer
      v-if="noteDrawerPreventivo?.id"
      v-model:visible="noteDrawerVisible"
      :preventivo-id="noteDrawerPreventivo.id"
    />
  </div>
</template>
