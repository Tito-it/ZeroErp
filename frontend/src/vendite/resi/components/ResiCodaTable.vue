<script setup>
// Scopo: Coda di lavoro resi (righe reso CONFERMATE), promossa a lista
//        configurabile standard. Due varianti via prop `coda`: 'accreditare'
//        (righe a credito, predisposizione slice nota di credito) e
//        'riconsegnare' (righe per ri-consegna con copertura pendente, colonne
//        resa/ri-consegnata/residua + stato derivato).
//
//        Migrata da DataTable raw a <ListaConfigurabile> (config DB
//        `vendite.resi_da_accreditare` / `vendite.resi_da_riconsegnare`, id
//        10/11): personalizzazione colonne + export CSV/XLSX + paginatore in
//        alto, allineata al pattern lista standard (memoria
//        feedback_lista_pattern_standard). Scaffolding via
//        useListaConfigurabilePage (search/sort/page + export dialog +
//        pageActions). Grana RIGA: dataKey=`resi_riga_id`; l'azione "apri reso"
//        usa `reso_id` (diverso dal PK di riga). Le due code sono code di
//        lavoro: nessun default temporale (lo store carica sempre il pendente).
//        Click riga / azione -> apre il reso nel drawer.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import ListaConfigurabile from '../../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../../core/components/ExportDialog.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { DATE_FORMAT, MANAGE_ICONS } from '../../../core/constants'
import { formatNumber } from '../../../core/utils/format'
import { statoRiconsegnaSeverity } from '../../../core/utils/severity'
import { exportDaAccreditare, exportDaRiconsegnare } from '../api/resiApi'
import {
  useResiCodaAccreditareStore,
  useResiCodaRiconsegnareStore,
} from '../stores/resiCoda'

const props = defineProps({
  coda: {
    type: String,
    required: true,
    validator: (v) => ['accreditare', 'riconsegnare'].includes(v),
  },
})
const emit = defineEmits(['apri-reso'])

const { t } = useI18n()
const isBlocked = useInjectBlocked()

// Risoluzione statica per variante (la prop `coda` e' fissa per istanza:
// ResiView monta un componente per tab).
const isRiconsegna = props.coda === 'riconsegnare'
const store = isRiconsegna
  ? useResiCodaRiconsegnareStore()
  : useResiCodaAccreditareStore()
const listaCodice = isRiconsegna
  ? 'vendite.resi_da_riconsegnare'
  : 'vendite.resi_da_accreditare'
const exportFn = isRiconsegna ? exportDaRiconsegnare : exportDaAccreditare

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  exportFn,
  getExportParams: (fmt) => buildExportParams(fmt),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// Le code non hanno "Nuovo" (il reso nasce dal DDT consegnato): si filtra
// l'azione standard dello scaffolding, restano reload/personalizza/export.
const codaPageActions = computed(
  () => pageActions.value.filter((a) => a.key !== 'new'),
)

// --- Filtri custom (toolbar caller): date opzionali, NESSUN default (coda). ---
const { bindDate } = useStoreFilterBindings(store, applyFilters)
const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da')
const { value: dataAlFilter, onChange: onDataAlChange } = bindDate('data_a')

// Params export: filtri da store.filters + search dal ref immediato + sort
// corrente. Il BE rispetta colonne visibili/ordine/permessi (DEF-1).
function buildExportParams(format) {
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (store.filters.data_da) p.data_da = store.filters.data_da
  if (store.filters.data_a) p.data_a = store.filters.data_a
  if (store.filters.order_by) {
    p.order_by = store.filters.order_by
    p.order_dir = store.filters.order_dir || 'desc'
  }
  return p
}

// `<ListaConfigurabile>` emette `data` direttamente. Apertura reso via reso_id
// (grana RIGA: il PK di riga e' resi_riga_id, il target azione e' reso_id).
function onRowClick(data) { emit('apri-reso', data.reso_id) }

function buildRowActions(data) {
  return [
    {
      key: 'apri-reso',
      label: t('vendite.resi.coda_apri_reso'),
      icon: MANAGE_ICONS.INSPECT,
      severity: 'primary',
      command: () => emit('apri-reso', data.reso_id),
    },
  ]
}

const searchPlaceholder = computed(() =>
  isRiconsegna
    ? t('vendite.resi.coda_search_riconsegnare')
    : t('vendite.resi.coda_search_accreditare'),
)

onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- Toolbar UNICA esterna (pattern lista standard). -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="searchText" :placeholder="searchPlaceholder" style="width: 260px;" />
          <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
            :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
            @date-select="onDataDaChange" @clear-click="onDataDaChange" />
          <DatePicker v-model="dataAlFilter" :placeholder="t('common.data_a')"
            :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
            @date-select="onDataAlChange" @clear-click="onDataAlChange" />
        </div>
        <PageActionsBar :actions="codaPageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <ListaConfigurabile
        ref="listaRef"
        :codice="listaCodice"
        data-key="resi_riga_id"
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
        <template #cell-reso_numero="{ data }">
          {{ data.reso_numero || '—' }}
        </template>

        <!-- Coda accrediti: quantita' (formato numerico centralizzato). -->
        <template #cell-qta_operativa="{ data }">
          {{ formatNumber(data.qta_operativa) }}
        </template>
        <template #cell-quantita="{ data }">
          {{ formatNumber(data.quantita) }}
        </template>

        <!-- Coda ri-consegne: copertura resa/ri-consegnata/residua. -->
        <template #cell-qta_resa="{ data }">
          {{ formatNumber(data.qta_resa) }}
        </template>
        <template #cell-qta_riconsegnata="{ data }">
          {{ formatNumber(data.qta_riconsegnata) }}
        </template>
        <template #cell-qta_residua="{ data }">
          {{ formatNumber(data.qta_residua) }}
        </template>

        <!-- Stato ri-consegna derivato: Tag severity data-driven. -->
        <template #cell-stato_riconsegna="{ data }">
          <Tag :value="t(`vendite.resi.riconsegna_stato.${data.stato_riconsegna}`)"
            :severity="statoRiconsegnaSeverity(data.stato_riconsegna)" />
        </template>

        <template #actions="{ data, compact }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" :force-compact="compact" />
        </template>

        <!-- Empty-state onesto: mostrato solo dopo il primo fetch riuscito
             (hasSearched), così non lampeggia durante il caricamento. -->
        <template #empty>
          <div v-if="store.hasSearched" class="app-empty-state">
            {{ t(isRiconsegna ? 'vendite.resi.riconsegna_nessuna_riga' : 'common.no_results') }}
          </div>
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
