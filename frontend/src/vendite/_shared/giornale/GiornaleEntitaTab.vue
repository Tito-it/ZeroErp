<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la STORIA di un'entita' — «cosa e' successo a questa cosa, in che
//        ordine» — come tab-lista dentro il suo drawer: la lista a catalogo
//        `vendite.giornale` filtrata sulla fattura (`FatturaDrawer`) o sul
//        lotto e le sue fatture (`LottoDrawer`).
//
// ⭐ UN COMPONENTE PER DUE DRAWER, e una lista per tre schermate (decisione di
//    Tid, 2026-09-27, brief-db-liste-datatable-grezze §3.1): fino a quel giorno
//    i due drawer avevano ciascuno la sua `DataTable` grezza con le colonne
//    scritte a mano, e il giornale trasversale una terza resa. Le colonne
//    Entita'/Riferimento servono anche qui: la Storia del lotto mescola il
//    lotto e le sue fatture per costruzione.
//
// ⭐ Lo STORE lo passa il drawer (`useFatturaGiornaleStore` /
//    `useLottoGiornaleStore`): ne legge il totale per l'etichetta della
//    scheda, e i due store sono separati perche' i due drawer si aprono uno
//    dentro l'altro. Il filtro «solo problemi» compare se lo store lo DICHIARA
//    (`info` fra i suoi filtri, solo il lotto): una sede sola, niente prop
//    gemella che possa dire il contrario.
//
// ⚠️ L'EMITTENTE del documento viaggia in due posti, per due domande: alla
//    configurazione della lista (`emittente-esplicito`, «la schermata e'
//    leggibile?») e alla lettura delle righe (una parte del padre composto,
//    che lo store manda come `emittente_soggetto_ruolo_id`). Senza, chi ha piu'
//    emittenti nello scope vedrebbe il pannello «scegli un emittente» dentro
//    un drawer gia' aperto.
//
// ⚠️ Sta dentro `app-drawer-content`, che in LETTURA diventa `.app-readonly`:
//    paginatore, intestazioni e filtri restano cliccabili per regola di foglio
//    (leggere non e' scrivere); il SelectButton porta comunque `app-escape`.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import DrawerTabLista from '../../../core/components/DrawerTabLista.vue'
import { useDrawerTabLista } from '../../../core/composables/useDrawerTabLista'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { STATUS_ICONS } from '../../../core/constants'
import GiornaleCella from './GiornaleCella.vue'
import { GIORNALE_CELLE } from './giornaleCelle'

const props = defineProps({
  // Lo store-lista della Storia (una delle due istanze di `giornaleEntita`).
  store: { type: Object, required: true },
  // L'id dell'entita' (fattura o lotto). `null` = nessuna: lo store si svuota.
  entitaId: { type: [Number, null], default: null },
  // ⚠️ Il SOGGETTO-RUOLO dell'emittente, non la PK di `emittenti_fiscali`
  //    (`feedback_emittente_pk_vs_soggetto_ruolo`): e' la colonna che fattura
  //    e lotto portano nel dettaglio, NOT NULL su entrambi.
  emittenteSoggettoRuoloId: { type: [Number, null], default: null },
})

const { t } = useI18n()

// ⭐ IL PADRE E' LA COPPIA (entita', emittente): il padre composto del core. Le
//    due parti le segue il `watch` del BB — la fetch parte con l'emittente
//    gia' dentro, e finche' manca la lista aspetta (`attesaPadre`).
const padre = {
  entitaId: () => props.entitaId,
  emittenteId: () => props.emittenteSoggettoRuoloId,
}

// ⭐ CAMBIO DI ENTITA' = SI RIPARTE DA CAPO (righe, filtri, ordine di
//    partenza): lo fa il BB, per ogni tab-lista — la Storia riparte sempre
//    dallo stesso punto, come le altre schede del drawer.

