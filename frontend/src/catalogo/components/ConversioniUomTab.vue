<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Tab «Conversioni» della vista Unita' di misura: elenco TRASVERSALE
//        delle conversioni fra unita' + drawer di dettaglio.
//
// ⭐ Era una vista sua fino al 2026-09-04 (raggruppamento chiesto da Tid): le
//    tre tabelle delle UdM sono un soggetto solo — un tipo raggruppa le unita',
//    una conversione ne lega due — e stavano su tre voci di menu che non si
//    sapevano l'una dell'altra.
// ⚠️ Non e' un doppione di `UomConversioniDrawer`, che dalla riga di
//    un'unita' mostra le SUE conversioni: qui si vedono tutte insieme, ed e'
//    il posto dove ci si accorge di quella che manca o e' doppia.
// ⛔ Il provider readonly resta QUI e a livello OGGETTO
//    (`READONLY_MODELS.UNITA_MISURA`): un unico provider d'AREA sulla vista
//    ospite appiattirebbe la granularita' che questa scheda ha gia'.
// ⭐ L'handler «salvato → ricarica, e dopo una create riapri in edit» era
//    scritto a mano qui, identico al BB `useDrawerSavedListRefresh` che le
//    altre due schede usano gia': tolta la copia. In piu' il BB azzera
//    `filters.offset`, cosa che la copia non faceva — dopo un salvataggio da
//    pagina 3 la lista restava a pagina 3, e la riga appena creata (che le
//    liste mostrano in testa) non si vedeva.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useConversioniUomStore } from '../stores/conversioniUom'
import ConversioniUomSearchTable from './ConversioniUomSearchTable.vue'
import ConversioneUomDrawer from './ConversioneUomDrawer.vue'

const drawer = useDrawerState()
const store = useConversioniUomStore()
const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)
useReadonlyMode(READONLY_DOMAINS.CATALOGO, READONLY_MODELS.UNITA_MISURA)
</script>

<template>
  <!-- ⛔ NESSUN wrapper attorno alla SearchTable: la catena flex dei tab e'
       `.p-tabpanel > .app-tab-content > DataTable` e la SearchTable porta gia'
       `app-tab-content` come proprio root. Un div in mezzo non fa matchare il
       selettore e la tabella perde `scroll-height="flex"` — difetto muto, che
       si vede solo con abbastanza righe da dover scorrere.
       Il componente ha quindi PIU' ROOT (SearchTable + drawer), che e' lecito
       in Vue 3 e non cambia niente ai drawer (PrimeVue li rende su body). -->
  <ConversioniUomSearchTable
    @new="drawer.openCreate"
    @row-click="(data) => drawer.editRow(data, 'id')"
  />

  <ConversioneUomDrawer
    :visible="drawer.state.visible"
    @update:visible="v => drawer.state.visible = v"
    :mode="drawer.state.mode"
    :conv-id="drawer.state.itemId"
    @saved="onDrawerSaved"
    @cancelled="drawer.close"
  />
</template>
