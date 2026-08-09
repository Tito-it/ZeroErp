<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
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
import Select from 'primevue/select'

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
import { labelOrCode } from '../../../core/utils/i18nLabel'
import {
  etichettaAccreditoSeverity,
  statoRiconsegnaSeverity,
} from '../../../core/utils/severity'
import { ETICHETTA_ACCREDITO } from '../constants'
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

const { t, te } = useI18n()
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

// Le code non hanno "Nuovo" (il reso nasce dal DDT consegnato): lo
// scaffolding omette l'azione da sé, non ricevendo `onNew`.

// --- Filtri custom (toolbar caller): date opzionali, NESSUN default (coda). ---
const { bindDate, bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da')
const { value: dataAlFilter, onChange: onDataAlChange } = bindDate('data_a')

// Filtro etichetta accredito (solo coda accrediti, forma contatore): DOVUTA =
// lavoro arretrato, FACOLTATIVA = opzione dell'operatore (DL-26 — la scelta
// "emetto una nota?" si esercita da qui, quindi le facoltative devono restare
// visibili, non solo filtrate via).
// ⚠️ Le ETICHETTE a schermo dicono «Accredito dovuto / facoltativo», non «NC»
// (allineamento 2026-08-09): DL-24 impone di nominare il FATTO e non il
// rimedio, perche' lo strumento — nota di credito o altro — non e' ancora
// definito e l'etichetta non deve pre-deciderlo. I CODICI restano
// DOVUTA/FACOLTATIVA: sono colonna della vista DB `vw_resi_da_accreditare`.
const { value: etichettaFilter, onChange: onEtichettaChange } = bindSelect('etichetta')
const etichettaOptions = computed(() => [
  { value: null, label: t('vendite.resi.coda_etichetta_tutte') },
  ...Object.values(ETICHETTA_ACCREDITO).map((et) => ({
    value: et,
    label: etichettaLabel(et),
  })),
])

// Decodifica fail-visible (pattern labelOrCode): un'etichetta futura fuori
// vocabolario mostra il codice grezzo, mai la chiave i18n letterale.
function etichettaLabel(et) {
  return labelOrCode(t, te, `vendite.resi.coda_etichetta.${et}`, et)
}

// Params export: filtri da store.filters + search dal ref immediato + sort
// corrente. Il BE rispetta colonne visibili/ordine/permessi (DEF-1).
function buildExportParams(format) {
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (store.filters.data_da) p.data_da = store.filters.data_da
  if (store.filters.data_a) p.data_a = store.filters.data_a
  if (store.filters.etichetta) p.etichetta = store.filters.etichetta
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
          <Select
            v-if="!isRiconsegna"
            v-model="etichettaFilter"
            :options="etichettaOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('vendite.resi.coda_etichetta_tutte')"
            style="width: 170px;"
            @change="onEtichettaChange"
          />
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

        <!-- Coda accrediti, forma contatore: il conto della partita
             (tenuti/fatturati) e l'accredito dovuto (l'informazione centrale:
             «fatturata per 10, tenuta 7 → accredito 3»). -->
        <template #cell-accredito_dovuto="{ data }">
          <strong>{{ formatNumber(data.accredito_dovuto) }}</strong>
        </template>
        <template #cell-tenuti="{ data }">
          {{ formatNumber(data.tenuti) }}
        </template>
        <template #cell-fatturati="{ data }">
          {{ formatNumber(data.fatturati) }}
        </template>
        <template #cell-etichetta="{ data }">
          <Tag :value="etichettaLabel(data.etichetta)"
            :severity="etichettaAccreditoSeverity(data.etichetta)" />
        </template>

        <!-- ddt_numero nullable (forma contatore: aggancio partita via
             ordine, il join al DDT e' LEFT): mai stringa vuota. -->
        <template #cell-ddt_numero="{ data }">
          {{ data.ddt_numero || '—' }}
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
