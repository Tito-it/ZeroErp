<script setup>
// Scopo: DataTable codici postali con filtro comune. Wrapper su GeoSearchTable.
import { ref } from 'vue'
import GeoSearchTable from './GeoSearchTable.vue'
import ComuneAutocomplete from './ComuneAutocomplete.vue'
import { useCodiciPostaliStore } from '../../anagrafiche/stores/codiciPostali'
import { TAB_ENTITIES } from '../constants'

const emit = defineEmits(['row-click', 'new'])
const store = useCodiciPostaliStore()
const comuneFilter = ref(null)
const columns = [
  { field: 'codice', headerKey: 'indirizzi.col_cap' },
  { field: 'comune_descrizione', headerKey: 'indirizzi.col_comune' },
]

function onComuneChange(id, applyFilters) {
  comuneFilter.value = id
  store.filters.comune_id = id
  applyFilters()
}
</script>

<template>
  <GeoSearchTable
    :store="store"
    :columns="columns"
    :tab-entity="TAB_ENTITIES.CODICE_POSTALE"
    search-placeholder-key="indirizzi.search_cap"
    new-tooltip-key="indirizzi.nuovo_cap"
    default-sort-field="comune_descrizione"
    @row-click="emit('row-click', $event)"
    @new="emit('new')"
  >
    <template #filters="{ applyFilters }">
      <ComuneAutocomplete
        :model-value="comuneFilter"
        class="app-filter-w-lg"
        @update:model-value="id => onComuneChange(id, applyFilters)"
      />
    </template>
  </GeoSearchTable>
</template>
