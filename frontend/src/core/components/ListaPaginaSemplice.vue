<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la PAGINA-LISTA SEMPLICE — una lista a catalogo di rotta (o di un tab
//        di pagina) che non ha logica propria: accesso bloccato, casella di
//        ricerca, filtri, azioni di testata («Nuovo», ricarica, personalizza,
//        export), `<ListaConfigurabile>`, freschezza del tab e prima lettura.
//        Il chiamante dichiara solo cio' che la distingue: store, codice,
//        entita' del tab, testi, ordine di partenza, click sulla riga, e —
//        dagli slot — i filtri in piu' e le celle.
//
// ⭐ ESTRATTO IL 2026-09-27 (regola del 2, ok Tid) dalle SEI liste geografiche
//    (`config.regioni`, `.province`, `.stati`, `.comuni`, `.codici_postali`,
//    `.toponomastica`): sei file da 90-100 righe uguali salvo sette valori.
//    `GeoSearchTable`, ritirato lo stesso giorno, faceva la stessa cosa con la
//    `DataTable` grezza e le colonne scritte nel `.vue`; qui le colonne restano
//    del catalogo, e il BB non sa niente di geografia.
// ⚠️ NON e' per le liste con stato di dominio nel `.vue` (azioni di riga,
//    dialog, drawer montati dentro): quelle restano scritte con
//    `useListaConfigurabilePage` + `<ListaConfigurabile>`, che e' la forma
//    standard. Questo BB e' la forma standard CHIUSA, per chi non aggiunge
//    niente.
//
// Slot:
//   - `filtri` — i filtri in piu' dentro `<FiltriLista>` (dopo la ricerca),
//     con `{ applyFilters }` per rileggere dopo averli scritti nello store;
//   - ogni altro slot (`cell-*`, `#actions`, `#empty`) va a
//     `<ListaConfigurabile>` tal quale.
import { onMounted } from 'vue'
import InputText from 'primevue/inputtext'
import { useListaConfigurabilePage } from '../composables/useListaConfigurabilePage'
import { useTabFreshness } from '../composables/useTabFreshness'
import { useInjectBlocked } from '../composables/useReadonlyMode'
import AccessoBloccatoPanel from './AccessoBloccatoPanel.vue'
import FiltriLista from './FiltriLista.vue'
import ListaConfigurabile from './ListaConfigurabile.vue'
import ListaConfigStatusTag from './ListaConfigStatusTag.vue'
import PageActionsBar from './PageActionsBar.vue'
import ReadonlyBadge from './ReadonlyBadge.vue'

const props = defineProps({
  // Lo store-lista (factory del core): lo possiede il chiamante.
  store: { type: Object, required: true },
  // Il codice della lista a catalogo (`ui.lista_definizione.codice`).
  codice: { type: String, required: true },
  // L'entita' del tab (`TAB_ENTITIES.*`): la lista si rilegge quando un altro
  // tab la modifica (`useTabFreshness`).
  tabEntity: { type: String, required: true },
  // Il segnaposto della casella di ricerca, gia' tradotto.
  searchPlaceholder: { type: String, default: '' },
  // Chiave i18n del tooltip di «Nuovo». Il comando emette `new`.
  newTooltipKey: { type: String, default: null },
  // L'ordinamento di partenza (`useSearchTable`).
  defaultSortField: { type: String, default: null },
  defaultSortOrder: { type: String, default: 'asc' },
  // ⚠️ `false` quando la riga non apre niente: niente `row-click` e niente
  //    evidenziazione — una riga che si illumina al click prometterebbe un
  //    dettaglio che non c'e' (i comuni).
  righeCliccabili: { type: Boolean, default: true },
})

const emit = defineEmits(['row-click', 'new'])
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(props.store, {
  newTooltipKey: props.newTooltipKey,
  onNew: () => emit('new'),
  searchTableOptions: {
    defaultSortField: props.defaultSortField,
    defaultSortOrder: props.defaultSortOrder,
  },
})

useTabFreshness(props.store, props.tabEntity)
// Le liste di questa forma partono PIENE (`startsEmpty: false` nello store):
// la prima lettura e' qui, il rientro sotto KeepAlive lo gestisce lo
// scaffolding.
onMounted(() => { props.store.fetchList() })

// `<ListaConfigurabile>` emette la RIGA (non l'evento PrimeVue).
function onRowClick(data) {
  if (props.righeCliccabili) emit('row-click', data)
}

// ⭐ `applyFilters` esce anche dal componente, non solo dallo slot: i filtri
//    col binding allo store (`useStoreFilterBindings`) si dichiarano nel setup
//    del chiamante, prima che lo slot esista. Il chiamante lo passa PIGRO —
//    `() => paginaRef.value.applyFilters()` — e si risolve al cambio del
//    filtro, quando il componente c'e'.
defineExpose({ applyFilters })

// Gli slot da girare alla lista: tutti tranne `filtri`, che e' nostro.
// ⛔ Una funzione e non una `computed`: l'oggetto degli slot non e' reattivo
//    (vedi `DrawerTabLista`, stesso inoltro).
function slotInoltrati(slots) {
  return Object.keys(slots).filter((n) => n !== 'filtri')
}
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
              :placeholder="searchPlaceholder"
            />
          </template>
          <slot name="filtri" v-bind="{ applyFilters }" />
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
        :codice="codice"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        :selection-mode="righeCliccabili ? 'single' : null"
        @page="onPage"
        @sort="onSort"
        @row-click="onRowClick"
        @config-loaded="onConfigLoaded"
      >
        <template v-for="nome in slotInoltrati($slots)" #[nome]="scope" :key="nome">
          <slot :name="nome" v-bind="scope ?? {}" />
        </template>
      </ListaConfigurabile>
    </template>
  </div>
</template>
