<script setup>
// Scopo: Vista admin categorie cliente (Amm. Software).
//        CRUD minimo: list + filtri + create + edit. No delete (soft via attivo).
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useCategorieClientiStore } from '../stores/categorieClienti'
import CategorieClientiSearchTable from '../components/CategorieClientiSearchTable.vue'
import CategoriaClienteDrawer from '../components/CategoriaClienteDrawer.vue'

const drawer = useDrawerState()
const store = useCategorieClientiStore()

useReadonlyMode('amm_software')

async function onDrawerSaved() {
  store.filters.offset = 0
  await store.fetchList()
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <CategorieClientiSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <CategoriaClienteDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
