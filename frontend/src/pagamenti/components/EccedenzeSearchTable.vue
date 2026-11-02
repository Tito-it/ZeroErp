<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LE ECCEDENZE DA SISTEMARE — i documenti su cui e' entrato piu' del
//        dovuto, e la decisione che resta a una persona
//        (`<ListaConfigurabile codice="pagamenti.eccedenze">`).
//
// ⭐ ORDINATA PER CLIENTE, non per documento (D15-b), ed e' una decisione di
//    modello: compensare significa mettere insieme due documenti SUOI, quindi
//    la decisione si prende guardando il cliente. Un elenco per documento la
//    nasconderebbe.
// ⭐ L'elenco PRESENTA, non sana: nessuna riga ha un gemello automatico che la
//    corregge, perche' sanarla vorrebbe dire muovere denaro senza che nessuno
//    l'abbia deciso.
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
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useEtichettePagamenti } from '../etichette'
import { formatCurrency } from '../../core/utils/format'
import { SEVERITY_CHI_E_IN_CREDITO } from '../vocabolari'
import { useEccedenzeStore } from '../stores/eccedenze'
import { STATUS_ICONS } from '../../core/constants'
import FiltriLista from '../../core/components/FiltriLista.vue'

const emit = defineEmits(['row-click'])
const { t } = useI18n()
const store = useEccedenzeStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'eccedenza_cliente', defaultSortOrder: 'desc' },
})

const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: creditoFilter, onChange: onCreditoChange } = bindSelect('chi_e_in_credito')

// ⛔ IL VERSO NON E' UN DETTAGLIO: sbagliarlo significa rimborsare cio' che si
//    deve incassare. Per questo e' un filtro esposto e una colonna a Tag, non
//    un segno da leggere dentro un numero.
const { credito: etichettaCredito, opzioniCredito: costruisciOpzioni } = useEtichettePagamenti()
const opzioniCredito = costruisciOpzioni()

// ⚠️ Il colore viene dalla MAPPA, non da un confronto inline: un terzo valore
//    (se il vocabolario si allargasse) cadrebbe nel ramo `else` e si
//    colorerebbe come «azienda in credito» — cioe' direbbe una cosa falsa sul
//    verso, che e' l'unica che qui non si puo' sbagliare. Senza mappa: neutro.
const severityCredito = (c) => SEVERITY_CHI_E_IN_CREDITO[c] || 'secondary'

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
            v-model="creditoFilter"
            class="app-filter-w-md"
            :options="opzioniCredito"
            option-label="label"
            option-value="value"
            :placeholder="t('pagamenti.eccedenze.filtro_credito')"
            show-clear
            @update:model-value="onCreditoChange"
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
        codice="pagamenti.eccedenze"
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
        <!-- ⛔ Il verso del credito, a colori: e' l'informazione da cui dipende
             se si rimborsa o si incassa. Fail-visible sul codice. -->
        <template #cell-chi_e_in_credito="{ data }">
          <Tag
            v-if="data.chi_e_in_credito"
            :value="etichettaCredito(data.chi_e_in_credito)"
            :severity="severityCredito(data.chi_e_in_credito)"
          />
          <span v-else>—</span>
        </template>

        <!-- ⚠️ Gli ATTI IN BOZZA segnalano, non filtrano: una decisione presa e
             non confermata non toglie la riga dall'elenco — l'eccedenza c'e'
             ancora finche' qualcuno non la sistema davvero. Il badge dice «ci
             sta gia' lavorando qualcuno», che e' un'altra cosa. -->
        <template #cell-sistemazioni_in_bozza="{ data }">
          <Tag
            v-if="Number(data.sistemazioni_in_bozza) > 0"
            :value="String(data.sistemazioni_in_bozza)"
            severity="info"
          />
          <span v-else class="app-text-muted">—</span>
        </template>

        <!-- ⚠️ Il residuo qui si mostra COL SUO SEGNO, ed e' voluto: e' il
             verso, non il valore — e la colonna accanto (`chi_e_in_credito`)
             dice gia' a parole di chi sono i soldi. -->
        <template #cell-residuo="{ data }">{{ formatCurrency(data.residuo) }}</template>

        <template #empty>
          <div class="app-empty-state">
            <i :class="STATUS_ICONS.TUTTO_OK" />
            <p>{{ t('pagamenti.eccedenze.nessuna_eccedenza') }}</p>
          </div>
        </template>
      </ListaConfigurabile>
    </template>
  </div>
</template>
