<script setup>
// Scopo: vista principale Gestione Clienti.
// SearchTable + Drawer creazione/visualizzazione.
// Sotto-drawer indirizzi e conti bancari dalla lista (come SoggettiView).
import { ref } from 'vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useClientiStore } from '../stores/clienti'
import ClientiSearchTable from '../components/ClientiSearchTable.vue'
import ClienteDrawer from '../components/ClienteDrawer.vue'
import ContattiSoggettoDrawer from '../../core/components/ContattiSoggettoDrawer.vue'
import IndirizziSoggettoDrawer from '../../core/components/IndirizziSoggettoDrawer.vue'
import ContiBancariDrawer from '../../core/components/ContiBancariDrawer.vue'

const drawer = useDrawerState()
const store = useClientiStore()
useReadonlyMode('anagrafiche')

// Sotto-drawer dalla lista
const contattiDrawer = ref({ visible: false, ruoloId: null, utilityId: null })
const indirizziDrawer = ref({ visible: false, ruoloId: null, utilityId: null })
const contiBancariDrawer = ref({ visible: false, ruoloId: null, ownerName: '' })

function onContatti(data) {
  contattiDrawer.value = { visible: true, ruoloId: data.soggetto_ruolo_id, utilityId: data.utility_id }
}

function onIndirizzi(data) {
  indirizziDrawer.value = { visible: true, ruoloId: data.soggetto_ruolo_id, utilityId: data.utility_id }
}

function onContiBancari(data) {
  contiBancariDrawer.value = {
    visible: true,
    ruoloId: data.soggetto_ruolo_id,
    ownerName: data.ragione_sociale_completa || '',
    utilityId: data.utility_id,
  }
}

// Scopo: Dopo salvataggio, riapre in edit se era creazione (per gestire contatti/indirizzi/banca).
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
    <ClientiSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @contatti="onContatti"
      @indirizzi="onIndirizzi"
      @conti-bancari="onContiBancari"
    />

    <ClienteDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :cliente-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <ContattiSoggettoDrawer
      :visible="contattiDrawer.visible"
      @update:visible="v => contattiDrawer.visible = v"
      :soggetto-id="contattiDrawer.ruoloId"
      :utility-id="contattiDrawer.utilityId"
      context="ruolo"
    />

    <IndirizziSoggettoDrawer
      :visible="indirizziDrawer.visible"
      @update:visible="v => indirizziDrawer.visible = v"
      :soggetto-id="indirizziDrawer.ruoloId"
      :utility-id="indirizziDrawer.utilityId"
      context="ruolo"
    />

    <ContiBancariDrawer
      :visible="contiBancariDrawer.visible"
      @update:visible="v => contiBancariDrawer.visible = v"
      :owner-id="contiBancariDrawer.ruoloId"
      :owner-name="contiBancariDrawer.ownerName"
      :utility-id="contiBancariDrawer.utilityId"
      context="ruolo"
    />
  </div>
</template>
