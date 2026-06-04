<script setup>
// Scopo: DataTable regioni. Wrapper su GeoSearchTable.
import GeoSearchTable from './GeoSearchTable.vue'
import { useRegioniStore } from '../../anagrafiche/stores/regioni'
import { TAB_ENTITIES } from '../constants'

const emit = defineEmits(['row-click', 'new'])
const store = useRegioniStore()
const columns = [
  { field: 'descrizione', headerKey: 'geo.col_descrizione' },
  { field: 'stato_descrizione', headerKey: 'geo.col_stato' },
]
</script>

<template>
  <GeoSearchTable
    :store="store"
    :columns="columns"
    :tab-entity="TAB_ENTITIES.REGIONE"
    search-placeholder-key="geo.search_regione"
    new-tooltip-key="geo.nuova_regione"
    @row-click="emit('row-click', $event)"
    @new="emit('new')"
  />
</template>
