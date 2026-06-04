<script setup>
// Scopo: DataTable comuni (sola creazione, no row-click). Wrapper su GeoSearchTable.
// Riusabile da: tab Comuni in IndirizziView, futuro filtri clienti/fornitori.
import GeoSearchTable from './GeoSearchTable.vue'
import { useComuniStore } from '../../anagrafiche/stores/comuni'
import { TAB_ENTITIES } from '../constants'

const emit = defineEmits(['new'])
const store = useComuniStore()
const columns = [
  { field: 'descrizione', headerKey: 'indirizzi.col_comune' },
  { field: 'provincia_sigla', headerKey: 'indirizzi.col_provincia' },
  { field: 'regione_descrizione', headerKey: 'indirizzi.col_regione' },
]
</script>

<template>
  <GeoSearchTable
    :store="store"
    :columns="columns"
    :tab-entity="TAB_ENTITIES.COMUNE"
    search-placeholder-key="indirizzi.search_comune"
    new-tooltip-key="indirizzi.nuovo_comune"
    :row-clickable="false"
    @new="emit('new')"
  />
</template>