const {
  onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useDrawerTabLista(props.store, {
  parentId: padre,
  // Nessun `searchTableOptions`: l'ordinamento di partenza lo dichiara lo
  // store (il preset, `quando desc`), e una seconda copia qui divergerebbe.
})

// ⭐ «Solo problemi» esiste se lo store lo dichiara (solo il lotto).
const haFiltroInfo = computed(() => props.store.chiaviFiltro.includes('info'))
const { value: infoFilter, onChange: onInfoChange } = useStoreFilterBindings(
  props.store, applyFilters,
).bindSelect('info', { defaultValue: false })

// ⚠️ Niente `severity` sulle due voci: non sono livelli di gravita' — «Tutto»
//    non e' piu' grave di «Solo problemi», e' piu' largo.
const opzioniInfo = computed(() => [
  { value: false, label: t('vendite.giornale.storia_solo_problemi') },
  { value: true, label: t('vendite.giornale.storia_tutto') },
])
</script>

<template>
  <DrawerTabLista
    ref="listaRef"
    codice="vendite.giornale"
    data-key="riga_key"
    :store="store"
    :emittente-esplicito="emittenteSoggettoRuoloId"
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
    @config-loaded="onConfigLoaded"
  >
    <!-- Sopra la barra, dentro il contenitore del tab (`testata`, slot suo). -->
    <template #testata>
      <!-- ⛔ «Non sono riuscito a leggere la storia» non e' «non e' successo
           niente»: a lista vuota i due si leggerebbero uguali, quindi l'avviso
           sta qui sopra e l'empty-state del dominio tace. -->
      <Message v-if="store.erroreCaricamento" severity="warn" :closable="false" size="small">
        {{ t('vendite.giornale.storia_non_caricata') }}
      </Message>
      <!-- Il conto di cio' che il filtro toglie, quando c'e' qualcosa da
           mostrare: sull'elenco vuoto lo dice gia' l'empty-state. ⛔ E' meta'
           del mestiere di nascondere: «tre problemi» e «tre problemi e 173
           passi andati bene» sono due schermate diverse. -->
      <p v-if="store.infoCount > 0 && store.items.length" class="app-drawer-header-muted">
        {{ t('vendite.giornale.storia_info_nascoste', { n: store.infoCount }) }}
      </p>
      <p v-if="store.ritirateCount > 0 && store.items.length" class="app-drawer-header-muted">
        {{ t('vendite.giornale.ritirate_nascoste', { n: store.ritirateCount }) }}
      </p>
    </template>

    <template v-if="haFiltroInfo" #filtri>
      <!-- ⚠️ Nuova DOMANDA al server, non un filtro in memoria: l'elenco e'
           paginato, e filtrare qui filtrerebbe la sola pagina caricata. -->
      <SelectButton
        v-model="infoFilter"
        class="app-escape app-filtro-largo"
        :options="opzioniInfo"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        @change="onInfoChange"
      />
    </template>

    <!-- ⛔ QUATTRO vuoti diversi, e vanno detti diversi: «non sono riuscito a
         chiederlo» (l'avviso qui sopra), «e' successo tutto ed e' routine», «e'
         successo tutto ed e' stato superato», «non e' successo niente». -->
    <template #empty>
      <div v-if="!store.erroreCaricamento" class="app-empty-state">
        <i :class="STATUS_ICONS.TUTTO_OK" />
        <p v-if="store.infoCount > 0">
          {{ t('vendite.giornale.storia_solo_info', { n: store.infoCount }) }}
        </p>
        <p v-else-if="store.ritirateCount > 0">
          {{ t('vendite.giornale.storia_solo_ritirate', { n: store.ritirateCount }) }}
        </p>
        <p v-else>{{ t('vendite.giornale.storia_vuota') }}</p>
      </div>
    </template>

    <template v-for="codice in GIORNALE_CELLE" :key="codice" #[`cell-${codice}`]="{ data }">
      <GiornaleCella :codice="codice" :riga="data" />
    </template>
  </DrawerTabLista>
</template>
