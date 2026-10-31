<script setup>
// Scopo: Lista offerte commerciali configurabile (DEF-8). Migrazione 2026-06-03:
// <ListaConfigurabile codice="vendite.offerte"> con ritiro dinamico colonne
// (anti-scrollbar), personalizzazione colonne, export CSV/XLSX. Scaffolding
// (useSearchTable + ref lista + export + pageActions) centralizzato in
// useListaConfigurabilePage; qui restano filtri custom, slot e azioni di riga.
// Righe dalla vista canonica self-contained `vw_offerte_commerciali_lista`:
// cliente=`ragione_sociale_completa`, id.fiscale=`id_fiscale_univoco_cf_piva`,
// listino_codice + listino_versione_codice + is_scaduta materializzati in vista.
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
import FiltroToggle from '../../../core/components/FiltroToggle.vue'
import PdfDocumentiSorgenteDialog from '../../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import VenditeNoteDrawer from '../../_shared/note/VenditeNoteDrawer.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { MANAGE_ICONS, TAB_ENTITIES, TIPO_RUOLO } from '../../../core/constants'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { statoOffertaSeverity } from '../../../core/utils/severity'
import { STATI_OFFERTA_SEGNALA_SCADENZA } from '../constants'
import { exportOfferte } from '../api/offerteApi'
import { useOfferteStore } from '../stores/offerte'
import FiltroPeriodo from '../../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../../core/components/FiltriLista.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useOfferteStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportOfferte,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'vendite.offerte.nuova_offerta',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'validita_dal', defaultSortOrder: 'desc' },
})

// --- Filtri custom (toolbar caller) — binding store via BB (B14) ---
const { bindSelect, bindToggle, bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_codice_interno')
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
//        filtri a mano, e ne aveva persi due (`billing_account_id`, `listino_id`)
//        — e ricopiava il nome sul filo delle date (`validita_dal_min/max`), che
//        ora e' `paramNames` dello store. Un export che se li ricostruisce
//        esporta un insieme DIVERSO da quello a video appena se ne aggiunge uno,
//        e nessuno se ne accorge finche' qualcuno non confronta il file con la
//        schermata.
function buildExportParams(format) {
  return { formato: format, ...store.paramsFiltro() }
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

// ── Sub-dialog PDF + drawer note (azioni di riga) ──
const pdfDialogVisible = ref(false)
const pdfDialogOfferta = ref(null)
const noteDrawerVisible = ref(false)
const noteDrawerOfferta = ref(null)

function onPdfClick(row) {
  // Documenti PDF disponibili solo dopo l'emissione (la fn DB genera_documento
  // richiede l'offerta EMESSA). In BOZZA l'azione e' disabled.
  if (!row || row.stato_codice_interno === 'BOZZA') return
  pdfDialogOfferta.value = row
  pdfDialogVisible.value = true
}
function onNoteClick(row) {
  if (!row?.id) return
  noteDrawerOfferta.value = row
  noteDrawerVisible.value = true
}

// Scopo: costruisce le azioni contestuali di riga. Modifica = click riga.
function buildRowActions(data) {
  return [
    {
      key: 'documenti-pdf',
      label: t('vendite.offerte.pdf.label_scarica'),
      icon: MANAGE_ICONS.PDF,
      severity: 'primary',
      disabled: data.stato_codice_interno === 'BOZZA',
      tooltip: data.stato_codice_interno === 'BOZZA'
        ? t('vendite.offerte.pdf.tooltip_lista_disabilitato')
        : t('vendite.offerte.pdf.tooltip_lista'),
      command: () => onPdfClick(data),
    },
    {
      key: 'gestisci-note',
      label: t('vendite.offerte.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => onNoteClick(data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.OFFERTA_COMMERCIALE)

// Lista con filtro data_da default standard (frontend-standards "Filtro data
// standard"): auto-load al mount, lo store guard hasFilters considera data_da
// come filtro attivo.
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
            <InputText class="app-filter-w-lg" v-model="searchText" :placeholder="t('vendite.offerte.search_placeholder')"  />
          </template>
          <LookupSelect
            v-model="statoFilter"
            class="app-filter-w-md"
            rel="config.stati_doc_offerte"
            value-field="codice_interno"
            :placeholder="t('vendite.offerte.filtro_stato')"
            show-clear
            @change="onStatoChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            class="app-filter-w-md"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.offerte.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <FiltroPeriodo :periodo="periodo" />
          <FiltroToggle
            v-model="mostraStorico"
            :label="t('vendite.offerte.filtro_mostra_storico')"
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
        codice="vendite.offerte"
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
        <!-- Listino: codice + suffisso versione (cella composita). -->
        <template #cell-listino_codice="{ data }">
          {{ data.listino_codice }}
          <span v-if="data.listino_versione_codice" style="color: var(--app-text-muted);">
            · v{{ data.listino_versione_codice }}
          </span>
        </template>

        <!-- Stato: Tag severity + badge "scaduta" condizionale. -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoOffertaSeverity(data.stato_codice_interno)" />
          <Tag
            v-if="data.is_scaduta && STATI_OFFERTA_SEGNALA_SCADENZA.includes(data.stato_codice_interno)"
            :value="t('vendite.offerte.badge_scaduta')"
            severity="warn"
            style="margin-left: 0.25rem;"
          />
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

    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialogVisible"
      :sorgente-code="SORGENTE_CODES.OFFERTA_COMMERCIALE"
      :sorgente-id="pdfDialogOfferta?.id ?? null"
      :emittente-fiscale-id="pdfDialogOfferta?.emittente_fiscale_id ?? null"
      :title="pdfDialogOfferta
        ? t('vendite.offerte.pdf.dialog_title', { codice: pdfDialogOfferta.codice })
        : ''"
    />

    <VenditeNoteDrawer
      v-if="noteDrawerOfferta?.id"
      v-model:visible="noteDrawerVisible"
      dominio="offerte"
      :id="noteDrawerOfferta.id"
      :emittente-fiscale-id="noteDrawerOfferta.emittente_fiscale_id ?? null"
    />
  </div>
</template>
