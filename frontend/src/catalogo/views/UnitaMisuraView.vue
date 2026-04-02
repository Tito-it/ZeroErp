<script setup>
// Scopo: Vista principale gestione unita' di misura.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useUnitaMisuraStore } from '../stores/unitaMisura'
import UnitaMisuraSearchTable from '../components/UnitaMisuraSearchTable.vue'
import UnitaMisuraDrawer from '../components/UnitaMisuraDrawer.vue'

const drawer = useDrawerState()
const store = useUnitaMisuraStore()
useReadonlyMode('catalogo')

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
    <UnitaMisuraSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <UnitaMisuraDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :uom-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
