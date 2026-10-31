<script setup>
// Scopo: Vista principale gestione listini vendite.
// Orchestra: lista listini + drawer listino (dati e tab «Versioni»), drawer
// righe prezzo (VersioneDrawer), drawer create versione, drawer clone, dialog
// test resolver prezzo. Il tab «Versioni» chiede i drawer delle versioni con
// un evento; quando salvano, si ricaricano il tab e la lista listini
// (conteggio versioni, badge delle scadenze). Dal 2026-10-31: prima le
// versioni erano la riga espansa della lista, con una cache nello store.
import { ref } from 'vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useListiniStore } from '../stores/listini'
import ListiniSearchTable from '../components/ListiniSearchTable.vue'
import ListinoDrawer from '../components/ListinoDrawer.vue'
import VersioneDrawer from '../components/VersioneDrawer.vue'
import VersioneFormDrawer from '../components/VersioneFormDrawer.vue'
import CloneVersioneDrawer from '../components/CloneVersioneDrawer.vue'
import TestResolverDialog from '../components/TestResolverDialog.vue'

const drawer = useDrawerState()
const store = useListiniStore()
const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)
// Permessi: area `vendite` + oggetto `listino`, come le rotte `vendite/listini/…`
// del BE (brief-db-be-fe-catalogo-oggetti-permessi §3.3).
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.LISTINO)

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

const versioneListinoDescrizione = ref('')
const versioneListinoCodice = ref('')
const versioneListinoUtilityId = ref(null)

// Il drawer listino: il suo tab «Versioni» si ricarica dopo i drawer delle
// versioni.
const listinoDrawerRef = ref(null)
// La lista listini: il badge delle scadenze si rilegge da solo coi filtri, ma
// a filtri fermi lo cambiano le versioni (un successore toglie un listino) e
// il listino salvato (attivo/spento): glielo si chiede qui (`ricaricaBadge`).
const searchTableRef = ref(null)
async function versioniCambiate() {
  listinoDrawerRef.value?.ricaricaVersioni()
  searchTableRef.value?.ricaricaBadge()
  await store.fetchList()
}

// Il tab «Versioni» ha fatto un verbo (attiva, chiudi, elimina): lista e badge.
// (Il dettaglio del listino lo riallinea il drawer da se'.)
async function onVersioniCambiateDalDrawer() {
  searchTableRef.value?.ricaricaBadge()
  await store.fetchList()
}

async function onListinoSaved(result) {
  searchTableRef.value?.ricaricaBadge()
  await onDrawerSaved(result)
}

function onOpenRighe(versione, listino) {
  versioneSelezionata.value = versione
  versioneListinoId.value = listino.id
  versioneListinoCodice.value = listino.codice || ''
  versioneListinoDescrizione.value = listino.descrizione || listino.codice || ''
  versioneListinoUtilityId.value = listino.utility_id ?? null
  versioneDrawerVisible.value = true
}

async function onRigheClose() {
  versioneDrawerVisible.value = false
  // Dopo modifica righe, le righe_count della versione cambiano.
  listinoDrawerRef.value?.ricaricaVersioni()
  versioneSelezionata.value = null
  versioneListinoId.value = null
  versioneListinoCodice.value = ''
  versioneListinoDescrizione.value = ''
  versioneListinoUtilityId.value = null
}

function onOpenNuovaVersione(listino) {
  nuovaVersioneListino.value = listino
  nuovaVersioneVisible.value = true
}

// Una nuova versione cambia il versioni_count del listino (e puo' essere il
// successore che toglie il listino dalle scadenze).
async function onNuovaVersioneSaved() {
  await versioniCambiate()
}

function onOpenClonaVersione(versione, listino) {
  cloneSourceVersione.value = versione
  cloneSourceListino.value = listino
  cloneDrawerVisible.value = true
}

// Il clone aggiunge una nuova versione BOZZA: come una nuova versione.
async function onClonaVersioneSaved() {
  await versioniCambiate()
}
</script>

<template>
  <div class="app-page">
    <ListiniSearchTable
      ref="searchTableRef"
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @test-resolver="resolverVisible = true"
    />

    <ListinoDrawer
      ref="listinoDrawerRef"
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :listino-id="drawer.state.itemId"
      @saved="onListinoSaved"
      @cancelled="drawer.close"
      @open-righe="onOpenRighe"
      @open-nuova-versione="onOpenNuovaVersione"
      @open-clona-versione="onOpenClonaVersione"
      @versioni-cambiate="onVersioniCambiateDalDrawer"
    />

    <VersioneDrawer v-if="versioneSelezionata"
      :visible="versioneDrawerVisible"
      @update:visible="v => { if (!v) onRigheClose() }"
      :listino-id="versioneListinoId"
      :listino-codice="versioneListinoCodice"
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
