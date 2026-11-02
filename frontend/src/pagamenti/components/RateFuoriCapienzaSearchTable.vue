<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: L'ELENCO DELLE RATE FUORI CAPIENZA — le rate su cui e' entrato piu' di
//        quanto dovessero portare (`<ListaConfigurabile
//        codice="pagamenti.rate_fuori_capienza">`, vista `vw_rate_fuori_capienza`).
//
// ⭐ E' L'ELENCO CHE RENDE ONESTA LA FORZATURA. Quando l'operatore forza la
//    capienza di una rata, quel gesto resta scritto sulla riga; senza questa
//    lista il denaro di troppo sarebbe registrato e invisibile — cioe' forzare
//    NASCONDEREBBE invece di registrare. Per questo la PRIMA colonna e' il
//    motivo, non il numero.
//
// ⚠️ Le popolazioni sono DUE e non vanno confuse: sovra-incasso (e' entrato piu'
//    del dovuto) e movimento contrario (un segno che non torna). Il filtro le
//    separa; il vocabolario e' chiuso, e un valore sbagliato darebbe una lista
//    vuota — cioe' «non c'e' niente da sistemare», che qui e' la bugia peggiore.
//
// ⭐ E la NATURA del documento cambia cosa i due motivi SIGNIFICANO (P-7,
//    2026-09-18 — la vista la porta da quel giorno): su una nota di credito
//    «sovra-incassata» vuol dire rimborsato piu' del credito, e «movimento
//    contrario» che e' entrato denaro invece di uscire. Il codice resta uno, la
//    frase la sceglie la natura — in UNA sede (`useEtichettePagamenti`), la
//    stessa della tendina, del form e del picker.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Select from 'primevue/select'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import ResiduoCella from './ResiduoCella.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useEtichettePagamenti } from '../etichette'
import { useRateFuoriCapienzaStore } from '../stores/rateFuoriCapienza'
import { STATUS_ICONS } from '../../core/constants'
import FiltriLista from '../../core/components/FiltriLista.vue'

const emit = defineEmits(['row-click'])
// ⚠️ `te` serve a decodificare fail-visible: un motivo che il database aggiunge
//    e i locales non conoscono si vede come CODICE, non come cella vuota.
const { t } = useI18n()
const store = useRateFuoriCapienzaStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'data_scadenza', defaultSortOrder: 'desc' },
})

const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: motivoFilter, onChange: onMotivoChange } = bindSelect('motivo')

// ⛔ Vocabolario CHIUSO, e sono DUE mondi diversi: `SOVRA_INCASSATA` (e' entrato
//    piu' del dovuto) e `MOVIMENTO_CONTRARIO` (un segno che non torna). Due voci
//    statiche e non un lookup: e' un CHECK del backend, non una tabella.
// ⭐ Il residuo a parole e' `ResiduoCella`, la stessa cella del picker: fino al
//    18/09 questa lista aveva la sua copia («di troppo» e basta), che su una
//    nota di credito avrebbe detto la cosa sbagliata.
const { motivoFuoriCapienza: etichettaMotivo, opzioniMotivoFuoriCapienza } =
  useEtichettePagamenti()
const opzioniMotivo = opzioniMotivoFuoriCapienza()

function onRowClick(data) { emit('row-click', data) }
onMounted(() => store.fetchList())
// ⛔ NIENTE `onActivated` che ricarica: la freschezza al rientro nella scheda la
//    tiene gia' `useSearchTable` (refetch idempotente della pagina corrente,
//    saltato alla prima attivazione). Aggiungerne un secondo qui manderebbe DUE
//    richieste identiche a ogni rientro, e le loro risposte possono tornare in
//    ordine inverso — su una lista di denaro, l'ordine conta.
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <!-- La ricerca: colonne dal catalogo (`ricerca_full`: senza colonne
               accese la casella non si rende), sotto 3 caratteri il termine
               non filtra. -->
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('common.search')"
            />
          </template>
          <Select
            v-model="motivoFilter"
            class="app-filter-w-md"
            :options="opzioniMotivo"
            option-label="label"
            option-value="value"
            :placeholder="t('pagamenti.rate_fuori_capienza.filtro_motivo')"
            show-clear
            @update:model-value="onMotivoChange"
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
        codice="pagamenti.rate_fuori_capienza"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        @page="onPage"
        @sort="onSort"
        @row-click="onRowClick"
        @config-loaded="onConfigLoaded"
      >
        <!-- ⭐ Il MOTIVO e' la prima colonna perche' e' la prima domanda: le due
             popolazioni chiedono lavori diversi. Fail-visible: un motivo che il
             database aggiunge e i locales non conoscono si vede come CODICE, non
             come cella vuota. La frase segue la NATURA della riga (P-7). -->
        <template #cell-motivo="{ data }">
          <Tag
            v-if="data.motivo"
            :value="etichettaMotivo(data.motivo, data.natura_doc_codice_interno)"
            severity="warn"
          />
          <span v-else>—</span>
        </template>

        <!-- ⭐ La NATURA (colonna 767 del seed) NON ha slot: il seed dichiara
             `formato = natura_doc` e `CellaConfigurabile` la rende con
             `NaturaDocTag sempre` — una cella vuota su una fattura si
             leggerebbe come dato perso. -->

        <!-- ⛔ IL RESIDUO NEGATIVO NON SI MOSTRA COME NUMERO NEGATIVO: «-120,00»
             si legge come un guasto anche quando racconta correttamente il
             mondo. Si dice cosa significa, e a deciderlo e' la NATURA — nel BB
             `ResiduoCella`, la stessa cella del picker: su una fattura «di
             troppo» (e' entrato piu' del dovuto), su una nota di credito «da
             rimborsare» (il segno e' il verso del documento). -->
        <template #cell-residuo="{ data }">
          <ResiduoCella :residuo="data.residuo" :natura-codice="data.natura_doc_codice_interno" />
        </template>

        <template #empty>
          <div class="app-empty-state">
            <i :class="STATUS_ICONS.TUTTO_OK" />
            <p>{{ t('pagamenti.rate_fuori_capienza.nessuna_rata') }}</p>
          </div>
        </template>
      </ListaConfigurabile>
    </template>
  </div>
</template>
