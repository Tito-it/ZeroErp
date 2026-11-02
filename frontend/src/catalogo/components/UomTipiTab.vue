<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Tab «Tipi» della vista Unita' di misura: le tipologie che
//        raggruppano le unita' + drawer di dettaglio.
//
// ⭐ Era una vista sua fino al 2026-09-04 (raggruppamento chiesto da Tid).
// ⛔ Il provider readonly resta QUI, e il suo model e' `UOM_TIPI` — DIVERSO da
//    quello delle altre due schede (`UNITA_MISURA`): e' la ragione per cui
//    ogni tab e' provider di se' invece di ereditare un unico provider d'area
//    dalla vista ospite.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useUomTipiStore } from '../stores/uomTipi'
import UomTipiSearchTable from './UomTipiSearchTable.vue'
import UomTipoDrawer from './UomTipoDrawer.vue'

const drawer = useDrawerState()
const store = useUomTipiStore()
const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)
useReadonlyMode(READONLY_DOMAINS.CATALOGO, READONLY_MODELS.UOM_TIPI)

</script>

<template>
  <!-- ⛔ NESSUN wrapper attorno alla SearchTable: la catena flex dei tab e'
       `.p-tabpanel > .app-tab-content > DataTable` e la SearchTable porta gia'
       `app-tab-content` come proprio root. Un div in mezzo non fa matchare il
       selettore e la tabella perde `scroll-height="flex"` — difetto muto, che
       si vede solo con abbastanza righe da dover scorrere.
       Il componente ha quindi PIU' ROOT (SearchTable + drawer), che e' lecito
       in Vue 3 e non cambia niente ai drawer (PrimeVue li rende su body). -->
  <UomTipiSearchTable
    @new="drawer.openCreate"
    @row-click="(data) => drawer.editRow(data, 'id')"
  />

  <UomTipoDrawer
    :visible="drawer.state.visible"
    @update:visible="v => drawer.state.visible = v"
    :mode="drawer.state.mode"
    :tipo-id="drawer.state.itemId"
    @saved="onDrawerSaved"
    @cancelled="drawer.close"
  />
</template>
