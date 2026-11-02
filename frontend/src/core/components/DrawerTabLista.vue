<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: lo SCHELETRO di un tab-lista dentro un drawer — il markup che
//        `EmittenteFiscaleBillingAccountTab` si era scritto in casa e che il
//        secondo tab-lista avrebbe ricopiato: barra filtri + PageActionsBar
//        con il tag di stato della configurazione + <ListaConfigurabile>.
//        Estratto 2026-09-01 (regola del 2, ok Tid).
//
// ⭐ E' UN CONTENITORE, NON UNA LISTA. Non fa fetch, non tiene filtri, non sa
//    che colonne esistono: riceve i valori che `useDrawerTabLista` produce e
//    passa avanti TUTTI gli slot al componente di lista. Chi lo usa scrive le
//    stesse `<template #cell-...>` che scriverebbe su <ListaConfigurabile>.
//
// ⛔ GLI SLOT SI INOLTRANO PER NOME, NON SI ELENCANO. Un elenco cablato qui
//    sarebbe un secondo catalogo delle colonne accanto a `ui.lista_colonna`:
//    la colonna nuova comparirebbe nella lista e il suo slot no, senza che
//    niente fallisca. ⚠️ E l'inoltro conserva la CONDIZIONE del caller: uno
//    slot dichiarato con `v-if` (tipicamente `#actions` in sola lettura) non
//    entra in `$slots`, quindi qui non viene creato e <ListaConfigurabile>
//    non monta la colonna — che e' esattamente il comportamento di prima.
//
// ⚠️ QUATTRO NOMI SONO RISERVATI e non si inoltrano — `help`, `testata`,
//    `filtri`, `filtri-sempre`: stanno sopra o dentro la toolbar, che e'
//    markup di questo componente. `testata` e' il posto della form di
//    inserimento quando il tab ne ha una sopra la lista (il mapping BA
//    aggiunge da li', non da un drawer).
//
// ⭐ I DUE SLOT DEI FILTRI SONO I DUE DI `FiltriLista` (2026-09-23, lotto L2
//    del brief dei filtri compatti), e la differenza e' la decisione D2:
//    · `filtri-sempre` la RICERCA — resta a video anche in modalita' compatta,
//      perche' e' il gesto principale della lista;
//    · `filtri` gli altri filtri — in linea su desktop, nel drawer dal basso
//      sotto i 1024px, col segno di quanti ne sono attivi.
//    ⛔ Una ricerca lasciata in `filtri` finisce DENTRO il drawer, dietro due
//    tocchi proprio sul dispositivo in cui digitare costa di piu' — e da
//    desktop non si vede, perche' la' i due slot si rendono uno accanto
//    all'altro. Lo guarda `npm run guard:filtri`, che conosce questi nomi.
import { computed, ref } from 'vue'
import FiltriLista from './FiltriLista.vue'
import ListaConfigurabile from './ListaConfigurabile.vue'
import ListaConfigStatusTag from './ListaConfigStatusTag.vue'
import PageActionsBar from './PageActionsBar.vue'
import Message from 'primevue/message'

const SLOT_PROPRI = ['help', 'testata', 'filtri', 'filtri-sempre']

