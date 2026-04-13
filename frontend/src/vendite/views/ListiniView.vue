<script setup>
// Scopo: Vista principale gestione listini vendite.
// Orchestra: lista listini con expansion versioni inline + drawer testata listino,
// drawer associazioni, drawer righe prezzo (VersioneDrawer), drawer create versione,
// dialog test resolver prezzo. Cache versioni invalidata sui salvataggi.
import { ref } from 'vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useListiniStore } from '../stores/listini'
import ListiniSearchTable from '../components/ListiniSearchTable.vue'
import ListinoDrawer from '../components/ListinoDrawer.vue'
import ListinoAssociazioniDrawer from '../components/ListinoAssociazioniDrawer.vue'
import VersioneDrawer from '../components/VersioneDrawer.vue'
import VersioneFormDrawer from '../components/VersioneFormDrawer.vue'
import CloneVersioneDrawer from '../components/CloneVersioneDrawer.vue'
import TestResolverDialog from '../components/TestResolverDialog.vue'

const drawer = useDrawerState()
const store = useListiniStore()
useReadonlyMode('vendite')

// Drawer associazioni
const associazioniVisible = ref(false)
const associazioniListinoId = ref(null)

// Drawer righe prezzo (VersioneDrawer)
const versioneDrawerVisible = ref(false)
const versioneSelezionata = ref(null)
const versioneListinoId = ref(null)

// Drawer create nuova versione (VersioneFormDrawer)
const nuovaVersioneVisible = ref(false)
const nuovaVersioneListino = ref(null)

// Drawer clone versione (CloneVersioneDrawer)
const cloneDrawerVisible = ref(false)
const cloneSourceVersione = ref(null)
const cloneSourceListino = ref(null)

// Test resolver
const resolverVisible = ref(false)

async function onDrawerSaved(result) {
  store.filters.offset = 0
  await store.fetchList()
  if (result && result.id && drawer.state.mode === 'create') {
    drawer.editRow({ id: result.id }, 'id')
  } else {
    drawer.close()
  }
}

function onOpenAssociazioni(data) {
  associazioniListinoId.value = data.id
  associazioniVisible.value = true
}

async function onAssociazioniSaved() {
  // Refresh lista per aggiornare il count associazioni nella riga.
  await store.fetchList()
}

const versioneListinoDescrizione = ref('')
const versioneListinoUtilityId = ref(null)

function onOpenRighe(versione, listino) {
  versioneSelezionata.value = versione
  versioneListinoId.value = listino.id
  versioneListinoDescrizione.value = listino.descrizione || listino.codice || ''
  versioneListinoUtilityId.value = listino.utility_id ?? null
  versioneDrawerVisible.value = true
}

async function onRigheClose() {
  versioneDrawerVisible.value = false
  // Dopo modifica righe, le righe_count della versione cambiano: rinfresca le versioni del listino.
  if (versioneListinoId.value) {
    await store.invalidateVersioniListino(versioneListinoId.value)
  }
  versioneSelezionata.value = null
  versioneListinoId.value = null
}

function onOpenNuovaVersione(listino) {
  nuovaVersioneListino.value = listino
  nuovaVersioneVisible.value = true
}

async function onNuovaVersioneSaved({ listinoId }) {
  // Una nuova versione cambia il versioni_count del listino: refresh lista
  // (che farà a sua volta preload delle versioni e aprirà l'expansion).
  if (listinoId) {
    await store.invalidateVersioniListino(listinoId)
  }
  await store.fetchList()
}

function onOpenClonaVersione(versione, listino) {
  cloneSourceVersione.value = versione
  cloneSourceListino.value = listino
  cloneDrawerVisible.value = true
}

async function onClonaVersioneSaved({ listinoId }) {
  // Il clone aggiunge una nuova versione BOZZA: invalida cache versioni del
  // listino e refresh della lista per aggiornare il versioni_count.
  if (listinoId) {
    await store.invalidateVersioniListino(listinoId)
  }
  await store.fetchList()
}
</script>

<template>
  <div class="app-page">
    <ListiniSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @open-associazioni="onOpenAssociazioni"
      @open-righe="onOpenRighe"
      @open-nuova-versione="onOpenNuovaVersione"
      @open-clona-versione="onOpenClonaVersione"
      @test-resolver="resolverVisible = true"
    />

    <ListinoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :listino-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
      @open-associazioni="onOpenAssociazioni"
    />

    <ListinoAssociazioniDrawer
      :visible="associazioniVisible"
      @update:visible="v => associazioniVisible = v"
      :listino-id="associazioniListinoId"
      @saved="onAssociazioniSaved"
    />

    <VersioneDrawer v-if="versioneSelezionata"
      :visible="versioneDrawerVisible"
      @update:visible="v => { if (!v) onRigheClose() }"
      :listino-id="versioneListinoId"
      :listino-descrizione="versioneListinoDescrizione"
      :listino-utility-id="versioneListinoUtilityId"
      :versione="versioneSelezionata"
    />

    <VersioneFormDrawer
      :visible="nuovaVersioneVisible"
      @update:visible="v => nuovaVersioneVisible = v"
      :listino="nuovaVersioneListino"
      @saved="onNuovaVersioneSaved"
    />

    <CloneVersioneDrawer
      :visible="cloneDrawerVisible"
      @update:visible="v => cloneDrawerVisible = v"
      :listino="cloneSourceListino"
      :source-versione="cloneSourceVersione"
      @cloned="onClonaVersioneSaved"
    />

    <TestResolverDialog v-if="resolverVisible"
      :visible="resolverVisible"
      @update:visible="v => resolverVisible = v" />
  </div>
</template>
