<script setup>
// Scopo: DataTable paginata listini con search, filtro dominio e attivo.
// Pulsanti riga per accesso diretto a versioni e associazioni.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useListiniStore } from '../stores/listini'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { MANAGE_ICONS } from '../../core/constants'
import { dominioListinoSeverity } from '../../core/utils/severity'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'

const emit = defineEmits(['new', 'row-click', 'open-versioni', 'open-associazioni', 'test-resolver'])
const { t } = useI18n()
const store = useListiniStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'descrizione'
})

const dominioFilter = ref(null)
const dominioOptions = [
  { value: null, label: t('common.all') },
  { value: 'UTILITY', label: t('listini.dominio_utility') },
  { value: 'COMMERCIO', label: t('listini.dominio_commercio') }
]

const attivoFilter = ref(true)
const boolOptions = [
  { value: null, label: t('common.all') },
  { value: true, label: t('common.yes') },
  { value: false, label: t('common.no') }
]

function onDominioChange() {
  store.filters.dominio = dominioFilter.value
  applyFilters()
}

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, 'listino')
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('listini.search_placeholder')" />
        <Select v-model="dominioFilter" :options="dominioOptions" option-label="label" option-value="value"
          :placeholder="t('listini.filtro_dominio')" @change="onDominioChange" style="width: 150px;" />
        <Select v-model="attivoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" style="width: 120px;" />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-calculator" text severity="info"
          v-tooltip.bottom="t('listini.test_prezzo')" @click="emit('test-resolver')" />
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('listini.nuovo_listino')" @click="emit('new')" />
      </div>
    </div>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy removable-sort striped-rows scrollable scrollHeight="flex"
      class="app-datatable"
      @page="onPage" @sort="onSort" @row-click="onRowClick"
      selection-mode="single" data-key="id"
    >
      <Column field="codice" :header="t('listini.col_codice')" sortable style="width: 140px;" />
      <Column field="descrizione" :header="t('listini.col_descrizione')" sortable style="min-width: 200px;" />
      <Column field="dominio" :header="t('listini.col_dominio')" sortable style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.dominio" :severity="dominioListinoSeverity(data.dominio)" />
        </template>
      </Column>
      <Column field="versioni_count" :header="t('listini.col_versioni')" style="width: 80px;" />
      <Column field="associazioni_count" :header="t('listini.col_associazioni')" style="width: 90px;" />
      <Column field="attivo" :header="t('listini.col_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
      <Column :header="t('listini.col_gestione')" style="width: 100px;" frozen alignFrozen="right">
        <template #body="{ data }">
          <div class="flex gap-1" @click.stop>
            <Button :icon="MANAGE_ICONS.VERSIONI" text rounded size="small"
              class="app-manage-btn" v-tooltip.bottom="t('listini.tab_versioni')"
              @click="emit('open-versioni', data)" />
            <Button :icon="MANAGE_ICONS.ASSOCIAZIONI" text rounded size="small"
              class="app-manage-btn" v-tooltip.bottom="t('listini.tab_associazioni')"
              @click="emit('open-associazioni', data)" />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</template>
