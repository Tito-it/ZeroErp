<script setup>
// Scopo: Vista admin matrice config.utilities_tipi_ruolo (Amm. Software).
//        Lista filtrabile + drawer create/edit + tab "Utilizzo" lato drawer.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { useUtilitiesTipiRuoloStore } from '../stores/utilitiesTipiRuolo'
import UtilitiesTipiRuoloSearchTable from '../components/UtilitiesTipiRuoloSearchTable.vue'
import UtilityTipoRuoloDrawer from '../components/UtilityTipoRuoloDrawer.vue'

const drawer = useDrawerState()
const store = useUtilitiesTipiRuoloStore()

// Provider readonly del dominio Amm. Software: i drawer figli ne ereditano lo stato.
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)

async function onDrawerSaved() {
  store.filters.offset = 0
  await store.fetchList()
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <UtilitiesTipiRuoloSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <UtilityTipoRuoloDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
