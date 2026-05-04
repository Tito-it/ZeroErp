<script setup>
// Scopo: pagina lista emittenti fiscali (admin only).
// Click riga -> apre EmittenteFiscaleDrawer (anagrafica) in modifica.
// Pulsanti riga BA / Utilities -> aprono i drawer DEDICATI per la sotto-entita',
// senza passare dal drawer dati.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliStore } from '../stores/emittentiFiscali'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, TAB_ENTITIES, MANAGE_ICONS } from '../../core/constants'
import EmittenteFiscaleDrawer from '../components/EmittenteFiscaleDrawer.vue'
import EmittenteFiscaleBillingAccountDrawer from '../components/EmittenteFiscaleBillingAccountDrawer.vue'
import EmittenteFiscaleUtilitiesDrawer from '../components/EmittenteFiscaleUtilitiesDrawer.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Badge from 'primevue/badge'
import NewButton from '../../core/components/NewButton.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const { t } = useI18n()
const store = useEmittentiFiscaliStore()
const { searchText, applyFilters, reload, paginatorProps, onPage, onSort } = useSearchTable(store)

// Tre drawer indipendenti: anagrafica, BA mapping, utility matrix.
const drawer = useDrawerState()
const baDrawer = useDrawerState()
const utDrawer = useDrawerState()

// Provider readonly: livello LETTURA disabilita i pulsanti di scrittura nei drawer figli.
const { isReadonly, isBlocked } = useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)

useTabFreshness(store, TAB_ENTITIES.EMITTENTE_FISCALE)

const attivoFilter = ref(null)
const attivoOptions = [
  { label: t('amm.stato_all'), value: null },
  { label: t('amm.stato_attivo'), value: true },
  { label: t('amm.stato_inattivo'), value: false }
]

onMounted(() => { store.fetchList() })

function applyExtraFilters() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

function onDrawerSaved() {
  drawer.close()
  store.fetchList()
}

function openCreate() {
  drawer.openCreate()
}

function openEdit(row) {
  drawer.editRow(row, 'id')
}

function openBA(row, event) {
  event.stopPropagation()
  baDrawer.editRow(row, 'id')
}

function openUtilities(row, event) {
  event.stopPropagation()
  utDrawer.editRow(row, 'id')
}

// Scopo: azioni di riga emittente fiscale (sub-drawer BA + utilities).
function buildRowActions(data) {
  return [
    {
      key: 'ba',
      label: t('amm_emittenti_fiscali.action_ba'),
      icon: MANAGE_ICONS.BILLING_ACCOUNT,
      command: () => baDrawer.editRow(data, 'id'),
    },
    {
      key: 'utilities',
      label: t('amm_emittenti_fiscali.action_utilities'),
      icon: MANAGE_ICONS.UTILITY,
      command: () => utDrawer.editRow(data, 'id'),
    },
  ]
}
</script>

<template>
  <div class="app-page">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('amm_emittenti_fiscali.search_placeholder')"
        />
        <Select
          v-model="attivoFilter"
          :options="attivoOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amm.filter_stato')"
          @change="applyExtraFilters"
        />
      </div>
      <div class="app-page-actions">
        <ReadonlyBadge />
        <ReloadButton @click="reload" />
        <NewButton :tooltip="t('amm_emittenti_fiscali.new')" @click="openCreate" />
      </div>
    </div>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy
      removable-sort
      striped-rows
      scrollable
      scrollHeight="flex"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
      @row-click="(e) => openEdit(e.data)"
      selection-mode="single"
      data-key="id"
    >
      <Column field="codice" :header="t('amm_emittenti_fiscali.col_codice')" sortable style="width: 220px;" />
      <Column field="descrizione" :header="t('amm_emittenti_fiscali.col_descrizione')" sortable />
      <Column field="ragione_sociale_completa" :header="t('amm_emittenti_fiscali.col_ragione_sociale')" sortable />
      <Column field="partita_iva" :header="t('amm_emittenti_fiscali.col_piva')" style="width: 160px;" />
      <Column field="attivo" :header="t('amm_emittenti_fiscali.col_attivo')" sortable style="width: 110px;">
        <template #body="{ data }">
          <Badge
            :value="data.attivo ? t('amm.stato_attivo') : t('amm.stato_inattivo')"
            :severity="data.attivo ? 'success' : 'danger'"
          />
        </template>
      </Column>
      <Column v-if="!isReadonly" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false" frozen alignFrozen="right">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>
    </template>

    <EmittenteFiscaleDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :emittente-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <EmittenteFiscaleBillingAccountDrawer
      :visible="baDrawer.state.visible"
      @update:visible="v => baDrawer.state.visible = v"
      :emittente-id="baDrawer.state.itemId"
      :emittente-codice="baDrawer.state.itemData?.codice || ''"
      :emittente-ragione-sociale="baDrawer.state.itemData?.ragione_sociale_completa || ''"
      @close="baDrawer.close"
    />

    <EmittenteFiscaleUtilitiesDrawer
      :visible="utDrawer.state.visible"
      @update:visible="v => utDrawer.state.visible = v"
      :emittente-id="utDrawer.state.itemId"
      :emittente-codice="utDrawer.state.itemData?.codice || ''"
      :emittente-ragione-sociale="utDrawer.state.itemData?.ragione_sociale_completa || ''"
      :emittente-attivo="utDrawer.state.itemData?.attivo ?? true"
      @close="utDrawer.close"
    />
  </div>
</template>
