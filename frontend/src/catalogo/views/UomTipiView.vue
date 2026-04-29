<script setup>
// Scopo: Vista principale gestione tipologie UoM.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useUomTipiStore } from '../stores/uomTipi'
import UomTipiSearchTable from '../components/UomTipiSearchTable.vue'
import UomTipoDrawer from '../components/UomTipoDrawer.vue'

const drawer = useDrawerState()
const store = useUomTipiStore()
useReadonlyMode(READONLY_DOMAINS.CATALOGO, READONLY_MODELS.UOM_TIPI)

async function onDrawerSaved(result) {
  store.filters.offset = 0
  await store.fetchList()
  if (result && result.id && drawer.state.mode === 'create') {
    drawer.editRow({ id: result.id }, 'id')
  } else {
    drawer.close()
  }
}
</script>

<template>
  <div class="app-page">
    <UomTipiSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <UomTipoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :tipo-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
