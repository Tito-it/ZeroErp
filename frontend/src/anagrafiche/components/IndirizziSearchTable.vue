<script setup>
// Scopo: DataTable indirizzi dettaglio con ricerca, filtro comune e CRUD.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useIndirizziStore } from '../stores/indirizzi'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import ComuneAutocomplete from '../../core/components/ComuneAutocomplete.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import NewButton from '../../core/components/NewButton.vue'
import Tag from 'primevue/tag'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useIndirizziStore()
const { searchText, onPage, onSort, applyFilters, paginatorProps } = useSearchTable(store)

const comuneFilter = ref(null)

useTabFreshness(store, 'indirizzo')
onMounted(() => { store.fetchList() })

function onComuneChange(id) {
  comuneFilter.value = id
  store.filters.comune_id = id
  applyFilters()
}

function onRowClick(event) {
  emit('row-click', event.data)
}
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('indirizzi.search_indirizzo')"
        />
        <ComuneAutocomplete
          :model-value="comuneFilter"
          @update:model-value="onComuneChange"
        />
      </div>
      <NewButton :tooltip="t('indirizzi.nuovo_indirizzo')" @click="emit('new')" />
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
      data-key="indirizzo_dettaglio_id"
    >
      <Column field="indirizzo_normalizzato" :header="t('indirizzi.col_indirizzo')" sortable />
      <Column field="civico" :header="t('indirizzi.col_civico')" sortable>
        <template #body="{ data }">
          {{ data.civico }}{{ data.estensione_civico ? `/${data.estensione_civico}` : '' }}
        </template>
      </Column>
      <Column field="descrizione_comune" :header="t('indirizzi.col_comune')" sortable />
      <Column field="provincia" :header="t('indirizzi.col_provincia')" sortable />
      <Column field="cap" :header="t('indirizzi.col_cap')" sortable />
      <Column field="attivo" :header="t('indirizzi.col_attivo')" sortable>
        <template #body="{ data }">
          <Tag
            :value="data.attivo ? t('indirizzi.attivo') : t('indirizzi.non_attivo')"
            :severity="data.attivo ? 'success' : 'warn'"
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>
