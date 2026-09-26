<script setup>
// Scopo: DataTable toponomastica (colonna stato attivo). Wrapper su GeoSearchTable.
// Riusabile da: tab Toponomastica in IndirizziView, futuro gestione stradario.
import { useI18n } from 'vue-i18n'
import GeoSearchTable from './GeoSearchTable.vue'
import AttivoTag from '../../core/components/AttivoTag.vue'
import { useToponomasticaStore } from '../stores/toponomastica'
import { TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useToponomasticaStore()
const columns = [
  { field: 'descrizione', headerKey: 'indirizzi.col_descrizione' },
  { field: 'attivo', headerKey: 'indirizzi.col_attivo' },
]
</script>

<template>
  <GeoSearchTable
    :store="store"
    :columns="columns"
    :tab-entity="TAB_ENTITIES.TOPONOMASTICA"
    search-placeholder-key="indirizzi.search_toponomastica"
    new-tooltip-key="indirizzi.nuova_toponomastica"
    @row-click="emit('row-click', $event)"
    @new="emit('new')"
  >
    <template #cell-attivo="{ data }">
      <AttivoTag
        :active="data.attivo"
        :active-label="t('indirizzi.attivo')"
        :inactive-label="t('indirizzi.non_attivo')"
      />
    </template>
  </GeoSearchTable>
</template>
