<script setup>
// Scopo: Vista principale Gestione Fornitori.
// SearchTable + Drawer creazione/modifica + sotto-drawer contatti/indirizzi/conti da lista.
import { ref, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useContextStore } from '../../stores/context'
import { useFornitoriStore } from '../stores/fornitori'
import { TIPO_RUOLO, READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import FornitoriSearchTable from '../components/FornitoriSearchTable.vue'
import FornitoreDrawer from '../components/FornitoreDrawer.vue'
import SoggettoDrawer from '../components/SoggettoDrawer.vue'
import ContattiSoggettoDrawer from '../../core/components/ContattiSoggettoDrawer.vue'
import IndirizziSoggettoDrawer from '../../core/components/IndirizziSoggettoDrawer.vue'
import ContiBancariDrawer from '../../core/components/ContiBancariDrawer.vue'

const drawer = useDrawerState()
const store = useFornitoriStore()
const ctx = useContextStore()
const route = useRoute()
useReadonlyMode(READONLY_DOMAINS.ANAGRAFICHE, READONLY_MODELS.FORNITORE)

watch(() => route.fullPath, () => {
  if (route.name === 'anagrafiche-fornitori' && ctx.entitaId) {
    nextTick(() => drawer.editRow({ id: ctx.entitaId }, 'id'))
  }
}, { immediate: true })

// Sotto-drawer dalla lista
const soggettoDrawer = ref({ visible: false, soggettoId: null })
const contattiDrawer = ref({ visible: false, ruoloId: null })
const indirizziDrawer = ref({ visible: false, ruoloId: null })
const contiBancariDrawer = ref({ visible: false, ruoloId: null, ownerName: '' })

function onSoggetto(data) {
  soggettoDrawer.value = { visible: true, soggettoId: data.soggetto_id }
}
function onContatti(data) {
  contattiDrawer.value = { visible: true, ruoloId: data.soggetto_ruolo_id }
}
function onIndirizzi(data) {
  indirizziDrawer.value = { visible: true, ruoloId: data.soggetto_ruolo_id }
}
function onContiBancari(data) {
  contiBancariDrawer.value = {
    visible: true,
    ruoloId: data.soggetto_ruolo_id,
    ownerName: data.ragione_sociale_completa || ''
  }
}

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
    <FornitoriSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @soggetto="onSoggetto"
      @contatti="onContatti"
      @indirizzi="onIndirizzi"
      @conti-bancari="onContiBancari"
    />

    <FornitoreDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :fornitore-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <SoggettoDrawer
      :visible="soggettoDrawer.visible"
      @update:visible="v => soggettoDrawer.visible = v"
      mode="edit"
      :item-id="soggettoDrawer.soggettoId"
    />

    <ContattiSoggettoDrawer
      :visible="contattiDrawer.visible"
      @update:visible="v => contattiDrawer.visible = v"
      :soggetto-id="contattiDrawer.ruoloId"
      context="ruolo"
    />

    <IndirizziSoggettoDrawer
      :visible="indirizziDrawer.visible"
      @update:visible="v => indirizziDrawer.visible = v"
      :soggetto-id="indirizziDrawer.ruoloId"
      :tipo-ruolo-codice="TIPO_RUOLO.FORNITORE"
      context="ruolo"
    />

    <ContiBancariDrawer
      :visible="contiBancariDrawer.visible"
      @update:visible="v => contiBancariDrawer.visible = v"
      :owner-id="contiBancariDrawer.ruoloId"
      :owner-name="contiBancariDrawer.ownerName"
      context="ruolo"
    />
  </div>
</template>