defineProps({
  // --- identita' e dati della lista (girati a <ListaConfigurabile>) ---
  codice: { type: String, required: true },
  // Lo store-lista del tab — lo stesso che il caller passa a
  // `useDrawerTabLista`. Serve al segno dei filtri attivi e a «Pulisci
  // filtri»: e' il contratto di `FiltriLista` (`chiaviFiltro`,
  // `filtriDefault`, `azzeraFiltri`).
  // ⛔ Non si deriva da `rows`/`total`: quelli sono il risultato, non i filtri.
  // ⭐ Dallo store si legge anche `attesaPadre` (padre composto a meta': il
  //    documento c'e', il suo emittente non ancora), reso come CARICAMENTO —
  //    qui e non nei chiamanti, perche' e' lo stesso per ogni tab-lista, e
  //    senza la lista in attesa mostrerebbe la frase del vuoto su righe che
  //    nessuno ha letto (`useListaStoreCore`, «il padre composto»).
  store: { type: Object, default: null },
  // Girata a <ListaConfigurabile>: l'emittente che il drawer ha gia' fissato.
  // ⭐ E' la ragione per cui un tab-lista dentro il drawer di un emittente non
  //    deve vedere il pannello «scegli un emittente» — ce l'ha davanti.
  emittenteEsplicito: { type: [String, Number], default: null },
  rows: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  paginatorOptions: { type: Object, default: null },
  // ⚠️ Si inoltra, non si decide qui: una lista limitata PER MODELLO (gli
  //    ambiti di un titolo) si monta senza paginatore, e senza questa prop il
  //    contenitore imporrebbe la paginazione a tutti — cioe' deciderebbe al
  //    posto del catalogo. Il building block interno pretende in cambio che
  //    `total` coincida con le righe consegnate, e lo verifica.
  paginata: { type: Boolean, default: true },
  page: { type: Number, default: 1 },
  sortField: { type: String, default: null },
  sortOrder: { type: Number, default: null },
  dataKey: { type: String, default: 'id' },
  // La riga aperta nel form inline (valore di `dataKey`) e se il click apre
  // le righe: inoltrate a <ListaConfigurabile>, che le evidenzia e spegne
  // l'hover (vedi le due prop la').
  rigaAttiva: { type: [String, Number], default: null },
  righeCliccabili: { type: Boolean, default: true },

  // --- testata (dallo scaffolding) ---
  pageActions: { type: Array, default: () => [] },
  dirty: { type: Boolean, default: false },
  // Cancello di perimetro emittente: rende `inert` i filtri del caller. Lo
  // scaffolding lo calcola, la toolbar e' markup nostro — e' l'unico modo che
  // ha di raggiungerla.
  perimetroBloccato: { type: Boolean, default: false },

  // Testo di aiuto in testa al tab. Alternativa allo slot `help`, per il caso
  // — che e' quello frequente — in cui e' una riga sola di testo tradotto.
  helpText: { type: String, default: '' },
})

// ⚠️ `row-click` si INOLTRA, non si assorbe: un contenitore che si tiene un
//    evento del componente che avvolge e' un buco silenzioso — il caller
//    scrive `@row-click`, non fallisce niente, e la riga non si apre. Aggiunto
//    il 2026-09-02 al primo caller che ne aveva bisogno (i titoli IVA del
//    soggetto, che dal click aprono il drawer del titolo).
// ⭐ La firma resta quella del BB: si emette la RIGA, non l'evento PrimeVue
//    (`feedback` del guard `check-liste-configurabili.mjs`).
const emit = defineEmits(['page', 'sort', 'config-loaded', 'row-click'])

const listaInterna = ref(null)

// Gli slot da inoltrare: tutti tranne i tre nostri.
//
// ⛔ E' UNA FUNZIONE, NON UNA `computed`, E LA DIFFERENZA E' UN BUG. L'oggetto
//    degli slot NON e' reattivo: viene rimpiazzato a ogni render, ma non
//    notifica nessuno. Una `computed` che lo legge non ha quindi NESSUNA
//    dipendenza tracciata — si calcola la prima volta e non si ricalcola mai
//    piu'. ⇒ Uno slot condizionato dal caller (`<template v-if="!isReadonly"
//    #actions>`) resterebbe congelato allo stato che aveva al primo render:
//    entrando in sola lettura la colonna azioni non sparirebbe, e uscendone
//    non ricomparirebbe. Chiamata dal template, la funzione gira a ogni render
//    e legge gli slot di ADESSO.
// ⚠️ Si legge `$slots` del template (passato come argomento) e non un
//    `useSlots()` catturato nel setup: sono lo stesso oggetto, ma prendere
//    l'argomento rende esplicito che il valore e' quello del render corrente.
function slotInoltrati(slots) {
  return Object.keys(slots).filter((n) => !SLOT_PROPRI.includes(n))
}

