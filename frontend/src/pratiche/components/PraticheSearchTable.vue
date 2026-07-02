<script setup>
// Scopo: DataTable paginata pratiche con search, filtro stato, priorita' e data.
// I campi display (stato_descrizione, soggetto_display, ecc.) arrivano dal backend via JOIN.
// I lookup servono solo per popolare i filtri Select.
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePraticheStore } from '../stores/pratiche'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { displayDate, toDateString } from '../../core/utils/date'
import { statoPraticaSeverity, prioritaPraticaSeverity } from '../../core/utils/severity'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import LookupSelect from '../../core/components/LookupSelect.vue'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = usePraticheStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'data_apertura',
  defaultSortOrder: -1
})

// Init dallo store (persistente nella sessione, userScoped): al rientro in
// dashboard i Select devono riflettere i filtri ancora attivi sulla lista
// (stesso pattern di dataDaFilter; prima stato/priorita ripartivano null →
// lista filtrata ma Select visivamente vuoti).
const statoFilter = ref(store.filters.stato ?? null)
const prioritaFilter = ref(store.filters.priorita_id ?? null)
// Filtro tipo prestazione: preimpostabile dal deep-link della home launcher
// (tile "Comincia" → dashboard filtrata sul tipo). Il watch tiene il Select
// allineato quando il deep-link cambia il filtro a componente GIA' montato:
// sotto KeepAlive la dashboard viene ri-attivata senza remount, quindi
// l'init a setup-time da solo non basta.
const tipoPrestazioneFilter = ref(store.filters.tipo_prestazione_id ?? null)
watch(() => store.filters.tipo_prestazione_id, v => { tipoPrestazioneFilter.value = v ?? null })
// Lente di contesto D1 (workflow v2): solo pratiche interne (senza soggetto).
const soloInterneFilter = ref(store.filters.solo_interne || false)

// Filtro data sempre attivo: default inizio mese precedente (dal store)
const dataDaFilter = ref(store.filters.data_da ? new Date(store.filters.data_da + 'T00:00:00') : null)
const dataAFilter = ref(null)
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: reload,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('pratiche.nuova_pratica'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

function onStatoChange() {
  // value-field="codice": il BE filtra per codice_interno (param `stato`);
  // per gli stati pratiche codice e codice_interno coincidono (seed).
  store.filters.stato = statoFilter.value
  applyFilters()
}

function onPrioritaChange() {
  store.filters.priorita_id = prioritaFilter.value
  applyFilters()
}

function onTipoPrestazioneChange() {
  store.filters.tipo_prestazione_id = tipoPrestazioneFilter.value
  applyFilters()
}

function onSoloInterneChange() {
  store.filters.solo_interne = soloInterneFilter.value
  applyFilters()
}

function onDataDaChange() {
  store.filters.data_da = dataDaFilter.value ? toDateString(dataDaFilter.value) : null
  applyFilters()
}

function onDataAChange() {
  store.filters.data_a = dataAFilter.value ? toDateString(dataAFilter.value) : null
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, TAB_ENTITIES.PRATICA)

// Scopo: calcolo dinamico altezza scroll DataTable.
// Desktop (>=1280px): calcola altezza dal viewport reale meno area flussi.
// Mobile/tablet (<1280px): niente scroll interno, la pagina scrolla.
const tableContainer = ref(null)
const tableScrollHeight = ref(null)

function recalcScrollHeight() {
  if (window.innerWidth < 1280) {
    // Mobile/tablet: niente scroll interno DataTable, scrolla il container padre
    tableScrollHeight.value = null
    return
  }
  if (!tableContainer.value) return
  const rect = tableContainer.value.getBoundingClientRect()
  const available = window.innerHeight - rect.top - 100 - 240
  tableScrollHeight.value = Math.max(available, 150) + 'px'
}

// Lista eager: carica subito col filtro data sempre attivo (default inizio
// mese precedente impostato dallo store).
onMounted(() => {
  store.fetchList()
  recalcScrollHeight()
  window.addEventListener('resize', recalcScrollHeight)
})
onUnmounted(() => { window.removeEventListener('resize', recalcScrollHeight) })
</script>

<template>
  <div ref="tableContainer" class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('pratiche.search_placeholder')"
        />
        <LookupSelect
          v-model="statoFilter"
          rel="config.stati_pratiche"
          value-field="codice"
          :placeholder="t('pratiche.filtro_stato')"
          show-clear
          @change="onStatoChange"
        />
        <LookupSelect
          v-model="prioritaFilter"
          rel="config.priorita_pratiche"
          :placeholder="t('pratiche.filtro_priorita')"
          show-clear
          @change="onPrioritaChange"
        />
        <LookupSelect
          v-model="tipoPrestazioneFilter"
          rel="pratiche.tipi_prestazione"
          :placeholder="t('pratiche.filtro_tipo_prestazione')"
          show-clear
          @change="onTipoPrestazioneChange"
        />
        <DatePicker
          v-model="dataDaFilter"
          :placeholder="t('common.data_da')"
          date-format="dd/mm/yy"
          show-icon
          show-button-bar
          style="width: 150px;"
          @date-select="onDataDaChange"
          @clear-click="onDataDaChange"
        />
        <DatePicker
          v-model="dataAFilter"
          :placeholder="t('common.data_a')"
          date-format="dd/mm/yy"
          show-icon
          show-button-bar
          style="width: 150px;"
          @date-select="onDataAChange"
          @clear-click="onDataAChange"
        />
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <ToggleSwitch v-model="soloInterneFilter" inputId="pratiche-solo-interne"
            @change="onSoloInterneChange" />
          <label for="pratiche-solo-interne" style="font-size: 0.85rem; cursor: pointer;">
            {{ t('pratiche.filtro_solo_interne') }}
          </label>
        </div>
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy
      removable-sort
      striped-rows
      :scrollable="!!tableScrollHeight"
      :scrollHeight="tableScrollHeight || undefined"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      selection-mode="single"
      data-key="id"
    >
      <Column field="codice" :header="t('pratiche.col_codice')" sortable style="width: 140px;" />
      <Column field="tipo_prestazione_descrizione" :header="t('pratiche.col_tipo_prestazione')" sortable style="width: 160px;" />
      <Column field="soggetto_display" :header="t('pratiche.col_soggetto')" sortable style="width: 200px;" />
      <Column field="stato_descrizione" :header="t('pratiche.col_stato')" sortable style="width: 110px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoPraticaSeverity(data.stato_codice_interno)" />
        </template>
      </Column>
      <Column field="priorita_descrizione" :header="t('pratiche.col_priorita')" sortable style="width: 110px;">
        <template #body="{ data }">
          <Tag v-if="data.priorita_descrizione" :value="data.priorita_descrizione" :severity="prioritaPraticaSeverity(data.priorita_codice_interno)" />
        </template>
      </Column>
      <Column field="risorsa_umana_display" :header="t('pratiche.col_assegnata_a')" sortable style="width: 160px;" />
      <Column field="data_scadenza" :header="t('pratiche.col_data_scadenza')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_scadenza) }}</template>
      </Column>
      <Column field="data_apertura" :header="t('pratiche.col_data_apertura')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_apertura) }}</template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
