<script setup>
// Scopo: DataTable stati (nazioni). Wrapper su GeoSearchTable.
import GeoSearchTable from './GeoSearchTable.vue'
import { useStatiStore } from '../../anagrafiche/stores/stati'
import { TAB_ENTITIES } from '../constants'

const emit = defineEmits(['row-click', 'new'])
const store = useStatiStore()
const columns = [
  { field: 'descrizione', headerKey: 'geo.col_descrizione' },
  { field: 'codice_iso2', headerKey: 'geo.col_iso2' },
  { field: 'codice_iso3', headerKey: 'geo.col_iso3' },
  { field: 'continente', headerKey: 'geo.col_continente' },
]
</script>

<template>
  <GeoSearchTable
    :store="store"
    :columns="columns"
    :tab-entity="TAB_ENTITIES.STATO"
    search-placeholder-key="geo.search_stato"
    new-tooltip-key="geo.nuovo_stato"
    @row-click="emit('row-click', $event)"
    @new="emit('new')"
  />
</template>
