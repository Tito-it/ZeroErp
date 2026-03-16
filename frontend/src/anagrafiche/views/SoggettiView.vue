<script setup>
// Scopo: vista principale Gestione Soggetti.
// SearchTable + Drawer per CRUD. Il refresh post-salvataggio
// e' gestito da useTabFreshness nel SearchTable.
import { useDrawerState } from '../../core/composables/useDrawerState'
import SoggettiSearchTable from '../components/SoggettiSearchTable.vue'
import SoggettoDrawer from '../components/SoggettoDrawer.vue'

const drawer = useDrawerState()
</script>

<template>
  <div class="app-page">
    <SoggettiSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <SoggettoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :item-id="drawer.state.itemId"
    />
  </div>
</template>
