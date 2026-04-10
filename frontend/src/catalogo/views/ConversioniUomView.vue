<script setup>
// Scopo: Vista principale gestione conversioni UoM.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useConversioniUomStore } from '../stores/conversioniUom'
import ConversioniUomSearchTable from '../components/ConversioniUomSearchTable.vue'
import ConversioneUomDrawer from '../components/ConversioneUomDrawer.vue'

const drawer = useDrawerState()
const store = useConversioniUomStore()
useReadonlyMode('catalogo', 'unita_misura')

async function onDrawerSaved(result) {
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
    <ConversioniUomSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <ConversioneUomDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :conv-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
