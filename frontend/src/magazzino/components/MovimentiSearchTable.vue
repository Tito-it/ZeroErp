<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL REGISTRO dei movimenti di magazzino — la lista configurabile
//        `magazzino.movimenti` (77) coi suoi filtri: magazzino, articolo,
//        causale, sorgente, date, e il documento di provenienza (deep-link dal
//        documento POSTED).
//
// ⭐ Sola lettura per costruzione: la porta sul registro e' la primitiva DB, e
//    da qui non si scrive niente — niente «Nuovo», niente azioni di riga,
//    niente drawer. Il click sulla riga non fa nulla: un movimento non ha un
//    dettaglio oltre la riga stessa.
//
// ⚠️ La lista DEVE dire quando e' filtrata su un documento (chip sopra la
//    tabella, stessa forma della coda resi): un elenco corto senza spiegazione
//    si legge come «in magazzino non e' successo quasi niente». Il chip toglie
//    il filtro e ricarica.
import { computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ArticoloLookup from '../../catalogo/components/ArticoloLookup.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { exportMovimenti } from '../api/magazzino'
import { useEtichetteMagazzino } from '../etichette'
import { useMovimentiStore } from '../stores/movimenti'
import FiltroPeriodo from '../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'

const { t } = useI18n()
const store = useMovimentiStore()
const isBlocked = useInjectBlocked()
const { sorgenteMovimento, opzioniSorgenteMovimento } = useEtichetteMagazzino()
const opzioniSorgente = opzioniSorgenteMovimento()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded,
  pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportMovimenti,
  // L'export segue la lista a video — filtri e ordinamento — dalla sede unica
  // dello store (`paramsFiltro`), non da una ricostruzione a mano.
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
  searchTableOptions: { defaultSortField: 'data_mov', defaultSortOrder: 'desc' },
})

// --- Filtri (toolbar caller) — binding store via BB ---
// L'articolo e' un lookup RICCO: il widget tiene l'oggetto, lo store l'id
// (`bindLookup`, lo stesso della disponibilita').
const { bindSelect, bindLookup, bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const { value: magazzinoFilter, onChange: onMagazzinoChange } = bindSelect('magazzino_id')
const { value: articoloFilter, onChange: onArticoloChange } = bindLookup('articolo_id')
const { value: causaleFilter, onChange: onCausaleChange } = bindSelect('causale_id')
const { value: sorgenteFilter, onChange: onSorgenteChange } = bindSelect('sorgente_tipo')
// Il periodo e' UN filtro con due estremi: un binding, un componente.
const periodo = bindPeriodo()

// ── il filtro documento (deep-link dal POSTED) ─────────────────────
// Sta nello STORE, non solo nella query: la lista lo deve DICHIARARE.
const filtroDocumento = computed(() => {
  if (store.filters.inventario_id != null) {
    return t('magazzino.movimenti.filtro_documento_inventario', { id: store.filters.inventario_id })
  }
  if (store.filters.rettifica_id != null) {
    return t('magazzino.movimenti.filtro_documento_rettifica', { id: store.filters.rettifica_id })
  }
  return null
})

function rimuoviFiltroDocumento() {
  store.filters.inventario_id = null
  store.filters.rettifica_id = null
}

// Il filtro documento arriva da FUORI (deep-link della vista) oppure dal chip:
// in entrambi i casi la ricarica la decide QUESTO componente, che e' l'unico a
// sapere di essere montato — la vista non prova a indovinarlo.
watch(
  [() => store.filters.inventario_id, () => store.filters.rettifica_id],
  () => applyFilters(),
)

// Lista con floor data standard: parte piena al mount.
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <!-- La ricerca: colonne dal catalogo (`ricerca_full`), sotto 3
               caratteri il termine non filtra; l'export porta la stessa
               `search` (`paramsFiltro`). -->
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('common.search')"
            />
          </template>
          <LookupSelect
            v-model="magazzinoFilter"
            class="app-filter-w-md"
            rel="magazzino.magazzini"
            :placeholder="t('magazzino.movimenti.filtro_magazzino')"
            show-clear
            show-code
            @change="onMagazzinoChange"
          />
          <ArticoloLookup
            v-model="articoloFilter"
            class="app-filter-w-lg"
            :placeholder="t('magazzino.movimenti.filtro_articolo')"
            :solo-attivi="false"
            @update:model-value="onArticoloChange"
          />
          <LookupSelect
            v-model="causaleFilter"
            class="app-filter-w-md"
            rel="magazzino.causali"
            :placeholder="t('magazzino.movimenti.filtro_causale')"
            show-clear
            show-code
            @change="onCausaleChange"
          />
          <Select
            v-model="sorgenteFilter"
            class="app-filter-w-md"
            :options="opzioniSorgente"
            option-label="label"
            option-value="value"
            :placeholder="t('magazzino.movimenti.filtro_sorgente')"
            show-clear
            @update:model-value="onSorgenteChange"
          />
          <FiltroPeriodo :periodo="periodo" />
        </FiltriLista>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <Message
        v-if="filtroDocumento"
        severity="info"
        :closable="false"
        size="small"
      >
        {{ filtroDocumento }}
        <Button
          link
          size="small"
          :label="t('magazzino.movimenti.filtro_documento_rimuovi')"
          @click="rimuoviFiltroDocumento"
        />
      </Message>

      <ListaConfigurabile
        ref="listaRef"
        codice="magazzino.movimenti"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        @page="onPage"
        @sort="onSort"
        @config-loaded="onConfigLoaded"
      >
        <!-- La sorgente e' un codice del DB (`config.sorgenti.codice_interno`),
             vocabolario APERTO: l'etichetta ripiega sul codice. -->
        <template #cell-sorgente_codice_interno="{ data }">
          <Tag
            v-if="data.sorgente_codice_interno"
            :value="sorgenteMovimento(data.sorgente_codice_interno)"
            severity="secondary"
          />
          <span v-else>—</span>
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
