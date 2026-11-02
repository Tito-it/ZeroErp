<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA LISTA DELLE DISTINTE CONTABILI — la porta d'ingresso del dominio
//        incassi (`<ListaConfigurabile codice="pagamenti.distinte">`,
//        scaffolding in `useListaConfigurabilePage`).
//
// ⭐ Che cos'e' una distinta: il foglio su cui si raccoglie il denaro arrivato
//    in un giorno da un canale — a mano, importato o generato. Da qui si apre,
//    si digitano le righe, si abbinano alle rate e infine si REGISTRA, che e'
//    l'unico gesto irreversibile del cantiere.
//
// ⭐ La ricerca (brief-be-ricerca-full-liste-residue §5.3): la casella sta nel
//    `#sempre` di `FiltriLista`, che la rende solo se la configurazione dice
//    `ricerca_full` — le colonne le decide il catalogo, non questo file.
// ⚠️ Niente export: il backend non espone `/export/` per questo dominio, e dal
//    2026-07-31 il BB il pulsante non lo mette se non gli passi `exportFn`. Un
//    pulsante che apre un dialogo inerte e' peggio della sua assenza.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Select from 'primevue/select'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { statoDistintaSeverity } from '../../core/utils/severity'
import { useEtichettePagamenti } from '../etichette'
import { formatCurrency } from '../../core/utils/format'
import { useDistinteStore } from '../stores/distinte'
import { STATUS_ICONS } from '../../core/constants'
import FiltroPeriodo from '../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useDistinteStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  // ⭐ «Apri distinta» e non «Nuovo»: il gesto ha un nome nel dominio, e non e'
  //    una creazione qualunque — e' un *get or create* che puo' RIDARTI quella
  //    di stamattina (Q-3). Il BB monta l'azione solo perche' passiamo `onNew`.
  onNew: () => emit('new'),
  newTooltipKey: 'pagamenti.distinte.apri_tooltip',
  searchTableOptions: { defaultSortField: 'data_contabile', defaultSortOrder: 'desc' },
})

const { bindSelect, bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato')
const { value: origineFilter, onChange: onOrigineChange } = bindSelect('origine')
const { value: centroFilter, onChange: onCentroChange } = bindSelect('centro_riscossione_id')
const { value: canaleFilter, onChange: onCanaleChange } = bindSelect('ente_incasso_id')
// Il periodo e' UN filtro con due estremi: un binding, un componente.
const periodo = bindPeriodo()

// ⛔ L'ORIGINE e' un vocabolario chiuso di tre valori, ed e' un CHECK del
//    database (`MANUALE` | `AUTOMATICA` | `GENERATA`): un Select statico, non un
//    lookup — un round-trip per tre voci e' lavoro sprecato.
// ⚠️ Gli STATI invece NON si cablano: sono una tabella di catalogo e li serve il
//    lookup generico, che e' gia' in whitelist. Cablarli qui vorrebbe dire
//    riscrivere un vocabolario che vive a DB, e il giorno che ne nasce uno
//    nuovo il filtro lo nasconderebbe senza dirlo.
// ⚠️ Fail-visible come gli altri vocabolari del dominio: un'origine che il
//    database aggiunge e i locales non conoscono si vede come CODICE. Con `t()`
//    diretto a video sarebbe finito il PATH della chiave
//    («pagamenti.distinte.origine_xxx»), che non e' un'etichetta ne' un errore.
const { origineDistinta: etichettaOrigine, opzioniOrigineDistinta } = useEtichettePagamenti()
const opzioniOrigine = opzioniOrigineDistinta()

function onRowClick(data) { emit('row-click', data) }

// ⭐ Coda di lavoro: carica subito, senza aspettare un filtro. Non e' una lista
//    storica — l'arretrato e' proprio cio' che si viene a vedere.
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
          <LookupSelect
            v-model="statoFilter"
            class="app-filter-w-md"
            rel="pagamenti.vendite_contabili_stati"
            value-field="codice_interno"
            :placeholder="t('pagamenti.distinte.filtro_stato')"
            show-clear
            :filter="false"
            @change="onStatoChange"
          />
          <Select
            v-model="origineFilter"
            class="app-filter-w-md"
            :options="opzioniOrigine"
            option-label="label"
            option-value="value"
            :placeholder="t('pagamenti.distinte.filtro_origine')"
            show-clear
            @update:model-value="onOrigineChange"
          />
          <LookupSelect
            v-model="centroFilter"
            class="app-filter-w-md"
            rel="pagamenti.centri_riscossione"
            :placeholder="t('pagamenti.distinte.filtro_centro')"
            show-clear
            @change="onCentroChange"
          />
          <LookupSelect
            v-model="canaleFilter"
            class="app-filter-w-md"
            rel="pagamenti.enti_incasso"
            :placeholder="t('pagamenti.distinte.filtro_canale')"
            show-clear
            @change="onCanaleChange"
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

      <ListaConfigurabile
        ref="listaRef"
        codice="pagamenti.distinte"
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
        <!-- ⚠️ I nomi degli slot sono i `codice` delle colonne A CATALOGO, non i
             `campo_sorgente`: qui la colonna si chiama `stato` e il campo che
             legge e' `stato_descrizione`. Uno slot col nome sbagliato non da'
             nessun errore — la cella ripiega sul valore grezzo e il Tag colorato
             sparisce in silenzio. Il nome si legge dal seed. -->
        <template #cell-stato="{ data }">
          <Tag
            :value="data.stato_descrizione || data.stato_codice"
            :severity="statoDistintaSeverity(data.stato_codice)"
          />
        </template>

        <!-- L'origine dice CHI ha creato la distinta, ed e' la differenza fra
             «l'ho digitata io» e «e' arrivata da un flusso»: neutra, non e' uno
             stato e non colora un giudizio. -->
        <template #cell-origine="{ data }">
          <Tag
            v-if="data.origine"
            :value="etichettaOrigine(data.origine)"
            severity="secondary"
          />
          <span v-else>—</span>
        </template>

        <!-- ⭐ LO SCARTO E' IL NUMERO PER CUI LA COLONNA ESISTE: e' la
             differenza fra quanto e' stato digitato e quanto l'operatore aveva
             DICHIARATO all'apertura. Zero = quadra. Diverso da zero = c'e'
             qualcosa da guardare, e si accende.
             ⚠️ `null` NON e' zero: significa «non e' stato dichiarato niente»,
             quindi la quadratura non si applica — e mostrarlo come 0,00
             direbbe «quadra» di una distinta che nessuno ha mai quadrato. -->
        <template #cell-scarto_dichiarato="{ data }">
          <span v-if="data.scarto_dichiarato == null" class="app-text-muted">—</span>
          <Tag
            v-else-if="Number(data.scarto_dichiarato) !== 0"
            :value="formatCurrency(data.scarto_dichiarato)"
            severity="warn"
          />
          <span v-else>{{ formatCurrency(data.scarto_dichiarato) }}</span>
        </template>

        <!-- Quante righe sono pronte per la registrazione, sul totale. Le due
             cifre insieme dicono a colpo d'occhio quanto lavoro resta. -->
        <template #cell-righe_registrabili="{ data }">
          {{ data.righe_registrabili ?? 0 }} / {{ data.righe_totali ?? 0 }}
        </template>

        <template #empty>
          <div class="app-empty-state">
            <i :class="STATUS_ICONS.VUOTO" />
            <p>{{ t('pagamenti.distinte.nessuna_distinta') }}</p>
          </div>
        </template>
      </ListaConfigurabile>
    </template>
  </div>
</template>

