<script setup>
// Scopo: Vista admin matrice anagrafiche.categorie_clienti_listini (Amm. Software).
//        Pricing v5 - STADIO 2 resolver (categoria x utility x emittente x
//        classe_utenza opz -> listino con variazione opzionale).
// Pattern: copia 1:1 di UtilitiesTipiRuoloListView.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { useCategorieClientiListiniStore } from '../stores/categorieClientiListini'
import CategorieClientiListiniSearchTable from '../components/CategorieClientiListiniSearchTable.vue'
import CategoriaClienteListinoDrawer from '../components/CategoriaClienteListinoDrawer.vue'

const drawer = useDrawerState()
const store = useCategorieClientiListiniStore()

// Provider readonly del dominio Amm. Software: i drawer figli ne ereditano
// lo stato (stesso pattern di UtilitiesTipiRuoloListView).
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)

async function onDrawerSaved() {
  store.filters.offset = 0
  await store.fetchList()
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <CategorieClientiListiniSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <CategoriaClienteListinoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
