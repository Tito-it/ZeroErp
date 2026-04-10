<script setup>
// Scopo: Vista admin matrice config.tipi_ruolo_tipi_indirizzo (Amm. Software).
import { useTipiRuoloTipiIndirizzoStore } from '../stores/tipiRuoloTipiIndirizzo'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import TipiRuoloTipiIndirizzoSearchTable from '../components/TipiRuoloTipiIndirizzoSearchTable.vue'
import TipoRuoloTipoIndirizzoDrawer from '../components/TipoRuoloTipoIndirizzoDrawer.vue'

const store = useTipiRuoloTipiIndirizzoStore()
useReadonlyMode('amm_software')
const drawer = useDrawerState()

async function onSaved() {
  store.filters.offset = 0
  await store.fetchList()
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <TipiRuoloTipiIndirizzoSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />
    <TipoRuoloTipoIndirizzoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      @saved="onSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
