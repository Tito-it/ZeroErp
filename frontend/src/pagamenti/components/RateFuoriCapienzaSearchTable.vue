<!--
  SPDX-License-Identifier: GPL-3.0-or-later
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
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Select from 'primevue/select'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useEtichettePagamenti } from '../etichette'
import { euro } from '../formato'
import { useRateFuoriCapienzaStore } from '../stores/rateFuoriCapienza'

const emit = defineEmits(['row-click'])
// ⚠️ `te` serve a decodificare fail-visible: un motivo che il database aggiunge
//    e i locales non conoscono si vede come CODICE, non come cella vuota.
const { t } = useI18n()
const store = useRateFuoriCapienzaStore()
const isBlocked = useInjectBlocked()

const {
  onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'data_scadenza', defaultSortOrder: 'desc' },
})

const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: motivoFilter, onChange: onMotivoChange } = bindSelect('motivo')

// ⛔ Vocabolario CHIUSO, e sono DUE mondi diversi: `SOVRA_INCASSATA` (e' entrato
//    piu' del dovuto) e `MOVIMENTO_CONTRARIO` (un segno che non torna). Due voci
//    statiche e non un lookup: e' un CHECK del backend, non una tabella.
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
        <div class="app-page-filters" :inert="perimetroBloccato">
          <Select
            v-model="motivoFilter"
            :options="opzioniMotivo"
            option-label="label"
            option-value="value"
            :placeholder="t('pagamenti.rate_fuori_capienza.filtro_motivo')"
            show-clear
            style="width: 230px;"
            @update:model-value="onMotivoChange"
          />
        </div>
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
             come cella vuota. -->
        <template #cell-motivo="{ data }">
          <Tag v-if="data.motivo" :value="etichettaMotivo(data.motivo)" severity="warn" />
          <span v-else>—</span>
        </template>

        <!-- ⛔ IL RESIDUO NEGATIVO NON SI MOSTRA COME NUMERO NEGATIVO quando
             descrive denaro di troppo: «-120,00» si legge come un guasto anche
             quando racconta correttamente il mondo. Si dice cosa significa.
             ⚠️ Il segno NON si traduce qui a caso: negativo = e' entrato piu'
             del dovuto, ed e' esattamente la definizione della lista. -->
        <template #cell-residuo="{ data }">
          <Tag
            v-if="Number(data.residuo) < 0"
            :value="t('pagamenti.rate_fuori_capienza.di_troppo', {
              importo: euro(Math.abs(Number(data.residuo))),
            })"
            severity="warn"
          />
          <span v-else>{{ euro(data.residuo) }}</span>
        </template>

        <template #empty>
          <div class="app-empty-state">
            <i class="pi pi-check-circle" />
            <p>{{ t('pagamenti.rate_fuori_capienza.nessuna_rata') }}</p>
          </div>
        </template>
      </ListaConfigurabile>
    </template>
  </div>
</template>
