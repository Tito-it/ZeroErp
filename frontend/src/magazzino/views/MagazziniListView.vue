<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pagina dei MAGAZZINI (anagrafica del dominio, prima voce L2): host
//        della lista configurabile, del drawer del magazzino e del drawer
//        autonomo delle ubicazioni (raggiungibile dal kebab della lista E
//        da «Gestisci ubicazioni» nel drawer).
//
// ⚠️ Il permesso e' di AREA (`magazzino`): creare un magazzino passa da qui e
//    non piu' dall'area `config` (decisione B del piano anagrafiche-fuori-dal-
//    pannello-config §2, conseguenza dichiarata).
import { ref } from 'vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import MagazziniSearchTable from '../components/MagazziniSearchTable.vue'
import MagazzinoDrawer from '../components/MagazzinoDrawer.vue'
import MagazzinoUbicazioniDrawer from '../components/MagazzinoUbicazioniDrawer.vue'

useReadonlyMode(READONLY_DOMAINS.MAGAZZINO)
const drawer = useDrawerState()

// Il drawer delle ubicazioni aperto dal kebab: porta il magazzino della riga.
const ubicazioniVisible = ref(false)
const ubicazioniMagazzino = ref(null)

function onManageUbicazioni(riga) {
  ubicazioniMagazzino.value = riga
  ubicazioniVisible.value = true
}

// ⛔ Nessun `store.fetchList()` qui: ogni verbo dello store emette
//    `TAB_ENTITIES.MAGAZZINO` e la lista si ricarica da sola.
function onSaved() {
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <MagazziniSearchTable
      @new="drawer.openCreate"
      @row-click="(riga) => drawer.editRow(riga, 'id')"
      @manage-ubicazioni="onManageUbicazioni"
    />

    <MagazzinoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :magazzino-id="drawer.state.itemId"
      @saved="onSaved"
      @cancelled="drawer.close"
    />

    <MagazzinoUbicazioniDrawer
      v-model:visible="ubicazioniVisible"
      :magazzino-id="ubicazioniMagazzino?.id ?? null"
      :magazzino-codice="ubicazioniMagazzino?.codice ?? ''"
      :usa-ubicazioni="ubicazioniMagazzino?.usa_ubicazioni ?? true"
    />
  </div>
</template>
