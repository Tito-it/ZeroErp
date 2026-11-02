<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer AUTONOMO dei LOTTI di un articolo (piano anagrafiche-fuori-
//        dal-pannello-config §6, Q-1: vive in `src/magazzino` perche' la
//        tabella, l'API e lo store sono di magazzino; lo montano
//        `ArticoloDrawer` e `ArticoliView` di catalogo). Lista configurabile
//        (`magazzino.lotti`, 82) con `useDrawerTabLista` + `<DrawerTabLista>`,
//        «Mostra non attivi», «Nuovo», export, e il drawer del singolo lotto.
//
// ⭐ Un lotto di MAGAZZINO e' la PARTITA di merce di un articolo
//    (`articolo_id + codice`, arrivo, scadenza), nominata da
//    `movimenti.lotto_id` quando l'articolo e' `requires_lotto` — da non
//    confondere con `vendite.fatturazione_lotti`, il giro di fatturazione.
// ⚠️ Su un articolo DISATTIVO il DB rifiuta la scrittura (`E_ATTIVO_REQUIRE`,
//    TECNICO): il chiamante non apre questo drawer su un articolo spento.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'

import AttivoTag from '../../core/components/AttivoTag.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useAzioniAttivo } from '../../core/composables/useAzioniAttivo'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { exportLotti } from '../api/magazzino'
import { useLottiStore } from '../stores/lotti'
import LottoDrawer from './LottoDrawer.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: String, default: null },
  articoloCodice: { type: String, default: '' },
  // Se l'articolo NON si movimenta per lotti, il drawer lo dice: un lotto ha
  // senso solo su merce che il registro nomina per partita.
  requiresLotto: { type: Boolean, default: true },
})
const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const store = useLottiStore()

const lottoDrawerVisible = ref(false)
const lottoSelezionatoId = ref(null)

// ⚠️ `parentId` porta l'id SOLO a drawer aperto: il `null` alla chiusura
//    chiama `store.reset()`, o i lotti dell'articolo precedente lampeggerebbero
//    sotto il prossimo.
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm, reloadAll,
} = useDrawerTabLista(store, {
  parentId: () => (props.visible ? props.articoloId : null),
  parentField: 'articoloId',
  exportFn: (params) => exportLotti({ articolo_id: props.articoloId, ...params }),
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
  newTooltipKey: 'magazzino.lotti.nuovo',
  onNew: () => apriLotto(null),
})

const { bindToggle } = useStoreFilterBindings(store, applyFilters)
const { value: mostraNonAttivi, onChange: onMostraNonAttiviChange } = bindToggle('attivo', { on: null, off: true })

function apriLotto(id) {
  lottoSelezionatoId.value = id
  lottoDrawerVisible.value = true
}

function onLottoSaved() {
  reloadAll()
  emit('saved')
}

// La disattivazione la rifiuta il DB se il lotto ha movimenti o righe
// (`E_ATTIVO_BLOCK_CHILDREN_EXIST`): le azioni di riga sono il BB
// `useAzioniAttivo`, la frase arriva dal backend.
const { azioniAttivo } = useAzioniAttivo(store, { prefisso: 'magazzino.lotti', onDone: onLottoSaved })

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :proteggi-corpo="false"
    :title="t('magazzino.lotti.titolo_lista')"
    :icon="MANAGE_ICONS.LOTTO_MAGAZZINO"
    :action="articoloCodice"
    :width="DRAWER_WIDTH.WIDE"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <Message v-if="!requiresLotto" severity="info" :closable="false" class="mt-05">
      {{ t('magazzino.lotti.articolo_non_per_lotti') }}
    </Message>

    <DrawerTabLista
      ref="listaRef"
      codice="magazzino.lotti"
      :store="store"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      :page-actions="pageActions"
      :dirty="dirty"
      :perimetro-bloccato="perimetroBloccato"
      @page="onPage"
      @sort="onSort"
      @row-click="apriLotto($event.id)"
      @config-loaded="onConfigLoaded"
    >
      <!-- La ricerca: le colonne le decide il catalogo (`ricerca_full`),
           il placeholder non le elenca; l'export porta la stessa `search`
           (`paramsFiltro`). -->
      <template #filtri-sempre>
        <InputText
          v-model="searchText"
          class="app-filter-w-lg"
          :placeholder="t('common.search')"
        />
      </template>
      <template #filtri>
        <FiltroToggle
          v-model="mostraNonAttivi"
          :label="t('magazzino.anagrafiche.mostra_non_attivi')"
          @change="onMostraNonAttiviChange"
        />
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="azioniAttivo(data)" />
      </template>
    </DrawerTabLista>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm" />

    <LottoDrawer
      v-model:visible="lottoDrawerVisible"
      :lotto-id="lottoSelezionatoId"
      @saved="onLottoSaved" />
  </AppDrawer>
</template>
