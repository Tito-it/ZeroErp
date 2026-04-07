<script setup>
// Scopo: pagina lista emittenti fiscali (admin only).
// Click riga -> apre EmittenteFiscaleDrawer in modifica sul tab Dati.
// Pulsanti riga BA/Utilities -> aprono il drawer principale gia' sul tab corretto.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliStore } from '../stores/emittentiFiscali'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import EmittenteFiscaleDrawer from '../components/EmittenteFiscaleDrawer.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import NewButton from '../../core/components/NewButton.vue'

// Indici tab del drawer (sincronizzati con l'ordine TabPanel in EmittenteFiscaleDrawer).
const TAB_INDEX = { DATI: 0, BILLING_ACCOUNT: 1, UTILITIES: 2 }

const { t } = useI18n()
const store = useEmittentiFiscaliStore()
const { searchText, applyFilters, reload, paginatorProps, onPage, onSort } = useSearchTable(store)
const drawer = useDrawerState()
const initialTab = ref(TAB_INDEX.DATI)

// Provider readonly: livello LETTURA disabilita i pulsanti di scrittura nei drawer figli.
const { isReadonly } = useReadonlyMode('amm_software')

useTabFreshness(store, 'emittente-fiscale')

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
  initialTab.value = TAB_INDEX.DATI
  drawer.openCreate()
}

function openEdit(row) {
  initialTab.value = TAB_INDEX.DATI
  drawer.editRow(row, 'id')
}

function openTabBA(row, event) {
  event.stopPropagation()
  initialTab.value = TAB_INDEX.BILLING_ACCOUNT
  drawer.editRow(row, 'id')
}

function openTabUtilities(row, event) {
  event.stopPropagation()
  initialTab.value = TAB_INDEX.UTILITIES
  drawer.editRow(row, 'id')
}
</script>

<template>
  <div class="app-page">
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
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
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
      <Column field="codice" :header="t('amm_emittenti_fiscali.col_codice')" sortable style="width: 140px;" />
      <Column field="descrizione" :header="t('amm_emittenti_fiscali.col_descrizione')" sortable />
      <Column field="ragione_sociale_completa" :header="t('amm_emittenti_fiscali.col_ragione_sociale')" sortable />
      <Column field="codice_fiscale" :header="t('amm_emittenti_fiscali.col_cf')" style="width: 160px;" />
      <Column field="partita_iva" :header="t('amm_emittenti_fiscali.col_piva')" style="width: 160px;" />
      <Column field="attivo" :header="t('amm_emittenti_fiscali.col_attivo')" sortable style="width: 110px;">
        <template #body="{ data }">
          <Badge
            :value="data.attivo ? t('amm.stato_attivo') : t('amm.stato_inattivo')"
            :severity="data.attivo ? 'success' : 'danger'"
          />
        </template>
      </Column>
      <Column v-if="!isReadonly" :header="t('amm.col_actions')" style="width: 110px;" frozen alignFrozen="right">
        <template #body="{ data }">
          <Button
            icon="pi pi-credit-card"
            text rounded size="small"
            class="app-manage-btn"
            v-tooltip.bottom="t('amm_emittenti_fiscali.action_ba')"
            @click="openTabBA(data, $event)"
          />
          <Button
            icon="pi pi-bolt"
            text rounded size="small"
            class="app-manage-btn"
            v-tooltip.bottom="t('amm_emittenti_fiscali.action_utilities')"
            @click="openTabUtilities(data, $event)"
          />
        </template>
      </Column>
    </DataTable>

    <EmittenteFiscaleDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :emittente-id="drawer.state.itemId"
      :initial-tab="initialTab"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
