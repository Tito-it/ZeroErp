<script setup>
// Scopo: Lista offerte commerciali configurabile (DEF-8). Migrazione 2026-06-03:
// <ListaConfigurabile codice="vendite.offerte"> con ritiro dinamico colonne
// (anti-scrollbar), personalizzazione colonne, export CSV/XLSX. Scaffolding
// (useSearchTable + ref lista + export + pageActions) centralizzato in
// useListaConfigurabilePage; qui restano filtri custom, slot e azioni di riga.
// Righe dalla vista canonica self-contained `vw_offerte_commerciali_lista`:
// cliente=`ragione_sociale_completa`, id.fiscale=`id_fiscale_univoco_cf_piva`,
// listino_codice + listino_versione_codice + is_scaduta materializzati in vista.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'

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
import OffertaNoteDrawer from './OffertaNoteDrawer.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { DATE_FORMAT, MANAGE_ICONS, TAB_ENTITIES, TIPO_RUOLO } from '../../../core/constants'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { statoOffertaSeverity } from '../../../core/utils/severity'
import { STATI_OFFERTA_SEGNALA_SCADENZA } from '../constants'
import { exportOfferte } from '../api/offerteApi'
import { useOfferteStore } from '../stores/offerte'

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
const { bindSelect, bindDate } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_codice_interno')
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da')
const { value: dataAlFilter, onChange: onDataAlChange } = bindDate('data_a')
// Toggle "mostra storico revisioni" (negazione del filtro store).
// mostraStorico=ON ⇔ solo_ultima_revisione=false. computed get/set per restare
// allineato al filtro reale anche se cambia altrove (reset, logout): single
// source of truth = store.
const mostraStorico = computed({
  get: () => !store.filters.solo_ultima_revisione,
  set: (val) => { store.filters.solo_ultima_revisione = !val },
})

// Params export: i filtri vivono in store.filters; `search` dal ref immediato.
// I filtri data BE si chiamano validita_dal_min/validita_dal_max (views_offerte).
function buildExportParams(format) {
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (store.filters.stato_codice_interno != null) p.stato_codice_interno = store.filters.stato_codice_interno
  if (store.filters.utility_id != null) p.utility_id = store.filters.utility_id
  if (store.filters.data_da) p.validita_dal_min = store.filters.data_da
  if (store.filters.data_a) p.validita_dal_max = store.filters.data_a
  p.solo_ultima_revisione = store.filters.solo_ultima_revisione ? 'true' : 'false'
  if (store.filters.order_by) {
    p.order_by = store.filters.order_by
    p.order_dir = store.filters.order_dir || 'desc'
  }
  return p
}

// Il setter del computed scrive gia' lo store; qui basta triggerare la fetch.
function onMostraStoricoChange() { applyFilters() }

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
        <div class="app-page-filters" :inert="perimetroBloccato">
          <InputText v-model="searchText" :placeholder="t('vendite.offerte.search_placeholder')" style="width: 260px;" />
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_offerte"
            value-field="codice_interno"
            :placeholder="t('vendite.offerte.filtro_stato')"
            show-clear
            style="width: 160px;"
            @change="onStatoChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.offerte.filtro_utility')"
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
            <ToggleSwitch v-model="mostraStorico" inputId="off-mostra-storico"
              @change="onMostraStoricoChange" />
            <label for="off-mostra-storico" style="font-size: 0.85rem; cursor: pointer;">
              {{ t('vendite.offerte.filtro_mostra_storico') }}
            </label>
          </div>
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
      sorgente-code="OFFERTA_COMMERCIALE"
      :sorgente-id="pdfDialogOfferta?.id ?? null"
      :title="pdfDialogOfferta
        ? t('vendite.offerte.pdf.dialog_title', { codice: pdfDialogOfferta.codice })
        : ''"
    />

    <OffertaNoteDrawer
      v-if="noteDrawerOfferta?.id"
      v-model:visible="noteDrawerVisible"
      :offerta-id="noteDrawerOfferta.id"
    />
  </div>
</template>
