<script setup>
// Scopo: DataTable province. Wrapper su GeoSearchTable.
import GeoSearchTable from './GeoSearchTable.vue'
import { useProvinceStore } from '../../anagrafiche/stores/province'
import { TAB_ENTITIES } from '../constants'

const emit = defineEmits(['row-click', 'new'])
const store = useProvinceStore()
const columns = [
  { field: 'sigla', headerKey: 'geo.col_sigla' },
  { field: 'descrizione', headerKey: 'geo.col_descrizione' },
  { field: 'regione_descrizione', headerKey: 'geo.col_regione' },
]
</script>

<template>
  <GeoSearchTable
    :store="store"
    :columns="columns"
    :tab-entity="TAB_ENTITIES.PROVINCIA"
    search-placeholder-key="geo.search_provincia"
    new-tooltip-key="geo.nuova_provincia"
    @row-click="emit('row-click', $event)"
    @new="emit('new')"
  />
</template>
