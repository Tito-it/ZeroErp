<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il tab «Revisioni» di un documento di vendita — la catena delle
//        revisioni del documento aperto, come lista a catalogo paginata
//        (`vendite.preventivo_revisioni`, `vendite.offerta_revisioni`).
//        Montato da `PreventiviDrawer` e `OffertaDrawer`.
//
// ⭐ RITIRA `useRevisioniTab` (2026-09-27, brief-db-liste-datatable-grezze §4
//    righe 7 e 8). Quel BB teneva stato + load + reset e lasciava a ciascun
//    drawer la sua `<DataTable>` grezza: due tabelle scritte a mano, con
//    colonne, formattazioni e Tag di stato ricopiati — e la catena intera
//    caricata senza LIMIT. Ora la parte comune e' UNA, ed e' questo
//    componente: lo scaffolding (`useDrawerTabLista` + `<DrawerTabLista>`) e le
//    celle. ⚠️ La versione «cauta» di maggio (niente template condiviso) aveva
//    senso finche' le due tabelle erano diverse; il seed le ha rese GEMELLE —
//    stessi codici colonna (`rev`, `numero`, `data`, `stato`, `attiva`, piu'
//    `totale` sulla sola 7) — e uno slot `cell-stato` vale per entrambe.
//
// ⭐ Cosa resta al chiamante, e perche': il CODICE della lista, lo STORE (uno
//    per documento, dalla factory `createRevisioniStore`: niente stato
//    condiviso fra due drawer aperti insieme), la severita' del Tag di stato
//    (le mappe degli stati sono per documento) e le due frasi del dominio.
//
// ⚠️ Il codice arriva come prop (`:codice`), quindi i presidi statici che
//    leggono `codice="..."` nel sorgente non lo vedono: le due liste sono
//    registrate a mano in `_LISTE` di `test_liste_configurabili_seed`, come
//    `ResiCodaTable` che sceglie fra due costanti.
//
// ⛔ `data` e `totale` NON hanno uno slot: la cella la formatta il catalogo
//    (`date_short`, `currency_eur`), e `attiva` e' `yesno` (Tag Si'/No del BB).
//    Uno slot che rifacesse la formattazione sarebbe una seconda sede del
//    formato, che diverge dal catalogo alla prima modifica.
import { useDrawerTabLista } from '../../../core/composables/useDrawerTabLista'
import DrawerTabLista from '../../../core/components/DrawerTabLista.vue'
import Tag from 'primevue/tag'

const props = defineProps({
  // `vendite.preventivo_revisioni` | `vendite.offerta_revisioni`.
  codice: { type: String, required: true },
  // Lo store del documento (`usePreventivoRevisioniStore()`, ...). ⚠️ Lo
  // passa il chiamante perche' lo legge anche lui: il contatore nell'etichetta
  // del tab e la rilettura dopo un'azione di stato.
  store: { type: Object, required: true },
  // Id del documento aperto. ⚠️ Un documento nuovo fa ripartire la lista da
  // capo (il BB svuota le righe prima di leggere). A drawer CHIUSO il tab e'
  // gia' smontato e la prop non gli arriva: lo store lo azzera il drawer.
  documentoId: { type: Number, default: null },
  // Emittente del documento (PK `emittenti_fiscali.id`). Scioglie il cancello
  // di perimetro per chi vede piu' emittenti, sia sulla config della lista
  // (`emittente-esplicito`) sia sui dati (vedi `createRevisioniStore`).
  emittenteFiscaleId: { type: Number, default: null },
  // `(stato_codice_interno) => severity` del Tag di stato del documento.
  severity: { type: Function, required: true },
  // Frase in testa al tab e frase della lista vuota, gia' tradotte.
  intro: { type: String, default: '' },
  vuoto: { type: String, default: '' },
})

// Il padre dello store: documento + emittente, il padre COMPOSTO del core
// (vedi `createRevisioniStore`). Finche' manca l'emittente, che arriva col
// dettaglio, la lista non legge e resta in caricamento: partire senza vorrebbe
// dire una prima chiamata sbarrata dal cancello per chi vede piu' emittenti.
// Nessun `searchTableOptions`: l'ordinamento di partenza lo dichiara lo store
// (`rev` / `revisione_numero` ASC), e una seconda copia qui divergerebbe.
const {
  onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useDrawerTabLista(props.store, {
  parentId: {
    documentoId: () => props.documentoId,
    emittenteId: () => props.emittenteFiscaleId,
  },
})
</script>

<template>
  <DrawerTabLista
    ref="listaRef"
    :codice="codice"
    :store="store"
    :emittente-esplicito="emittenteFiscaleId"
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
    :help-text="intro"
    @page="onPage"
    @sort="onSort"
    @config-loaded="onConfigLoaded"
  >
    <!-- La frase del dominio, e solo se la lettura e' riuscita: con
         `erroreCaricamento` la lista e' vuota per un'altra ragione. -->
    <template #empty>
      <span v-if="!store.erroreCaricamento">{{ vuoto }}</span>
    </template>
    <!-- Colonna gemella `stato` (campo `stato_descrizione`): il Tag col colore
         dello stato INTERNO, che il catalogo porta nella colonna nascosta
         `stato_codice_interno` — la riga lo ha anche se la colonna e' spenta. -->
    <template #cell-stato="{ data }">
      <Tag :value="data.stato_descrizione" :severity="severity(data.stato_codice_interno)" />
    </template>
  </DrawerTabLista>
</template>
