<script setup>
// Scopo: Vista principale gestione articoli catalogo.
import { watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useContextStore } from '../../stores/context'
import { useArticoliStore } from '../stores/articoli'
import ArticoliSearchTable from '../components/ArticoliSearchTable.vue'
import ArticoloDrawer from '../components/ArticoloDrawer.vue'

const drawer = useDrawerState()
const store = useArticoliStore()
const ctx = useContextStore()
const route = useRoute()
useReadonlyMode('catalogo')

watch(() => route.fullPath, () => {
  if (route.name === 'catalogo-articoli' && ctx.entitaId) {
    nextTick(() => drawer.editRow({ id: ctx.entitaId }, 'id'))
  }
}, { immediate: true })

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
    <ArticoliSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <ArticoloDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :articolo-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
