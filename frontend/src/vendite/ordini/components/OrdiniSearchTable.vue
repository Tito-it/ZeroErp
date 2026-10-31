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
import InputText from 'primevue/inputtext'

import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import ListaConfigurabile from '../../../core/components/ListaConfigurabile.vue'
import FiltriLista from '../../../core/components/FiltriLista.vue'
import FiltroPeriodo from '../../../core/components/FiltroPeriodo.vue'
import LineagePraticaCell from '../../_shared/lineage/LineagePraticaCell.vue'
import LineageFaseTag from '../../_shared/lineage/LineageFaseTag.vue'
import LineageFrontieraChip from '../../_shared/lineage/LineageFrontieraChip.vue'
import ExportDialog from '../../../core/components/ExportDialog.vue'
import VenditeNoteDrawer from '../../_shared/note/VenditeNoteDrawer.vue'
import PdfDocumentiSorgenteDialog from '../../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { MANAGE_ICONS, TAB_ENTITIES, TIPO_RUOLO } from '../../../core/constants'
import { statoOrdineSeverity } from '../../../core/utils/severity'
import { exportOrdini } from '../api/ordiniApi'
import { PDF_MODE } from '../../../documenti/constants'
import { useOrdiniStore } from '../stores/ordini'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useOrdiniStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportOrdini,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'vendite.ordini.nuovo_ordine',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// --- Filtri custom (toolbar caller) — binding store via BB (B14) ---
const { bindSelect, bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_codice_interno')
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
// Il periodo e' UN filtro con due estremi: un binding, un componente.
const periodo = bindPeriodo()

// Scopo: i parametri dell'export = QUELLI DELLA LISTA a video, dalla sede
//        unica dello store (`paramsFiltro`: ricerca, filtri di dominio col nome
//        sul filo, ordinamento). ⛔ Fino al 2026-09-18 questo blocco ricostruiva i
//        filtri a mano. Un export che se li ricostruisce esporta un insieme
//        DIVERSO da quello a video appena se ne aggiunge uno, e nessuno se ne
//        accorge finche' qualcuno non confronta il file con la schermata.
function buildExportParams(format) {
  return { formato: format, ...store.paramsFiltro() }
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

// ── Sub-dialog PDF documenti generati + drawer note (azioni di riga) ──
const pdfDialogVisible = ref(false)
const pdfDialogOrdine = ref(null)
const noteDrawerVisible = ref(false)
const noteDrawerOrdine = ref(null)

// Flusso allineato a preventivi/contratti/offerte (§6 brief-ordini-stampa.md):
// dalla lista NON si fa anteprima/download diretto. In DRAFT (pdf_mode PREVIEW)
// l'azione e' disabilitata (anteprima solo dal drawer); dagli stati con PDF
// archiviato (pdf_mode ARCHIVE) apre `PdfDocumentiSorgenteDialog` con i
// documenti gia' generati alla conferma. La capability `pdf_mode` arriva
// data-driven dalla vista (`vw_ordini_lista`, colonna da config.stati_doc_ordini).
function onPdfClick(row) {
  if (!row?.id || row.pdf_mode !== PDF_MODE.ARCHIVE) return
  pdfDialogOrdine.value = row
  pdfDialogVisible.value = true
}

function onNoteClick(row) {
  if (!row?.id) return
  noteDrawerOrdine.value = row
  noteDrawerVisible.value = true
}

// Scopo: costruisce le azioni contestuali di riga. Modifica = click riga.
// Conferma/push vivono nel drawer (dove sono caricate le capability), non in
// lista: la lista resta consultazione + gestione documenti generati + note.
function buildRowActions(data) {
  const conDocumento = data.pdf_mode === PDF_MODE.ARCHIVE
  return [
    {
      key: 'documenti-pdf',
      label: t('vendite.ordini.pdf.label_scarica'),
      icon: MANAGE_ICONS.PDF,
      severity: 'primary',
      disabled: !conDocumento,
      tooltip: conDocumento
        ? t('vendite.ordini.pdf.tooltip_lista')
        : t('vendite.ordini.pdf.tooltip_lista_disabilitato'),
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

// Lista con filtro data_da default standard: auto-load al mount (lo store guard
// hasFilters considera data_da come filtro attivo).
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- Toolbar UNICA esterna (pattern lista standard). -->
      <div class="app-page-toolbar">
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('vendite.ordini.search_placeholder')"
            />
          </template>
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_ordini"
            value-field="codice_interno"
            class="app-filter-w-sm"
            :placeholder="t('vendite.ordini.filtro_stato')"
            show-clear
            @change="onStatoChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            class="app-filter-w-md"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.ordini.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <FiltroPeriodo :periodo="periodo" />
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

    <VenditeNoteDrawer
      v-if="noteDrawerOrdine?.id"
      v-model:visible="noteDrawerVisible"
      dominio="ordini"
      :id="noteDrawerOrdine.id"
      :emittente-fiscale-id="noteDrawerOrdine.emittente_fiscale_id ?? null"
    />

    <!-- Dialog lista PDF documenti generati per l'ordine selezionato. Riusa il
         building block `PdfDocumentiSorgenteDialog` (come preventivi/offerte). -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialogVisible"
      :sorgente-code="SORGENTE_CODES.ORDINE_VENDITA"
      :sorgente-id="pdfDialogOrdine?.id ?? null"
      :emittente-fiscale-id="pdfDialogOrdine?.emittente_fiscale_id ?? null"
      :title="pdfDialogOrdine
        ? t('vendite.ordini.pdf.dialog_title', { numero: pdfDialogOrdine.numero })
        : ''"
    />
  </div>
</template>
