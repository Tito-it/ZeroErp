<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA LISTA dei magazzini (`magazzino.magazzini`, lista 80): lista
//        configurabile, ricerca, «Mostra non attivi», «Nuovo», export, azioni
//        di riga («Ubicazioni» apre il drawer autonomo delle figlie;
//        «Disattiva/Riattiva» e' un PATCH e il DB decide).
//
// ⚠️ La disattivazione la rifiuta il DB se il magazzino ha ubicazioni,
//    documenti o movimenti attivi (`E_ATTIVO_BLOCK_CHILDREN_EXIST`, 409, con
//    la frase): le due azioni, la conferma e il PATCH sono il BB
//    `useAzioniAttivo` (regola del 2: tre anagrafiche, una forma).
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import AttivoTag from '../../core/components/AttivoTag.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useAzioniAttivo } from '../../core/composables/useAzioniAttivo'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { exportMagazzini } from '../api/magazzino'
import { useMagazziniStore } from '../stores/magazzini'
import FiltriLista from '../../core/components/FiltriLista.vue'

const emit = defineEmits(['new', 'row-click', 'manage-ubicazioni'])

const { t } = useI18n()
const store = useMagazziniStore()
const isBlocked = useInjectBlocked()
// ⛔ Nessun `onDone`: il verbo dello store emette `TAB_ENTITIES.MAGAZZINO` e
//    `useTabFreshness` ricarica.
const { azioniAttivo } = useAzioniAttivo(store, { prefisso: 'magazzino.magazzini' })

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded,
  pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportMagazzini,
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
  newTooltipKey: 'magazzino.magazzini.nuovo',
  newLabelKey: 'magazzino.magazzini.nuovo',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'codice', defaultSortOrder: 'asc' },
})

// «Mostra non attivi»: acceso = `attivo: null` (tutti), spento = `true`.
const { bindToggle } = useStoreFilterBindings(store, applyFilters)
const { value: mostraNonAttivi, onChange: onMostraNonAttiviChange } = bindToggle('attivo', { on: null, off: true })

function onRowClick(data) { emit('row-click', data) }

function buildRowActions(riga) {
  return [
    {
      key: 'ubicazioni',
      label: t('magazzino.ubicazioni.gestisci'),
      icon: MANAGE_ICONS.UBICAZIONI,
      command: () => emit('manage-ubicazioni', riga),
    },
    ...azioniAttivo(riga),
  ]
}

// Il numero di pulsanti inline della colonna azioni: e' l'unica larghezza che
// il catalogo non conosce, e la dichiara chi scrive `buildRowActions`.
const AZIONI_INLINE = 2

useTabFreshness(store, TAB_ENTITIES.MAGAZZINO)

onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('magazzino.magazzini.search_placeholder')"
            />
          </template>
          <FiltroToggle
            v-model="mostraNonAttivi"
            :label="t('magazzino.anagrafiche.mostra_non_attivi')"
            @change="onMostraNonAttiviChange"
          />
        </FiltriLista>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <ListaConfigurabile
        ref="listaRef"
        codice="magazzino.magazzini"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        :azioni-inline="AZIONI_INLINE"
        @page="onPage"
        @sort="onSort"
        @row-click="onRowClick"
        @config-loaded="onConfigLoaded"
      >
        <template #cell-attivo="{ data }">
          <AttivoTag :active="data.attivo" />
        </template>
        <template #cell-predefinito="{ data }">
          <Tag v-if="data.predefinito" :value="t('magazzino.magazzini.tag_predefinito')" severity="info" />
        </template>

        <template #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </ListaConfigurabile>
    </template>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />
  </div>
</template>