// ⭐ Il caller mette `ref="listaRef"` QUI, non sulla lista interna — che non
//    puo' raggiungere. `useListaAzioni` legge `config`/`dirty`/`colonneNuove`
//    e chiama `openModal()`: le quattro cose viaggiano di rimbalzo.
// ⚠️ `defineExpose` auto-unwrappa i ref, quindi i computed qui sotto arrivano
//    al chiamante gia' come valori (`feedback_defineexpose_unwrap`).
//
// ⛔ E DI RIMBALZO DEVE VIAGGIARE TUTTO CIO' CHE `useListaAzioni` LEGGE, non
//    solo cio' che leggeva il giorno dell'estrazione. Il 18/09 e' nata
//    «Espandi tutte», che legge `haEspansione`/`haRighe`/`tutteEspanse` e
//    chiama `espandiTutte`/`comprimiTutte`: <ListaConfigurabile> li esponeva,
//    questo contenitore no — e l'azione restava invisibile (`visible:
//    haEspansione === true`, su `undefined`) in OGNI lista dentro un drawer o
//    un dialog, senza nessun errore. Rilievo in-app di Tid sulle righe della
//    distinta contabile (2026-09-18). E' la forma «un BB unifica la lettura,
//    non il trasporto» (`feedback_bb_legge_non_trasporta`): il consumatore
//    leggeva un nome che qui nessuno inoltrava.
defineExpose({
  config: computed(() => listaInterna.value?.config ?? null),
  dirty: computed(() => listaInterna.value?.dirty ?? false),
  colonneNuove: computed(() => listaInterna.value?.colonneNuove ?? 0),
  presetAggiornato: computed(() => listaInterna.value?.presetAggiornato ?? false),
  openModal: (...a) => listaInterna.value?.openModal?.(...a),
  save: (...a) => listaInterna.value?.save?.(...a),
  reset: (...a) => listaInterna.value?.reset?.(...a),
  applyChange: (...a) => listaInterna.value?.applyChange?.(...a),
  ignorePresetUpdate: (...a) => listaInterna.value?.ignorePresetUpdate?.(...a),
  // Espansione righe, per l'azione standard «Espandi tutte» di useListaAzioni.
  haEspansione: computed(() => listaInterna.value?.haEspansione === true),
  haRighe: computed(() => listaInterna.value?.haRighe === true),
  tutteEspanse: computed(() => listaInterna.value?.tutteEspanse === true),
  espandiTutte: (...a) => listaInterna.value?.espandiTutte?.(...a),
  comprimiTutte: (...a) => listaInterna.value?.comprimiTutte?.(...a),
})
</script>

<template>
  <div class="app-tab-content">
    <slot name="help">
      <Message v-if="helpText" severity="info" :closable="false">
        {{ helpText }}
      </Message>
    </slot>

    <slot name="testata" />

    <div class="app-page-toolbar">
      <!-- ⚠️ `v-if` sui due slot: un tab-lista senza filtri non deve rendere
           la barra: in modalita' compatta comparirebbe l'icona a imbuto su una
           lista che non ha niente da filtrare. Senza zona sinistra le azioni
           restano a destra per regola di foglio
           (`.app-page-toolbar > .app-page-actions:first-child`). -->
      <FiltriLista
        v-if="$slots.filtri || $slots['filtri-sempre']"
        :store="store"
        :inert="perimetroBloccato"
      >
        <template v-if="$slots['filtri-sempre']" #sempre>
          <slot name="filtri-sempre" />
        </template>
        <!-- ⚠️ ANCHE IL DEFAULT E' CONDIZIONATO, e non e' ridondanza: uno
             `<slot name="filtri" />` scritto senza `v-if` E' un default slot
             per `FiltriLista` anche quando il caller non passa `#filtri` — la
             funzione dello slot esiste, e rende il vuoto. Il building block
             accenderebbe l'icona a imbuto su un drawer senza niente dentro. -->
        <template v-if="$slots.filtri" #default>
          <slot name="filtri" />
        </template>
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaInterna"
      :codice="codice"
      :emittente-esplicito="emittenteEsplicito"
      :rows="rows"
      :total="total"
      :loading="loading || store?.attesaPadre === true"
      :paginator-options="paginatorOptions"
      :paginata="paginata"
      :page="page"
      :sort-field="sortField"
      :sort-order="sortOrder"
      :data-key="dataKey"
      :riga-attiva="rigaAttiva"
      :righe-cliccabili="righeCliccabili"
      @page="emit('page', $event)"
      @sort="emit('sort', $event)"
      @row-click="emit('row-click', $event)"
      @config-loaded="emit('config-loaded', $event)"
    >
      <!-- ⚠️ La frase del vuoto del caller NON si rende mentre la lista carica
           o aspetta il padre: il DataTable disegna la riga vuota anche sotto
           la maschera di caricamento, e «nessuna revisione» sotto lo spinner
           dice una cosa che nessuno ha ancora letto. -->
      <template v-for="nome in slotInoltrati($slots)" #[nome]="scope" :key="nome">
        <slot
          v-if="nome !== 'empty' || !(loading || store?.attesaPadre === true)"
          :name="nome"
          v-bind="scope ?? {}"
        />
      </template>
    </ListaConfigurabile>
  </div>
</template>
