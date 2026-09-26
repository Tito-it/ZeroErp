<script setup>
// Scopo: Vista principale gestione articoli catalogo.
//        Drawer articolo + sub-drawer UoM/BoM/Note apribili da lista e da drawer.
import { ref, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useContextStore } from '../../stores/context'
import { useArticoliStore } from '../stores/articoli'
import ArticoliSearchTable from '../components/ArticoliSearchTable.vue'
import ArticoloDrawer from '../components/ArticoloDrawer.vue'
import ArticoloUomDrawer from '../components/ArticoloUomDrawer.vue'
import ArticoloBomDrawer from '../components/ArticoloBomDrawer.vue'
import ArticoloNoteDrawer from '../components/ArticoloNoteDrawer.vue'

const drawer = useDrawerState()
const store = useArticoliStore()
const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)
const ctx = useContextStore()
const route = useRoute()
useReadonlyMode(READONLY_DOMAINS.CATALOGO, READONLY_MODELS.ARTICOLO)

// Sub-drawer aperti dalla lista
const uomDrawerVisible = ref(false)
const uomArticoloId = ref(null)
const bomDrawerVisible = ref(false)
const bomArticoloId = ref(null)
const noteDrawerVisible = ref(false)
const noteArticoloId = ref(null)

watch(() => route.fullPath, () => {
  if (route.name === 'catalogo-articoli' && ctx.entitaId) {
    nextTick(() => drawer.editRow({ id: ctx.entitaId }, 'id'))
  }
}, { immediate: true })

function onManageUom(data) {
  uomArticoloId.value = data.id
  uomDrawerVisible.value = true
}
function onManageBom(data) {
  bomArticoloId.value = data.id
  bomDrawerVisible.value = true
}
function onManageNote(data) {
  noteArticoloId.value = data.id
  noteDrawerVisible.value = true
}
</script>

<template>
  <div class="app-page">
    <ArticoliSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @manage-uom="onManageUom"
      @manage-bom="onManageBom"
      @manage-note="onManageNote"
    />

    <ArticoloDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :articolo-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <!-- Sub-drawer aperti dalla lista -->
    <ArticoloUomDrawer
      :visible="uomDrawerVisible"
      @update:visible="v => uomDrawerVisible = v"
      :articolo-id="uomArticoloId"
    />
    <ArticoloBomDrawer
      :visible="bomDrawerVisible"
      @update:visible="v => bomDrawerVisible = v"
      :articolo-id="bomArticoloId"
    />
    <ArticoloNoteDrawer
      :visible="noteDrawerVisible"
      @update:visible="v => noteDrawerVisible = v"
      :articolo-id="noteArticoloId"
    />
  </div>
</template>
