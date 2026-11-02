<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Tab «Unita' di misura» della vista omonima: elenco delle unita' +
//        drawer di dettaglio + sub-drawer delle conversioni della singola
//        unita', apribile dalla riga.
//
// ⭐ Era il corpo di `UnitaMisuraView` fino al 2026-09-04 (raggruppamento
//    chiesto da Tid): la vista ora e' il solo contenitore dei tre tab, e
//    ogni scheda porta il proprio stato e il proprio provider readonly.
// ⚠️ Il sub-drawer conversioni resta QUI e non diventa il tab «Conversioni»:
//    sono due domande diverse — «le conversioni DI questa unita'» contro
//    «tutte le conversioni». Il tab non lo sostituisce.
import { ref } from 'vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useUnitaMisuraStore } from '../stores/unitaMisura'
import UnitaMisuraSearchTable from './UnitaMisuraSearchTable.vue'
import UnitaMisuraDrawer from './UnitaMisuraDrawer.vue'
import UomConversioniDrawer from './UomConversioniDrawer.vue'

const drawer = useDrawerState()
const store = useUnitaMisuraStore()
const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)
// ⛔ Provider a livello OGGETTO, e sta qui e non sulla vista ospite: le tre
//    schede non hanno lo stesso model (`UOM_TIPI` per i tipi), quindi un
//    provider unico d'area toglierebbe la granularita' che c'e' gia'.
useReadonlyMode(READONLY_DOMAINS.CATALOGO, READONLY_MODELS.UNITA_MISURA)

// Sub-drawer conversioni
const convDrawerVisible = ref(false)
const convUomId = ref(null)
const convUomCodice = ref('')

function onManageConversioni(data) {
  convUomId.value = data.id
  convUomCodice.value = data.codice || ''
  convDrawerVisible.value = true
}
</script>

<template>
  <!-- ⛔ NESSUN wrapper attorno alla SearchTable: la catena flex dei tab e'
       `.p-tabpanel > .app-tab-content > DataTable` e la SearchTable porta gia'
       `app-tab-content` come proprio root. Un div in mezzo non fa matchare il
       selettore e la tabella perde `scroll-height="flex"` — difetto muto, che
       si vede solo con abbastanza righe da dover scorrere.
       Il componente ha quindi PIU' ROOT (SearchTable + drawer), che e' lecito
       in Vue 3 e non cambia niente ai drawer (PrimeVue li rende su body). -->
  <UnitaMisuraSearchTable
    @new="drawer.openCreate"
    @row-click="(data) => drawer.editRow(data, 'id')"
    @manage-conversioni="onManageConversioni"
  />

  <UnitaMisuraDrawer
    :visible="drawer.state.visible"
    @update:visible="v => drawer.state.visible = v"
    :mode="drawer.state.mode"
    :uom-id="drawer.state.itemId"
    @saved="onDrawerSaved"
    @cancelled="drawer.close"
  />

  <UomConversioniDrawer
    :visible="convDrawerVisible"
    @update:visible="v => convDrawerVisible = v"
    :uom-id="convUomId"
    :uom-codice="convUomCodice"
  />
</template>
