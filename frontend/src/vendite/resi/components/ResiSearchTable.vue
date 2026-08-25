<script setup>
// Scopo: Lista resi di vendita configurabile. Nasce direttamente
// <ListaConfigurabile codice="vendite.resi"> (seed DB id 9): ritiro dinamico
// colonne + personalizzazione. Scaffolding centralizzato in
// useListaConfigurabilePage; qui restano filtri custom e slot. Righe dalla
// vista canonica `vw_resi_lista` (destinatario, ba_codice, id fiscale, DDT di
// origine, emittente). Clone ridotto di DdtSearchTable (brief §11): NIENTE
// azione "Nuovo" (il reso nasce SOLO dal pannello nel drawer DDT), filtrata via.
// Export CSV/XLSX operativo (endpoint BE `/vendite/resi/export/`, DEF-1).
// Dal 2026-08-25 e' la SESTA SORELLA delle liste documento: colonne di
// genealogia (pratica, fase, transito) dal seed + i tre slot lineage.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import ListaConfigurabile from '../../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../../core/components/ExportDialog.vue'
import LineagePraticaCell from '../../_shared/lineage/LineagePraticaCell.vue'
import LineageFaseTag from '../../_shared/lineage/LineageFaseTag.vue'
import LineageFrontieraChip from '../../_shared/lineage/LineageFrontieraChip.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { DATE_FORMAT, TAB_ENTITIES } from '../../../core/constants'
import { statoResoSeverity } from '../../../core/utils/severity'
import { exportResi } from '../api/resiApi'
import { useResiStore } from '../stores/resi'

const emit = defineEmits(['row-click'])
const { t } = useI18n()
const store = useResiStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm,
} = useListaConfigurabilePage(store, {
  exportFn: exportResi,
  getExportParams: (fmt) => buildExportParams(fmt),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// Niente "Nuovo": il reso nasce dal DDT consegnato. Non serve filtrare —
// lo scaffolding include l'azione solo se riceve `onNew`.

// Params export: filtri da store.filters + search dal ref immediato + sort
// corrente. Il BE rispetta colonne visibili/ordine/permessi (DEF-1).
function buildExportParams(format) {
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (store.filters.stato_codice_interno != null) p.stato_codice_interno = store.filters.stato_codice_interno
  if (store.filters.billing_account_id != null) p.billing_account_id = store.filters.billing_account_id
  if (store.filters.data_da) p.data_da = store.filters.data_da
  if (store.filters.data_a) p.data_a = store.filters.data_a
  if (store.filters.order_by) {
    p.order_by = store.filters.order_by
    p.order_dir = store.filters.order_dir || 'desc'
  }
  return p
}

// --- Filtri custom (toolbar caller) — binding store via BB ---
const { bindSelect, bindDate } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_codice_interno')
const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da')
const { value: dataAlFilter, onChange: onDataAlChange } = bindDate('data_a')

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

useTabFreshness(store, TAB_ENTITIES.RESO)

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
        <div class="app-page-filters" :inert="perimetroBloccato">
          <InputText v-model="searchText" :placeholder="t('vendite.resi.search_placeholder')" style="width: 260px;" />
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_reso"
            value-field="codice_interno"
            :placeholder="t('vendite.resi.filtro_stato')"
            show-clear
            :filter="false"
            style="width: 160px;"
            @change="onStatoChange"
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
        codice="vendite.resi"
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
        <!-- Numero: NULL in DRAFT (assegnato solo a CONFERMATO) → mostra "—". -->
        <template #cell-numero="{ data }">
          {{ data.numero || '—' }}
        </template>

        <!-- Stato: Tag severity data-driven (statoResoSeverity). -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoResoSeverity(data.stato_codice_interno)" />
        </template>

        <!-- Colonne lineage: pratica cliccabile, fase, chip transito. Stessi
             tre slot delle cinque sorelle — il seed (colonne 549/550/551 su
             lista 9, 2026-08-25) porta le colonne, ma senza QUESTI slot il BB
             renderebbe il valore grezzo: `fase` come testo al posto del Tag e
             la frontiera come numero nudo al posto del chip.
             ⭐ Su un reso il chip transito e' la risposta a «questo reso e'
             gia' stato accreditato, e con quale documento»: la frontiera di un
             reso accreditato e' la nota di credito (arco S, 20260825-19). -->
        <template #cell-pratica="{ data }">
          <LineagePraticaCell :pratica-id="data.pratica_id" :pratica-numero="data.pratica_numero" :n-pratiche="data.n_pratiche" />
        </template>
        <template #cell-fase="{ data }">
          <LineageFaseTag :fase="data.fase" />
        </template>
        <template #cell-transito="{ data }">
          <LineageFrontieraChip :is-transitato="data.is_transitato" :tipo-codice="data.frontiera_tipo_codice"
            :codice="data.frontiera_codice" :stato="data.frontiera_stato_codice_interno"
            :fase="data.frontiera_fase" :n-attivi="data.n_discendenti_attivi" />
        </template>
      </ListaConfigurabile>
    </template>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />
  </div>
</template>
