<script setup>
// Scopo: vista principale Gestione Soggetti.
// Se la ricerca universale ha selezionato un soggetto (contextStore),
// apre automaticamente il drawer in edit mode.
// Supporta apertura diretta drawer contatti/indirizzi dalla lista.
import { ref, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useContextStore } from '../../stores/context'
import SoggettiSearchTable from '../components/SoggettiSearchTable.vue'
import SoggettoDrawer from '../components/SoggettoDrawer.vue'
import ContattiSoggettoDrawer from '../../core/components/ContattiSoggettoDrawer.vue'
import IndirizziSoggettoDrawer from '../../core/components/IndirizziSoggettoDrawer.vue'
import ContiBancariDrawer from '../../core/components/ContiBancariDrawer.vue'

const drawer = useDrawerState()
const { isReadonly } = useReadonlyMode('anagrafiche')
const ctx = useContextStore()
const route = useRoute()

// Drawer contatti/indirizzi/conti bancari dalla lista
const contattiDrawer = ref({ visible: false, soggettoId: null })
const indirizziDrawer = ref({ visible: false, soggettoId: null, tipoDettaglioId: null })
const contiBancariDrawer = ref({ visible: false, soggettoId: null, ownerName: '' })

function onContatti(data) {
  contattiDrawer.value = { visible: true, soggettoId: data.id }
}

function onIndirizzi(data) {
  indirizziDrawer.value = {
    visible: true,
    soggettoId: data.id,
    tipoDettaglioId: data.tipo_soggetto_dettaglio_id,
  }
}

function onContiBancari(data) {
  contiBancariDrawer.value = {
    visible: true,
    soggettoId: data.id,
    ownerName: data.ragione_sociale_completa || '',
  }
}

// Se la ricerca universale ha selezionato un soggetto, apri il drawer in edit.
// Il filtro lista viene applicato automaticamente da useSearchTable (legge ctx.searchTerm).
watch(() => route.fullPath, () => {
  if (route.name === 'anagrafiche-soggetti' && ctx.soggettoId) {
    nextTick(() => drawer.editRow({ id: ctx.soggettoId }))
  }
}, { immediate: true })
</script>

<template>
  <div class="app-page">
    <SoggettiSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @contatti="onContatti"
      @indirizzi="onIndirizzi"
      @conti-bancari="onContiBancari"
    />

    <SoggettoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :item-id="drawer.state.itemId"
    />

    <ContattiSoggettoDrawer
      :visible="contattiDrawer.visible"
      @update:visible="v => contattiDrawer.visible = v"
      :soggetto-id="contattiDrawer.soggettoId"
    />

    <IndirizziSoggettoDrawer
      :visible="indirizziDrawer.visible"
      @update:visible="v => indirizziDrawer.visible = v"
      :soggetto-id="indirizziDrawer.soggettoId"
      :tipo-soggetto-dettaglio-id="indirizziDrawer.tipoDettaglioId"
    />

    <ContiBancariDrawer
      :visible="contiBancariDrawer.visible"
      @update:visible="v => contiBancariDrawer.visible = v"
      :owner-id="contiBancariDrawer.soggettoId"
      :owner-name="contiBancariDrawer.ownerName"
    />
  </div>
</template>
