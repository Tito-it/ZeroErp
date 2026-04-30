<script setup>
// Scopo: DataTable contratti v5 con filtri (stato, utility, ambito, BA, date).
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContrattiStore } from '../stores/contratti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { displayDate, toDateString } from '../../core/utils/date'
import { statoContrattoSeverity } from '../../core/utils/severity'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import LookupSelect from '../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import NewButton from '../../core/components/NewButton.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TIPO_RUOLO, MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['new', 'row-click', 'open-righe'])
const { t } = useI18n()
const store = useContrattiStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'valido_dal'
})

const statoFilter = ref(null)
const utilityFilter = ref(null)
const ambitoFilter = ref(null)
const dataDaFilter = ref(store.filters.data_da ? new Date(store.filters.data_da) : null)
const dataAFilter = ref(null)
const scadenzaMeseFilter = ref(null)

const ambitoOptions = computed(() => [
  { value: null, label: t('common.all') },
  { value: 'COMMODITY', label: t('contratti.ambito_commodity') },
  { value: 'COMMERCIO', label: t('contratti.ambito_commercio') },
])

function onStatoChange() { store.filters.stato_doc_contratto_id = statoFilter.value; applyFilters() }
function onUtilityChange() { store.filters.utility_id = utilityFilter.value; applyFilters() }
function onAmbitoChange() { store.filters.ambito = ambitoFilter.value; applyFilters() }
function onDataDaChange(val) {
  if (val) {
    store.filters.data_da = toDateString(val)
  } else {
    // Ripristina default anno-1: la lista ha sempre bisogno di un floor.
    const defaultVal = `${new Date().getFullYear() - 1}-01-01`
    dataDaFilter.value = new Date(defaultVal)
    store.filters.data_da = defaultVal
  }
  applyFilters()
}
function onDataAChange(val) {
  store.filters.data_a = val ? toDateString(val) : null
  applyFilters()
}
function onScadenzaMeseChange(val) {
  if (val) {
    const d = val instanceof Date ? val : new Date(val)
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    store.filters.scadenza_mese = `${yyyy}-${mm}`
  } else {
    store.filters.scadenza_mese = null
  }
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

// Scopo: costruisce le azioni contestuali di riga per il menu kebab.
// La modifica del contratto e' gia' disponibile cliccando la riga.
function buildRowActions(data) {
  return [
    {
      key: 'gestisci-righe',
      label: t('contratti.gestisci_righe'),
      icon: MANAGE_ICONS.CONTRATTI,
      command: () => emit('open-righe', data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.CONTRATTO)
// data_da ha sempre un valore default (anno-1): la lista si carica subito,
// non serve attendere che l'utente digiti una ricerca.
onMounted(() => {
  store.fetchList()
})
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('contratti.search_placeholder')" style="width: 320px;" />
        <LookupSelect
          v-model="statoFilter"
          rel="config.stati_doc_contratti"
          :placeholder="t('contratti.filtro_stato')"
          show-clear
          @change="onStatoChange"
        />
        <UtilityPerRuoloSelect
          v-model="utilityFilter"
          :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
          :placeholder="t('contratti.filtro_utility')"
          show-clear
          @change="onUtilityChange"
        />
        <Select
          v-model="ambitoFilter"
          :options="ambitoOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('contratti.filtro_ambito')"
          @change="onAmbitoChange"
          style="min-width: 160px;"
        />
        <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
          date-format="dd/mm/yy" show-icon show-button-bar style="width: 150px;"
          @update:modelValue="onDataDaChange" />
        <DatePicker v-model="dataAFilter" :placeholder="t('common.data_a')"
          date-format="dd/mm/yy" show-icon show-button-bar style="width: 150px;"
          @update:modelValue="onDataAChange" />
        <DatePicker v-model="scadenzaMeseFilter" :placeholder="t('contratti.filtro_scadenza_mese')"
          view="month" date-format="mm/yy" show-icon show-button-bar style="width: 160px;"
          :min-date="new Date()"
          @update:modelValue="onScadenzaMeseChange" />
      </div>
      <div class="app-page-actions">
        <ReadonlyBadge />
        <ReloadButton @click="reload" />
        <NewButton :tooltip="t('contratti.nuovo_contratto')" @click="emit('new')" />
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
      @row-click="onRowClick"
      selection-mode="single"
      data-key="id"
    >
      <Column field="numero" :header="t('contratti.col_numero')" sortable style="width: 140px;" />
      <Column field="ba_codice" :header="t('contratti.col_ba_codice')" sortable style="width: 120px;" />
      <Column field="ba_ragione_sociale" :header="t('contratti.col_ba')" sortable style="width: 220px;" />
      <Column field="utility_codice" :header="t('contratti.col_utility')" sortable style="width: 100px;" />
      <Column field="ambito" :header="t('contratti.col_ambito')" sortable style="width: 120px;" />
      <Column field="categoria_cliente_snapshot_codice" :header="t('contratti.col_categoria_cliente')" sortable style="width: 120px;">
        <template #body="{ data }">{{ data.categoria_cliente_snapshot_codice || '—' }}</template>
      </Column>
      <Column field="listino_codice" :header="t('contratti.col_listino')" sortable style="width: 160px;">
        <template #body="{ data }">{{ data.listino_codice || '—' }}</template>
      </Column>
      <Column field="valido_dal" :header="t('contratti.col_valido_dal')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
      </Column>
      <Column field="valido_al" :header="t('contratti.col_valido_al')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.valido_al) }}</template>
      </Column>
      <Column field="data" :header="t('contratti.col_data')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data) }}</template>
      </Column>
      <Column field="stato_descrizione" :header="t('contratti.col_stato')" sortable style="width: 110px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoContrattoSeverity(data.stato_codice)" />
        </template>
      </Column>
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
