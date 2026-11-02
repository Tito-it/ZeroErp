<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer AUTONOMO delle UBICAZIONI di un magazzino (piano anagrafiche-
//        fuori-dal-pannello-config §5): lista configurabile
//        (`magazzino.ubicazioni`, 81) con `useDrawerTabLista` + `<DrawerTabLista>`
//        (⛔ non una `DataTable` in un drawer), «Mostra non attive», «Nuova»,
//        export, e il drawer della singola ubicazione. Raggiungibile dal kebab
//        della lista magazzini E da «Gestisci ubicazioni» nel drawer del
//        magazzino (`feedback_drawer_autonomi`).
//
// ⚠️ Se il magazzino NON usa le ubicazioni il drawer si apre lo stesso, con
//    l'avviso: il dato lo governa il flag, non l'assenza di righe.
// ⚠️ La disattivazione la rifiuta il DB se l'ubicazione ha figlie o movimenti
//    (`E_ATTIVO_BLOCK_CHILDREN_EXIST`): le azioni di riga sono il BB
//    `useAzioniAttivo`, la frase arriva dal backend.
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
import { exportUbicazioni } from '../api/magazzino'
import { useUbicazioniStore } from '../stores/ubicazioni'
import UbicazioneDrawer from './UbicazioneDrawer.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  magazzinoId: { type: Number, default: null },
  magazzinoCodice: { type: String, default: '' },
  usaUbicazioni: { type: Boolean, default: true },
})
const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const store = useUbicazioniStore()

const ubicazioneDrawerVisible = ref(false)
const ubicazioneSelezionataId = ref(null)

// ⚠️ `parentId` porta l'id SOLO a drawer aperto: il `null` alla chiusura dice
//    al BB di chiamare `store.reset()`, o la lista del magazzino precedente
//    lampeggerebbe sotto il prossimo.
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm, reloadAll,
} = useDrawerTabLista(store, {
  parentId: () => (props.visible ? props.magazzinoId : null),
  parentField: 'magazzinoId',
  exportFn: (params) => exportUbicazioni(props.magazzinoId, params),
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
  newTooltipKey: 'magazzino.ubicazioni.nuova',
  onNew: () => apriUbicazione(null),
})

const { bindToggle } = useStoreFilterBindings(store, applyFilters)
const { value: mostraNonAttive, onChange: onMostraNonAttiveChange } = bindToggle('attivo', { on: null, off: true })

function apriUbicazione(id) {
  ubicazioneSelezionataId.value = id
  ubicazioneDrawerVisible.value = true
}

// ⚠️ `reloadAll()` non e' awaitable: si ricarica e si avvisa il padre.
function onUbicazioneSaved() {
  reloadAll()
  emit('saved')
}

// Le sole azioni di riga sono spegni/riaccendi: dopo, la lista si ricarica e
// il padre viene avvisato come per un salvataggio dal drawer.
const { azioniAttivo } = useAzioniAttivo(store, { prefisso: 'magazzino.ubicazioni', onDone: onUbicazioneSaved })

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :proteggi-corpo="false"
    :title="t('magazzino.ubicazioni.titolo_lista')"
    :icon="MANAGE_ICONS.UBICAZIONI"
    :action="magazzinoCodice"
    :width="DRAWER_WIDTH.WIDE"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <Message v-if="!usaUbicazioni" severity="warn" :closable="false" class="mt-05">
      {{ t('magazzino.ubicazioni.magazzino_non_le_usa') }}
    </Message>

    <DrawerTabLista
      ref="listaRef"
      codice="magazzino.ubicazioni"
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
      @row-click="apriUbicazione($event.id)"
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
          v-model="mostraNonAttive"
          :label="t('magazzino.anagrafiche.mostra_non_attivi')"
          @change="onMostraNonAttiveChange"
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

    <UbicazioneDrawer
      v-model:visible="ubicazioneDrawerVisible"
      :magazzino-id="magazzinoId"
      :ubicazione-id="ubicazioneSelezionataId"
      @saved="onUbicazioneSaved" />
  </AppDrawer>
</template>
