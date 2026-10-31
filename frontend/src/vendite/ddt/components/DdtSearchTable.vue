<script setup>
// Scopo: Lista DDT di vendita configurabile. Nasce direttamente
// <ListaConfigurabile codice="vendite.ddt">: ritiro dinamico colonne
// (anti-scrollbar), personalizzazione colonne. Scaffolding (useSearchTable +
// ref lista + pageActions) centralizzato in useListaConfigurabilePage; qui
// restano filtri custom, slot e azioni di riga. Righe dalla vista canonica
// `vw_ddt_lista`: destinatario=`destinatario_denominazione`,
// id.fiscale=`id_fiscale_univoco_cf_piva`, ba_codice, causale/aspetto/vettore/
// mittente, ordine_origine_numero. Clone di OrdiniSearchTable (§D-4).
//
// Export lista CSV/XLSX operativo (endpoint BE `/vendite/ddt/export/`, DEF-1) e
// azioni di riga "Documenti PDF" + "Gestisci note" (gemelli offerte/contratti/
// ordini): la lista replica le gestioni del drawer. Il PDF di riga apre il
// building block `PdfDocumentiSorgenteDialog` (documenti generati all'emissione);
// disabilitato in DRAFT (documento generato solo dall'emissione DRAFT→EMESSO).
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
import LineagePraticaCell from '../../_shared/lineage/LineagePraticaCell.vue'
import LineageFaseTag from '../../_shared/lineage/LineageFaseTag.vue'
import LineageFrontieraChip from '../../_shared/lineage/LineageFrontieraChip.vue'
import ExportDialog from '../../../core/components/ExportDialog.vue'
import PdfDocumentiSorgenteDialog from '../../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import VenditeNoteDrawer from '../../_shared/note/VenditeNoteDrawer.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { MANAGE_ICONS, TAB_ENTITIES, TIPO_RUOLO } from '../../../core/constants'
import { statoDdtSeverity } from '../../../core/utils/severity'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { exportDdt } from '../api/ddtApi'
import { STATO_DDT } from '../constants'
import { useDdtStore } from '../stores/ddt'
import FiltroPeriodo from '../../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../../core/components/FiltriLista.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useDdtStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportDdt,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'vendite.ddt.nuovo_ddt',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// --- Filtri custom (toolbar caller) — binding store via BB ---
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

// ── Sub-dialog PDF + drawer note (azioni di riga) ──
const pdfDialogVisible = ref(false)
const pdfDialogDdt = ref(null)
const noteDrawerVisible = ref(false)
const noteDrawerDdt = ref(null)

function onPdfClick(row) {
  // Documenti PDF disponibili solo dopo l'emissione (il documento definitivo si
  // genera alla transizione DRAFT→EMESSO). In DRAFT l'azione e' disabled.
  if (!row || row.stato_codice_interno === STATO_DDT.DRAFT) return
  pdfDialogDdt.value = row
  pdfDialogVisible.value = true
}
function onNoteClick(row) {
  if (!row?.id) return
  noteDrawerDdt.value = row
  noteDrawerVisible.value = true
}

// Scopo: azioni contestuali di riga. Modifica = click riga. Emissione/cambio
// stato/push vivono nel drawer (dove sono caricate le capability), non in lista:
// la lista resta consultazione + gestione documenti generati + note (gemelli
// offerte/contratti/ordini).
function buildRowActions(data) {
  const isBozza = data.stato_codice_interno === STATO_DDT.DRAFT
  return [
    {
      key: 'documenti-pdf',
      label: t('vendite.ddt.pdf.label_scarica'),
      icon: MANAGE_ICONS.PDF,
      severity: 'primary',
      disabled: isBozza,
      tooltip: isBozza
        ? t('vendite.ddt.pdf.tooltip_lista_disabilitato')
        : t('vendite.ddt.pdf.tooltip_lista'),
      command: () => onPdfClick(data),
    },
    {
      key: 'gestisci-note',
      label: t('vendite.ddt.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => onNoteClick(data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.DDT)

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
            <InputText class="app-filter-w-lg" v-model="searchText" :placeholder="t('vendite.ddt.search_placeholder')"  />
          </template>
          <LookupSelect
            v-model="statoFilter"
            class="app-filter-w-md"
            rel="config.stati_doc_ddt"
            value-field="codice_interno"
            :placeholder="t('vendite.ddt.filtro_stato')"
            show-clear
            @change="onStatoChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            class="app-filter-w-md"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.ddt.filtro_utility')"
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
        codice="vendite.ddt"
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
        <!-- Numero: NULL in DRAFT (assegnato solo a EMESSO) → mostra "—". -->
        <template #cell-numero="{ data }">
          {{ data.numero || '—' }}
        </template>

        <!-- Stato: Tag severity data-driven (statoDdtSeverity). -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoDdtSeverity(data.stato_codice_interno)" />
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

    <!-- Dialog lista PDF documenti generati per il DDT selezionato. Riusa il
         building block `PdfDocumentiSorgenteDialog` (come ordini/offerte). -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialogVisible"
      :sorgente-code="SORGENTE_CODES.DDT_VENDITA"
      :sorgente-id="pdfDialogDdt?.id ?? null"
      :emittente-fiscale-id="pdfDialogDdt?.emittente_fiscale_id ?? null"
      :title="pdfDialogDdt
        ? t('vendite.ddt.pdf.dialog_title', { numero: pdfDialogDdt.numero })
        : ''"
    />

    <VenditeNoteDrawer
      v-if="noteDrawerDdt?.id"
      v-model:visible="noteDrawerVisible"
      dominio="ddt"
      :id="noteDrawerDdt.id"
      :emittente-fiscale-id="noteDrawerDdt.emittente_fiscale_id ?? null"
    />
  </div>
</template>
