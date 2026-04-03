<script setup>
// Scopo: Vista principale gestione preventivi vendita.
import { useDrawerState } from '../../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../../core/composables/useReadonlyMode'
import { usePreventiviStore } from '../stores/preventivi'
import PreventiviList from '../components/PreventiviList.vue'
import PreventiviDrawer from '../components/PreventiviDrawer.vue'

const drawer = useDrawerState()
const store = usePreventiviStore()
useReadonlyMode('vendite')

async function onDrawerSaved(result) {
  store.filters.offset = 0
  if (store.hasSearched) await store.fetchList()
  if (result && result.id && drawer.state.mode === 'create') {
    drawer.editRow({ id: result.id }, 'id')
  } else {
    drawer.close()
  }
}
</script>

<template>
  <div class="app-page">
    <PreventiviList
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <PreventiviDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :preventivo-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
