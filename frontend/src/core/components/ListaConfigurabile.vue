<script setup>
// Scopo: Wrapper PrimeVue DataTable parametrizzato dalla configurazione
// risolta dal BE (`ui.fn_resolve_lista_config`). Costruisce le colonne
// dinamicamente, applica `tipo_colonna` per le icon column / azione,
// `fissata` per frozen, `esportabile` per filtrare l'export.
//
// Confine di responsabilita': il componente si occupa SOLO della
// configurazione di presentazione. Il caller fornisce i dati riga
// (`rows`), il `total`, il `loading`, e gestisce paginazione/sort
// reagendo agli eventi `@page`/`@sort`/`@filter`. Tipico:
//
// ⭐ DUE MODALITA', e la prop che le separa e' `paginata` (default `true`).
//
//   `paginata` (default)   il caller pagina lato server: `rows` e' UNA PAGINA,
//                          `total` e' il conteggio vero, il BB monta il
//                          paginator ed emette `@page`/`@sort` perche' sia il
//                          caller a rifare la fetch.
//
//   `:paginata="false"`    la lista NON pagina: `rows` sono TUTTE le righe.
//                          Niente paginator, ordinamento LOCALE di PrimeVue,
//                          e `@page`/`@sort` NON vengono emessi (non c'e'
//                          niente da rifetchare).
//
// ⛔ «Non paginata» NON vuol dire «senza `total`»: vuol dire
//    **`rows.length === total`**, e il BB lo VERIFICA (vedi
//    `troncamentoSospetto`). E' l'unico difetto muto che questa modalita'
//    introduce, ed e' il motivo per cui il guard esiste — vedi il blocco
//    sopra la computed.
//
// ⚠️ DIVERGENZA DICHIARATA, non presidiabile: con `paginata: false` l'ordine
//    lo decide PrimeVue in locale, e non e' l'ordine del database. Su NULL,
//    accenti e numeri tenuti come testo i due possono differire — e la regola
//    di casa sulle date (`valido_al DESC` con `COALESCE(col,'infinity')`,
//    `feedback_ordinamento_validita_infinity`) in locale semplicemente non
//    esiste. Qui `nullSortOrder` e' impostato ESPLICITAMENTE a 1 (NULL in
//    fondo) per non lasciarlo a un default implicito, ma resta una scelta del
//    componente, non la semantica del server.
//    ⇒ Una lista in cui l'ordinamento dei NULL e' informazione va tenuta
//      `paginata: true`, oppure vuole un comparatore esplicito — che questo
//      building block oggi non ha.
//    ⚠️ In modalita' paginata `nullSortOrder` e' inerte (con `lazy` PrimeVue
//      non ordina): le liste esistenti non cambiano comportamento.
//
//   <ListaConfigurabile
//     codice="anagrafiche.clienti"
//     :rows="store.items"
//     :total="store.total"
//     :loading="store.loading"
//     @page="onPage"
//     @sort="onSort"
//     @row-click="onRowClick"
//   >
//     <template #cell-data_attivazione="{ value }">{{ displayDate(value) }}</template>
//     <template #cell-stato="{ data }">
//       <Tag :value="data.stato_descrizione" :severity="statoClienteSeverity(data.stato_codice)" />
//     </template>
//     <template #actions="{ data }">
//       <!-- il kebab sotto spazio stretto arriva da se' (`CellaAzioniRiga`) -->
//       <RowActionsMenu :row="data" :actions="buildActions(data)" />
//     </template>
//   </ListaConfigurabile>
//
// Render slot priorita':
//   1. slot dinamico `cell-{codice}` per la colonna (massima priorita')
//   2. formatter built-in da `formato` (`date_short`, `currency_eur`, ecc.)
//   3. fallback grezzo `data[codice]`
//
// Le colonne con `tipo_colonna='azione'` non hanno field e si renderizzano
// via slot `actions`. L'app cliente passa il proprio RowActionsMenu.
//
// Dettaglio inline (master-detail): slot `row-expansion` + `v-model:expanded-rows`
// se la pagina deve pilotare l'apertura delle righe.
//   <ListaConfigurabile v-model:expanded-rows="expandedRows" ...>
//     <template #row-expansion="{ data }"> ...tabella figlia... </template>
// Convive col ritiro dinamico: a riga aperta si vedono prima le colonne
// ritirate, poi il dettaglio.
//
// ⛔ NIENTE SCROLLBAR ORIZZONTALE, per costruzione (2026-09-18, decisione Tid):
//    in modalita' responsive la larghezza di catalogo e' anche il TETTO della
//    cella (`--col-w` + `.app-lista-cella`, main.css), quindi la tabella rende la
//    somma che il packing ha calcolato e la colonna azioni resta sempre
//    l'ultima a video. Un contenuto piu' lungo va in ellissi col testo intero
//    nel `title`; le colonne in eccesso stanno nella riga di espansione, e
//    «Espandi tutte» (useListaAzioni) le apre tutte insieme.
//    La sola larghezza che il catalogo non conosce e' quella dei pulsanti
//    inline della colonna azioni: la dichiara il chiamante con `azioni-inline`.

import { computed, nextTick, ref, onMounted, watch, useSlots } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'
import Button from 'primevue/button'
import { MANAGE_ICONS } from '../constants'
import { etichettaColonna } from '../utils/i18nLabel'
import { useListaConfig } from '../composables/useListaConfig'
import { drawerAperti } from '../composables/useDrawerInCima'
import {
  useResponsiveColumns,
  larghezzaAzioniInline,
  DEFAULT_COL_WIDTH,
  DEFAULT_ACTIONS_INLINE_COUNT,
} from '../composables/useResponsiveColumns'
import CellaAzioniRiga from './CellaAzioniRiga.vue'
import CellaConfigurabile, { testoCella } from './CellaConfigurabile.vue'
import ListaColonneModal from './ListaColonneModal.vue'
import { USO_MISURA, misuraDefault, misureOpzioni } from '../misurePagina'

// Default paginator allineato al pattern lista standard
// (paginatorPosition=top, JumpToPageDropdown 1/N, font compatto).
// Il caller puo' override passando paginatorProps di useSearchTable o
// un oggetto custom via la prop `paginator-options`.
// `removable-sort` + striped + scrollable restano fissati: sono regole del
// pattern, non parametriche (vedi frontend-standards.md).
// ⚠️ `lazy` e `paginator` NON sono piu' fra quelli: li governa la prop
//    `paginata` (2026-09-02). Erano cablati, e quella costante era l'unica
//    ragione per cui una lista senza paginazione server-side non poteva usare
//    il catalogo colonne — cioe' un cancello che presidiava una cosa sola
//    davanti a cinque benefici che non c'entravano niente.
const _DEFAULT_PAGINATOR_OPTIONS = Object.freeze({
  paginator: true,
  paginatorPosition: 'top',
  paginatorTemplate:
    'FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink ' +
    'RowsPerPageDropdown JumpToPageDropdown CurrentPageReport',
  currentPageReportTemplate: '{currentPage}/{totalPages}',
  rowsPerPageOptions: misureOpzioni(),
})

// Ordine dei NULL nell'ordinamento LOCALE (modalita' non paginata).
// PrimeVue: `1` = «Excel like sort nulls at bottom» — verificato nel sorgente
// di `@primeuix/utils` (`sort.ts`), dove e' anche il valore di default.
// ⭐ Lo passiamo ESPLICITO proprio perche' e' il default: su una lista non
//    paginata l'ordine lo decide il browser, e una scelta ereditata in silenzio
//    da una libreria non e' una scelta — e' un default che nessuno ha visto.
// ⚠️ In modalita' paginata e' inerte (con `lazy` PrimeVue non ordina).
const NULL_IN_FONDO = 1

const props = defineProps({
  // Codice stabile della lista (es. 'anagrafiche.clienti').
  codice: { type: String, required: true },
  // Emittente GIA' fissato dal contesto che apre la lista — oggi il tab dentro
  // il drawer di un emittente. ⭐ Non filtra niente qui: viaggia al backend con
  // la richiesta di config, ed e' quello che gli permette di rispondere
  // `richiede_scelta_emittente: false` su una lista non certificata
  // multi-emittente. Senza, il pannello del cancello chiederebbe di scegliere
  // l'emittente che l'operatore ha gia' aperto davanti.
  // ⚠️ I dati della lista li fetcha il CALLER: sta a lui filtrare per lo stesso
  //    emittente. Qui la prop non tocca le righe.
  emittenteEsplicito: { type: [String, Number], default: null },
  // Dati riga forniti dal caller (no fetch interno).
  // ⚠️ Con `paginata: false` sono TUTTE le righe, non una pagina.
  rows: { type: Array, default: () => [] },
  // Conteggio totale.
  //  - `paginata: true`  → conteggio server-side, alimenta il paginator;
  //  - `paginata: false` → resta OBBLIGATORIO, e diventa l'ASSERZIONE che le
  //    righe siano tutte: il BB confronta `rows.length` con questo numero e
  //    rifiuta di disegnare la tabella se divergono (`troncamentoSospetto`).
  total: { type: Number, default: 0 },
  // Modalita' di paginazione della lista. `true` (default) = il caller pagina
  // lato server. `false` = la lista non pagina: niente paginator, ordinamento
  // locale, nessun evento `@page`/`@sort`.
  //
  // ⛔ NON e' un'opzione di comodo per saltare la paginazione. Si mette
  //    `false` quando la popolazione e' limitata PER MODELLO (una riga per
  //    voce di catalogo, le utility di un emittente, i reparti), non quando
  //    «oggi sono poche»: il giorno che diventano molte il guard qui sotto
  //    accende un errore invece di mostrare una lista troncata, ma la lista
  //    resta comunque da riportare su `paginata: true`.
  paginata: { type: Boolean, default: true },
  // Loading flag controllato dal caller.
  loading: { type: Boolean, default: false },
  // Pagina corrente 1-based (display nel paginator).
  page: { type: Number, default: 1 },
  // Field e direction correnti per l'header sortable.
  sortField: { type: String, default: null },
  sortOrder: { type: Number, default: null }, // 1 asc, -1 desc, null
  // Selection mode (vedi PrimeVue DataTable). Default 'single'.
  selectionMode: { type: String, default: 'single' },
  // Data key per riga.
  dataKey: { type: String, default: 'id' },
  // ⭐ LA RIGA APERTA NEL FORM INLINE del contenitore (il suo valore di
  //    `dataKey`), evidenziata (2026-10-04, §9.6 punto 2 del brief-db-liste-
  //    righe-documento, Tid: «si evidenzia»). Con il form sotto la lista,
  //    senza l'evidenza non si vede QUALE riga si sta modificando — la
  //    `DataTable` grezza di prima la mostrava selezionata. `null` = nessuna.
  // ⭐ Dal 2026-10-04 la riga aperta in un DRAWER si evidenzia da sola (vedi
  //    `rigaApertaDalClic`): questa prop serve quando il «dove sono» non nasce
  //    da un click (form inline, deep-link), e quando c'e' VINCE.
  rigaAttiva: { type: [String, Number], default: null },
  // Le righe si aprono col click? `false` (documento non modificabile, sola
  // lettura): niente hover ne' cursore a mano, che prometterebbero un click
  // che non fa niente.
  righeCliccabili: { type: Boolean, default: true },
  // Override prop paginator: tipicamente `paginatorProps` di useSearchTable.
  // Mergiato con i default del pattern (top + jump + 1/N + rowsOptions).
  // Le prop esplicite del caller hanno precedenza sui default.
  paginatorOptions: { type: Object, default: null },
  // Ritiro dinamico colonne (packing a somma via ResizeObserver) per evitare
  // la scrollbar orizzontale quando lo spazio si stringe (es. apertura
  // sidebar). Le colonne ritirate finiscono in una riga di espansione (zero
  // dati persi). Default true: tutte le liste configurabili ne beneficiano
  // (uniformita' UI). La priorita' di ritiro arriva dal catalogo
  // (`ui.lista_colonna.priorita`, esposta da fn_resolve_lista_config).
  responsive: { type: Boolean, default: true },
  // Quanti pulsanti INLINE puo' avere al massimo la colonna azioni (la
  // variante desktop di `RowActionsMenu`, un'icona per azione). E' la riserva
  // che il packing tiene per quella colonna prima di ritirare colonne dati:
  // il chiamante e' l'unico a saperlo, perche' e' lui che scrive
  // `buildRowActions`. Default 4; Clienti ne dichiara 6.
  // ⚠️ Un numero piu' basso del vero non taglia nulla — la colonna azioni
  //    resta alla sua larghezza naturale — ma la differenza esce dal
  //    contenitore come scrollbar orizzontale, che e' esattamente cio' che il
  //    packing esiste per evitare.
  azioniInline: { type: Number, default: DEFAULT_ACTIONS_INLINE_COUNT },
  // Stato di espansione PILOTATO dal caller (`v-model:expanded-rows`), per le
  // liste master-detail che devono aprire/chiudere righe da sole (es. listini:
  // "espandi tutte", toggle da azione di riga, fetch lazy del dettaglio).
  // Omesso (default `null`) = la lista gestisce l'espansione da se', che e' il
  // caso di tutte le liste senza dettaglio inline.
  //
  // ⚠️ Quando e' pilotato, la lista NON azzera piu' lo stato: chi lo possiede
  // decide anche quando svuotarlo. Azzerarlo qui cancellerebbe le righe che il
  // caller ha appena riaperto (su listini, tutte, a ogni fetch).
  expandedRows: { type: Object, default: null },
})

const emit = defineEmits([
  'page',
  'sort',
  'row-click',
  'config-loaded',
  'update:expandedRows',
])

const { t, te } = useI18n()
const slots = useSlots()

// Stato config (cascata BE) tramite composable per-codice.
const {
  config,
  catalogo,
  dirty,
  loading: configLoading,
  colonneNuove,
  presetAggiornato,
  load,
  ensureCatalogo,
  applyChange,
  save,
  reset,
  ignorePresetUpdate,
} = useListaConfig(props.codice, {
  emittenteEsplicito: () => props.emittenteEsplicito,
})

// Stato modale di personalizzazione.
const modalVisible = ref(false)

// Cancello di perimetro emittente (P-2b). ⚠️ E' il BACKEND a deciderlo:
// `richiede_scelta_emittente` arriva gia' calcolato nell'envelope, perche' la
// cardinalita' dello scope la conosce solo lui. Qui non si ricalcola niente —
// ricalcolarlo sarebbe una seconda sede della stessa verita'.
const perimetroBloccato = computed(
  () => config.value?.richiede_scelta_emittente === true,
)

// Scopo: caricare la config e DIRLO al caller. Il secondo pezzo non e'
//        decorativo: dentro `config-loaded` viaggia anche
//        `richiede_scelta_emittente`, da cui lo scaffolding di pagina decide
//        se mostrare la lista o il pannello e se sospendere le fetch.
// ⚠️ Un solo evento, e non uno dedicato al cancello. C'e' stato anche
//    `@perimetro-bloccato`, tolto il 2026-08-18: nessuno lo ascoltava e diceva
//    la stessa cosa che `config-loaded` porta gia' dentro. Chi la legge e'
//    `useListaConfigurabilePage`, sede unica dello scaffolding di pagina — due
//    strade per la stessa verita' divergono alla prima modifica.
async function loadEdEmetti() {
  const data = await load()
  if (data) emit('config-loaded', data)
}

onMounted(loadEdEmetti)

// ⭐ Si guarda la PRESENZA, non il valore: la risposta del backend dipende dal
//    fatto che UN emittente sia fissato, non da QUALE. Cambiare emittente
//    dentro il drawer non cambia `richiede_scelta_emittente`, e ricaricare la
//    config a ogni cambio sarebbe un round-trip per una risposta identica.
const emittenteFissato = computed(
  () => props.emittenteEsplicito !== null
    && props.emittenteEsplicito !== undefined
    && props.emittenteEsplicito !== '',
)

// ⚠️ L'emittente esplicito puo' arrivare DOPO il primo render (il drawer si
//    apre e poi passa l'id): la config e' gia' stata chiesta senza, e la
//    risposta era «scegli un emittente». Questa e' l'unica transizione che
//    cambia qualcosa.
watch(emittenteFissato, async (ora, prima) => {
  if (ora && !prima) await loadEdEmetti()
})

// Re-fetch se il codice cambia (caso raro: tab switch dinamico).
// ⚠️ Ricaricare SENZA riemettere l'evento era un difetto: il pannello del
//    cancello si aggiornava (lo calcola questo componente dalla `config`) ma
//    lo stato di pagina no — restava quello della lista PRECEDENTE, e con
//    esso la sospensione delle fetch. Chi carica dice sempre cosa ha caricato.
watch(
  () => props.codice,
  async (newCodice, oldCodice) => {
    if (newCodice && newCodice !== oldCodice) {
      await loadEdEmetti()
    }
  },
)

// Colonne renderizzate: dalla config + arricchite del campo_sorgente
// per poter accedere ai dati. Quando il catalogo non e' ancora caricato,
// i metadati estesi (etichetta, formato, ecc.) sono lookup-fallback al
// codice stesso.
const colonneRender = computed(() => {
  const cols = config.value?.colonne ?? []
  const meta = new Map()
  for (const c of catalogo.value?.colonne ?? []) {
    meta.set(c.codice, c)
  }
  return cols
    .filter((c) => c.visibile !== false)
    .map((c) => {
      const m = meta.get(c.codice) || {}
      // Risoluzione header multilingua: sede unica in `etichettaColonna`
      // (chiave dalla CONFIG, poi dal catalogo, poi le etichette letterali).
      // ⚠️ Prima la chiave si cercava SOLO nei metadati del catalogo, che
      // l'endpoint non restituiva: nessuna colonna si e' mai tradotta, in
      // nessuna lista — e il guard `te` lo rendeva silenzioso. La chiave
      // della config arriva invece a ogni richiesta (`fn_resolve_lista_config`).
      const header = etichettaColonna(t, te, { config: c, meta: m })
      return {
        codice: c.codice,
        ordine: c.ordine,
        // Peso di ritiro dinamico (packing a somma). Arriva da
        // fn_resolve_lista_config (ui.lista_colonna.priorita). Default 50
        // (mid-pack) coerente col DB se assente.
        priorita: c.priorita ?? 50,
        larghezza: c.larghezza ?? m.larghezza_default ?? null,
        fissata: c.fissata === true,
        esportabile: c.esportabile !== false,
        tipo_colonna: c.tipo_colonna || m.tipo_colonna || 'informazione',
        // Dal catalogo. Se non ancora caricato il fallback al `codice`
        // protegge il primo render; con load-eager non e' piu' raggiungibile.
        etichetta: header,
        campo_sorgente: m.campo_sorgente || c.codice,
        formato: m.formato || null,
        allineamento: m.allineamento || 'left',
        ordinabile: m.ordinabile !== false,
        // ⭐ Serve al VERSO DI PARTENZA dell'ordinamento (vedi `onSort`): una
        //    colonna data si legge dalla piu' recente. `c` prima di `m` perche'
        //    la config arriva a ogni richiesta, il catalogo e' un secondo giro.
        tipo_dato: c.tipo_dato || m.tipo_dato || null,
      }
    })
    .sort((a, b) => (a.ordine ?? 0) - (b.ordine ?? 0))
})

// Le colonne tipo 'azione' sono renderizzate separatamente via slot.
// Tutte le altre vanno nelle Column iterabili.
const colonneStandard = computed(() =>
  colonneRender.value.filter((c) => c.tipo_colonna !== 'azione'),
)
// Renderizza la Column "Azioni" solo se la config la dichiara E il caller
// fornisce lo slot — evita celle vuote silenziose se il consumer dimentica
// di passare il template.
const haAzioni = computed(
  () =>
    colonneRender.value.some((c) => c.tipo_colonna === 'azione') &&
    !!slots.actions,
)

// Colonna di SELEZIONE (checkbox custom, pattern useSelezioneToggle): chrome
// della lista come l'expander, NON una colonna di catalogo — non si ritira,
// non si esporta, non si personalizza. Renderizzata solo se il caller passa lo
// slot `#selection` (header nel gemello `#selection-header`). Estratta il
// 2026-08-03 alla 2ª occorrenza (regola del 2, ok Tid): righe approvabili di
// CommessaGestioneDrawer + emissione mirata dei gruppi fatturabili — PrimeVue 4
// non ha piu' il predicato per-riga, quindi la checkbox e' custom per forza
// (vedi useSelezioneToggle) e la Column deve viverla il BB.
const haSelezione = computed(() => !!slots.selection)

// Dettaglio inline del caller (slot `row-expansion`): master-detail dentro la
// riga, es. le versioni sotto ogni listino. Convive con le colonne ritirate —
// una riga aperta mostra prima quelle, poi il dettaglio.
const haRowExpansion = computed(() => !!slots['row-expansion'])

// Ritiro dinamico colonne (prop `responsive`). Il composable osserva la
// larghezza reale del contenitore (root della lista) e ritira le colonne a
// priorita' piu' bassa quando la somma delle larghezze supera lo spazio.
const containerRef = ref(null)

// Espansione: una sola per DataTable, condivisa fra le due cose che la usano —
// le colonne ritirate dal packing e il dettaglio inline del caller. Lo stato e'
// interno finche' il caller non passa `v-model:expanded-rows`; da quel momento
// e' suo, e qui si legge e si riemette soltanto.
const _expandedRowsInterno = ref({})
const expansionPilotata = computed(() => props.expandedRows !== null)
const expandedRows = computed({
  get: () => (expansionPilotata.value ? props.expandedRows : _expandedRowsInterno.value),
  set: (v) => {
    if (expansionPilotata.value) emit('update:expandedRows', v)
    else _expandedRowsInterno.value = v
  },
})

// ⛔ IL GUARD DELLA MODALITA' NON PAGINATA — l'unico difetto MUTO che
//    `paginata: false` introduce, e il motivo per cui `total` resta obbligatorio.
//
// Con `lazy` acceso PrimeVue rende esattamente le righe che gli dai e usa
// `totalRecords` per il paginator. SPENTO, tratta `rows` come il dataset
// COMPLETO: se il caller continua a mandare una pagina (`limit=25`), la tabella
// mostra 25 righe, niente paginator, **nessun errore** — e l'operatore non ha
// modo di sapere che ce n'erano 500. Non fallisce niente: la lista e' solo
// incompleta, e sembra intera.
//
// ⭐ Il confronto costa zero perche' il dato c'e' gia': `total` e' una prop e
//    l'endpoint lo restituisce comunque. «Non paginata» diventa un CONTRATTO
//    verificabile — `rows.length === total` — invece di un'assunzione.
//
// ⚠️ E vale soprattutto per DOMANI: una lista piccola oggi che cresce a 400
//    righe fra un anno e' il caso in cui questo si rompe, ed e' l'unico in cui
//    nessuno starebbe guardando (`feedback_concentrico_no_yagni`).
//
// ⚠️ `loading` esclude il transitorio: durante una fetch le due grandezze
//    possono essere legittimamente disallineate.
// ⚠️ Lista vuota con `total` a 0 non e' una pretesa: e' il caso «nessun dato».
const troncamentoSospetto = computed(() => {
  if (props.paginata) return false
  if (props.loading || configLoading.value) return false
  if (props.rows.length === 0 && props.total === 0) return false
  return props.rows.length !== props.total
})

// Fail-visible ha due destinatari: l'operatore vede il Message al posto della
// tabella, lo sviluppatore trova il perche' in console. Senza la seconda meta'
// il messaggio a video non dice quale lista ne' quali numeri.
watch(troncamentoSospetto, (sospetto) => {
  if (!sospetto) return
  console.error(
    `[ListaConfigurabile] "${props.codice}" e' montata con paginata=false ma `
    + `le righe ricevute (${props.rows.length}) non sono tutte quelle `
    + `dichiarate da total (${props.total}). La lista mostrerebbe un `
    + 'sottoinsieme facendolo passare per l\'insieme: tabella non renderizzata. '
    + 'O il caller smette di paginare la fetch, o la lista torna paginata=true.',
  )
}, { immediate: true })

// Scopo: azzera l'espansione solo quando e' la lista a possederla. Con
// `v-model` il proprietario e' il caller: sovrascriverlo qui gli cancellerebbe
// sotto i piedi le righe appena aperte.
function resetExpansionSePropria() {
  if (!expansionPilotata.value) _expandedRowsInterno.value = {}
}

const {
  visibleColumns: _responsiveVisible,
  hiddenColumns: _responsiveHidden,
  actionsCompact: _responsiveActionsCompact,
} = useResponsiveColumns(containerRef, colonneStandard, {
  hasActions: haAzioni,
  actionsInlineWidth: computed(() => larghezzaAzioniInline(props.azioniInline)),
  hasSelection: haSelezione,
  hasRowExpansion: haRowExpansion,
})

// Larghezza resa di una colonna dati = quella che il packing ha contato
// (catalogo, o lo stesso fallback). Va come `width` E come `--col-w`, il
// tetto che main.css applica al contenuto di celle e intestazioni delle liste
// responsive: senza il tetto il browser rende `max-content` e la larghezza di
// catalogo e' solo un minimo — il conto del packing non vale piu'.
function stileColonna(col) {
  const w = col.larghezza && col.larghezza > 0 ? col.larghezza : DEFAULT_COL_WIDTH
  return `width: ${w}px; --col-w: ${w}px;`
}

// `title` della cella: il testo intero quando l'ellissi lo tronca. Solo per le
// celle di testo (formatter di default); Tag, chip e slot del caller non hanno
// un testo da ripetere.
function titoloCella(col, data) {
  return testoCella(col, data, slots[`cell-${col.codice}`])
}

// Le azioni di riga si comprimono a kebab quando lo spazio si stringe (prima
// leva di recupero, prima di ritirare colonne dati). Passato allo slot
// `actions` come scope `compact` cosi' il caller lo gira a RowActionsMenu.
const actionsCompact = computed(() =>
  props.responsive ? _responsiveActionsCompact.value : false,
)

// Colonne renderizzate come Column dati: tutte (responsive off) o solo le
// visibili dopo il packing.
const colonneVisibili = computed(() =>
  props.responsive ? _responsiveVisible.value : colonneStandard.value,
)
// Colonne ritirate nell'expansion row (solo in modalita' responsive).
const colonneRitirate = computed(() =>
  props.responsive ? _responsiveHidden.value : [],
)

// Niente piu' colonne ritirate (es. sidebar richiusa) -> azzera lo stato
// expansion, altrimenti riallargando le righe gia' aperte riapparirebbero
// espanse (stato fantasma).
watch(
  () => colonneRitirate.value.length,
  (n) => {
    // Con un dettaglio inline del caller l'espansione serve comunque, anche a
    // zero colonne ritirate: qui non c'e' nessuno stato fantasma da pulire.
    if (n === 0 && !haRowExpansion.value) resetExpansionSePropria()
  },
)

// «Espandi tutte» / «Comprimi tutte» — l'azione standard di testata che
// `useListaAzioni` monta accanto a Personalizza/Esporta (2026-09-18, ok Tid).
// Vive QUI, non nel chiamante: passa dal setter di `expandedRows`, quindi
// funziona sia quando l'espansione e' della lista sia quando e' pilotata dal
// caller (listini), che riceve `update:expandedRows` come per un chevron.
// `haEspansione` e' il predicato di VISIBILITA' dell'azione: senza colonne
// ritirate ne' dettaglio inline non c'e' niente da aprire, e un pulsante che
// non fa nulla e' peggio della sua assenza.
const haEspansione = computed(
  () => colonneRitirate.value.length > 0 || haRowExpansion.value,
)
const haRighe = computed(() => props.rows.length > 0)
const tutteEspanse = computed(() => {
  if (!haRighe.value) return false
  const aperte = expandedRows.value || {}
  return props.rows.every((r) => aperte[r[props.dataKey]])
})

function espandiTutte() {
  const map = {}
  for (const r of props.rows) map[r[props.dataKey]] = true
  expandedRows.value = map
}

function comprimiTutte() {
  expandedRows.value = {}
}

// Pagina dimensione effettiva. ⭐ CASCATA, e l'ordine e' il punto:
//   1. quello che il CALLER dichiara (`paginatorOptions.rows`) — e' lo stato con
//      cui ha appena fatto la fetch, quindi e' l'unica verita';
//   2. la config BE (preferenza/preset) — vale finche' il caller non ne ha uno;
//   3. la misura di pagina del catalogo (`misuraDefault(USO_MISURA.PAGINA)`).
//
// ⛔ FINO AL 2026-08-28 IL CALLER NON ERA NELLA CASCATA, e la paginazione
//    SALTAVA. `pageSize` era una computed sulla SOLA config, quindi la scelta
//    «righe per pagina» dell'operatore non arrivava mai qui: lui sceglieva 10, il
//    caller rifaceva la fetch con 10, e al render successivo il paginator tornava
//    a disegnarsi con i 25 del catalogo. Da li' in poi i due numeri
//    litigavano — PrimeVue calcolava l'offset del «vai a pagina 2» con 25 e il
//    caller lo interpretava con 10: si passava da pagina 1 a pagina 3.
//    ⚠️ Trovato in collaudo. Prima si era corretto solo il valore INIZIALE
//    (allineamento su `@config-loaded`): non bastava, perche' il difetto non e'
//    nel valore di partenza — e' che la scelta dell'operatore non era MAI letta.
// ⚠️ `pagina_dimensione: null` e' «come lo standard» (voce del drawer, finche'
//    il salvataggio non rilegge la config — o se fallisce): vale lo standard
//    della config, non il default di catalogo.
const pageSize = computed(
  () => props.paginatorOptions?.rows
    ?? config.value?.pagina_dimensione
    ?? config.value?.pagina_dimensione_standard
    ?? misuraDefault(USO_MISURA.PAGINA),
)
// Offset 0-based del paginator, con la stessa cascata e per la stessa ragione:
// se il caller dichiara `first`, quello E' la posizione — ricalcolarla qui da
// `page x pageSize` significa farlo con un moltiplicatore che potrebbe non
// essere il suo.
// ⚠️ Resta a 0 finche' la config non e' caricata E il caller non ha detto
//    niente: e' la difesa originale contro il salto del primo render, e vale
//    ancora per le liste che non passano `first`.
const firstOffset = computed(() => {
  const dalCaller = props.paginatorOptions?.first
  if (dalCaller != null) return dalCaller
  return config.value ? (props.page - 1) * pageSize.value : 0
})

// Eventi DataTable -> il caller decide come gestire (server-side fetch).
// Azzeriamo lo stato expansion su cambio pagina/sort: le chiavi dataKey della
// pagina precedente non hanno senso sulla nuova.
// ⛔ Con `paginata: false` NON si emette. Spento `lazy`, PrimeVue ordina in
//    locale E continua a emettere `@sort`: un caller che aveva agganciato
//    `onSort -> refetch` farebbe entrambe le cose — riordina due volte, e su
//    collation diverse le due passate possono non concordare. Nulla fallisce,
//    ed e' esattamente la classe di difetto che questa modalita' non deve
//    portarsi dietro. Qui non c'e' niente da rifetchare: l'evento non parte.
// ⛔ E l'uscita e' PRIMA di `resetExpansionSePropria()`, non dopo. L'azzeramento
//    dell'espansione ha senso quando la pagina cambia DAVVERO contenuto: le
//    chiavi `dataKey` della pagina precedente non esistono piu'. In modalita'
//    non paginata invece le righe sono le stesse e vengono solo RIORDINATE:
//    l'espansione resta valida (PrimeVue la indicizza per `dataKey`, non per
//    posizione), e azzerarla chiuderebbe sotto gli occhi dell'operatore le
//    righe che aveva aperto per leggere le colonne ritirate.
//    ⚠️ In modalita' non paginata `onPage` non puo' nemmeno scattare — il
//    paginator non esiste — ma la guardia sta su entrambi: una simmetria che
//    non costa niente e non lascia un ramo che dipende da «tanto non capita».
function onPage(event) {
  if (!props.paginata) return
  resetExpansionSePropria()
  emit('page', event)
}

// ⭐ REGOLA DI TID (2026-09-02): «gli ordinamenti per DATA hanno sempre default
//    DESC». Una data si legge dalla piu' recente — cliccare «Data» e ricevere il
//    2019 in cima e' il contrario di cio' che si e' chiesto, e su una lista di
//    presidio e' anche il caso meno utile.
// ⚠️ QUALI SIANO LE COLONNE DATA NON SI DECIDE QUI: lo dice il catalogo
//    (`ui.lista_colonna.tipo_dato`), che e' gia' la sede di quel fatto. Un
//    elenco di nomi scritto nel frontend sarebbe una seconda verita' che
//    diverge alla prima colonna aggiunta a catalogo.
const TIPI_DATO_CRONOLOGICI = new Set(['date', 'datetime'])

// I `campo_sorgente` — cioe' i valori che PrimeVue manda in `sortField` — delle
// colonne cronologiche di QUESTA lista.
const campiCronologici = computed(() => new Set(
  colonneRender.value
    .filter((c) => TIPI_DATO_CRONOLOGICI.has(c.tipo_dato))
    .map((c) => c.campo_sorgente),
))

// ⛔ MEMORIA DEL CAMPO SU CUI SI STA CICLANDO, e non e' un dettaglio: senza,
//    il giro DESC qui sotto rende una colonna data NON PIU' ORDINABILE IN
//    CRESCENTE. Il motivo e' `removable-sort`: PrimeVue alterna
//    asc -> desc -> NIENTE, e nello stato «niente» il `sortField` applicato
//    torna `null`. Il click successivo sulla STESSA colonna sembra allora un
//    primo click — campo diverso da `null` — e viene girato di nuovo a DESC.
//    ⇒ il ciclo si chiude su desc -> niente -> desc, e l'ASC non si raggiunge
//    piu'. 🔴 Difetto reale, trovato da Tid in collaudo sulla lista DDT il
//    2026-09-02.
// ⚠️ La memoria sopravvive allo stato «niente» apposta: e' l'unica cosa che
//    distingue «sto ancora ciclando su Data» da «sono passato a un'altra
//    colonna», e lo stato intermedio cancella l'informazione da `props`.
const ultimoCampoOrdinato = ref(null)

// Scopo: il verso del PRIMO click su un'intestazione data.
// ⛔ SOLO IL PRIMO: girare anche i click successivi renderebbe la colonna non
//    invertibile. Con la memoria il ciclo e' desc -> niente -> asc -> desc,
//    cioe' lo stesso ciclo di prima letto dall'altro capo.
// ⚠️ Non tocca le liste non paginate: la' l'ordine lo calcola PrimeVue in
//    locale e questo evento non parte nemmeno (vedi la guardia sotto).
function versoIniziale(event) {
  const campoPrecedente = props.sortField ?? ultimoCampoOrdinato.value
  const nuovaColonna = event?.sortField && event.sortField !== campoPrecedente
  if (
    event?.sortOrder === 1
    && nuovaColonna
    && campiCronologici.value.has(event.sortField)
  ) {
    return { ...event, sortOrder: -1 }
  }
  return event
}

function onSort(event) {
  if (!props.paginata) return
  resetExpansionSePropria()
  const risolto = versoIniziale(event)
  // ⚠️ La memoria si aggiorna DOPO la decisione, e tiene il valore vecchio
  //    quando l'evento non porta un campo (stato «niente»): e' esattamente il
  //    caso per cui esiste.
  ultimoCampoOrdinato.value =
    event?.sortField ?? props.sortField ?? ultimoCampoOrdinato.value
  emit('sort', risolto)
}

// ⭐ LA RIGA APERTA IN UN DRAWER (2026-10-04, Tid): aprendo un drawer da una
//    riga, la lista sotto il velo deve dire QUALE riga e' aperta. Lo sa da
//    sola, senza che le pagine lo dichiarino: al click si ricorda la chiave
//    e quanti drawer erano aperti (la pila di `useDrawerInCima`); la riga
//    resta attiva finche' ce n'e' di piu' — il drawer nato da quel click, o
//    un suo figlio — e si spegne quando quel drawer si chiude.
// ⚠️ Un click che NON apre un drawer (form inline sotto la lista) si
//    dimentica subito: altrimenti il primo drawer aperto dopo, da un «Nuovo»
//    o da F6, evidenzierebbe una riga che non c'entra.
// ⚠️ Il drawer deve aprirsi nello stesso giro del click (`editRow` lo fa): uno
//    che si apre dopo un'attesa non viene riconosciuto e la riga non si
//    evidenzia. In quel caso il caller passa `riga-attiva`.
const rigaCliccata = ref(null)
const livelloAlClic = ref(0)
const rigaApertaDalClic = computed(() =>
  rigaCliccata.value != null && drawerAperti() > livelloAlClic.value ? rigaCliccata.value : null,
)
watch(
  () => drawerAperti(),
  (n) => { if (n <= livelloAlClic.value) rigaCliccata.value = null },
)
async function ricordaRigaCliccata(chiave) {
  rigaCliccata.value = chiave
  livelloAlClic.value = drawerAperti()
  await nextTick()
  if (drawerAperti() <= livelloAlClic.value && rigaCliccata.value === chiave) {
    rigaCliccata.value = null
  }
}

// La riga evidenziata: quella dichiarata dal caller, o quella aperta dal click.
const rigaEvidenziata = computed(() => props.rigaAttiva ?? rigaApertaDalClic.value)

// Scopo: le classi della riga: quella attiva (form o drawer aperti su di
//        lei), e le righe che il click non apre. Le regole di stile stanno in
//        main.css (§ «Riga attiva e righe non cliccabili»).
function classeRiga(data) {
  const classi = []
  if (rigaEvidenziata.value != null && data?.[props.dataKey] === rigaEvidenziata.value) {
    classi.push('app-riga-attiva')
  }
  if (!props.righeCliccabili) classi.push('app-riga-non-cliccabile')
  return classi
}

function onRowClick(event) {
  // Il click sul toggler dell'expander NON deve propagarsi come row-click
  // (altrimenti il chevron aprirebbe ANCHE il drawer del caller).
  const target = event?.originalEvent?.target
  if (
    target?.closest?.(
      '[data-pc-section="rowtogglebutton"], .p-datatable-row-toggle-button, .p-row-toggler',
    )
  ) {
    return
  }
  // Prima dell'emit: il caller apre il drawer DENTRO l'emit, e la pila va
  // letta com'era prima.
  if (props.righeCliccabili) ricordaRigaCliccata(event.data?.[props.dataKey] ?? null)
  emit('row-click', event.data)
}

// Toolbar: apri modale personalizzazione (carica catalogo lazy).
async function openModal() {
  await ensureCatalogo()
  modalVisible.value = true
}

// DEF-2: CTA "Vedi novita'" del banner preset aggiornato → apre la
// modale di personalizzazione. Niente reset del flag qui: il riallineo
// avviene naturalmente al successivo save (lo snapshot si aggiorna a
// `preset.contenuto_aggiornato_il` corrente in `ListaPreferenzaService.upsert`:
// la data del CONTENUTO del preset, non l'audit `data_update`).
async function onSeePresetUpdate() {
  await openModal()
}

// DEF-2: CTA "Ignora" del banner preset aggiornato → POST tombstone +
// reload config (composable). Toast/error handling via useApiHandler.
async function onIgnorePresetUpdate() {
  await ignorePresetUpdate()
}

// Modale -> apply: aggiorna config locale e salva sul server.
async function onApply(payload) {
  applyChange((c) => {
    if (payload.colonne) c.colonne = payload.colonne
    // `null` = «come lo standard»: `save()` toglie la chiave dalla preferenza
    // (BB `preferenzaPerChiave`), e la lista riprende la misura dal reload.
    if ('pagina_dimensione' in payload) c.pagina_dimensione = payload.pagina_dimensione
  })
  modalVisible.value = false
  if ((await save()) !== null) emettiConfigRiletta()
}

async function onReset() {
  modalVisible.value = false
  if ((await reset()) !== null) emettiConfigRiletta()
}

// Scopo: dopo salvataggio e ripristino la config e' riletta dal composable:
//        lo si dice al caller come al primo caricamento. Senza, la misura di
//        pagina scelta nel drawer non arrivava alla lista (il caller la legge
//        da `config-loaded`, BB `allineaMisuraConfig`).
function emettiConfigRiletta() {
  if (config.value) emit('config-loaded', config.value)
}

// Merge default-pattern + override caller. removable-sort/striped/scrollable
// restano fissati in template (non parametrizzabili: regole del pattern lista,
// frontend-standards.md §"Pattern lista").
// ⛔ `paginator: false` in coda al merge, e la posizione e' il punto: vince
//    sui default E sull'override del caller. Una lista non paginata che
//    disegnasse il paginator direbbe «1/1» su un dataset troncato — cioe'
//    la stessa bugia che il guard sopra esiste per impedire.
const effectivePaginatorOptions = computed(() => ({
  ..._DEFAULT_PAGINATOR_OPTIONS,
  ...props.paginatorOptions,
  ...(props.paginata ? {} : { paginator: false }),
}))

// API esposta al caller. `openModal` permette di trasformare il bottone
// "Personalizza colonne" in un'azione utility del PageActionsBar
// esterno (kebab-compact su touch). `dirty` / `colonneNuove` /
// `presetAggiornato` / `config` per eventuali Tag / Badge che il caller
// mostra nella sua toolbar.
defineExpose({
  config,
  dirty,
  colonneNuove,
  presetAggiornato,
  save,
  reset,
  applyChange,
  openModal,
  ignorePresetUpdate,
  // Espansione righe, per l'azione standard «Espandi tutte» di useListaAzioni.
  haEspansione,
  haRighe,
  tutteEspanse,
  espandiTutte,
  comprimiTutte,
})
</script>

<template>
  <div ref="containerRef" class="lista-configurabile">
    <!-- Niente toolbar interna: il caller compone la sua usando
         PageActionsBar standard e integra il bottone "Personalizza" via
         action utility che chiama il metodo `openModal()` esposto da
         questo componente (defineExpose). Tag stato (`dirty`/`config`)
         e badge colonne nuove (`colonneNuove`) sono anch'essi esposti e
         renderizzabili nel suffix della PageActionsBar del caller — su
         touch finiscono nel kebab insieme alle altre azioni. -->

    <!-- DEF-2: banner "preset aggiornato". Visibile solo quando il BE
         segnala che l'admin ha modificato il preset di base dopo lo
         snapshot della preferenza utente (e l'utente non ha ancora
         dismissato). PrimeVue Message severity=info non chiudibile: la
         dismissione esplicita avviene via CTA "Ignora" (tombstone). -->
    <Message
      v-if="presetAggiornato"
      severity="info"
      :closable="false"
      class="lista-preset-aggiornato"
    >
      <div class="lista-preset-aggiornato__row">
        <span class="lista-preset-aggiornato__msg">
          {{ t('lista_config.preset_aggiornato_messaggio') }}
        </span>
        <div class="lista-preset-aggiornato__actions">
          <Button
            severity="info"
            size="small"
            :label="t('lista_config.preset_aggiornato_vedi_novita')"
            :icon="MANAGE_ICONS.NOVITA"
            :disabled="configLoading"
            @click="onSeePresetUpdate"
          />
          <Button
            severity="secondary"
            text
            size="small"
            :label="t('lista_config.preset_aggiornato_ignora')"
            :disabled="configLoading"
            @click="onIgnorePresetUpdate"
          />
        </div>
      </div>
    </Message>

    <!-- Cancello di perimetro emittente (P-2b): la lista non sa dire da quale
         emittente arriva ogni riga, e chi la sta aprendo ne ha piu' di uno
         davanti. Si prende il posto della tabella: mostrarla comunque, con un
         avviso sopra, non toglierebbe l'ambiguita' — le righe resterebbero
         indistinguibili una dall'altra (P-2c: su una lista l'etichetta non
         basta, serve la colonna o il blocco).
         ⚠️ Non e' un errore di permesso e non va vestito da errore: il diritto
         c'e', manca una scelta che l'utente fa in due secondi dalla combo in
         alto. Severity `warn`, non `error`. -->
    <div v-if="perimetroBloccato" class="lista-perimetro-gate">
      <Message severity="warn" :closable="false">
        <div class="lista-perimetro-gate__titolo">
          {{ t('common.perimetro_emittente.titolo') }}
        </div>
        <div class="lista-perimetro-gate__testo">
          {{ t('common.perimetro_emittente.descrizione') }}
        </div>
      </Message>
    </div>

    <!-- ⛔ Troncamento silenzioso (`paginata: false` + righe che non sono
         tutte): si prende il posto della tabella, come il cancello di
         perimetro. Mostrarla con un avviso sopra sarebbe peggio del difetto —
         l'operatore leggerebbe comunque righe presentate come l'insieme
         completo, che e' esattamente la cosa da impedire.
         ⚠️ severity `error` e non `warn`: qui non manca una scelta
         dell'utente, c'e' un contratto rotto fra caller e building block, e
         non e' l'operatore a poterlo sanare. Il dettaglio (quale lista, quali
         numeri) e' in console per chi sviluppa. -->
    <div v-else-if="troncamentoSospetto" class="lista-troncamento-gate">
      <Message severity="error" :closable="false">
        <div class="lista-troncamento-gate__titolo">
          {{ t('lista_config.troncamento_titolo') }}
        </div>
        <div class="lista-troncamento-gate__testo">
          {{ t('lista_config.troncamento_testo', { righe: rows.length, total }) }}
        </div>
      </Message>
    </div>

    <DataTable
      v-else
      v-bind="effectivePaginatorOptions"
      :value="rows"
      :loading="loading || configLoading"
      :total-records="total"
      :rows="pageSize"
      :first="firstOffset"
      :lazy="paginata"
      :null-sort-order="NULL_IN_FONDO"
      removable-sort
      striped-rows
      scrollable
      scroll-height="flex"
      :class="['app-datatable', { 'app-datatable--responsive': responsive }]"
      :sort-field="sortField"
      :sort-order="sortOrder"
      :selection-mode="selectionMode"
      :data-key="dataKey"
      :row-class="classeRiga"
      v-model:expandedRows="expandedRows"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
    >
      <!-- Colonna selezione (chrome, slot-driven): prima di tutto come nei
           pattern useSelezioneToggle. Header = seleziona-tutto del caller. -->
      <Column
        v-if="haSelezione"
        :exportable="false"
        style="width: 3rem; max-width: 3rem;"
      >
        <template #header>
          <slot name="selection-header" />
        </template>
        <template #body="{ data }">
          <slot name="selection" :data="data" />
        </template>
      </Column>

      <!-- Expander: solo quando il ritiro dinamico ha nascosto colonne.
           Apre la riga di espansione che mostra le colonne ritirate (zero
           dati persi). -->
      <Column
        v-if="colonneRitirate.length > 0 || haRowExpansion"
        expander
        :header="''"
        style="width: 3rem; max-width: 3rem;"
      />

      <Column
        v-for="col in colonneVisibili"
        :key="col.codice"
        :field="col.campo_sorgente"
        :header="col.etichetta"
        :sortable="col.ordinabile"
        :frozen="col.fissata"
        :align-frozen="col.fissata ? 'left' : undefined"
        :exportable="col.esportabile"
        :style="stileColonna(col)"
        :body-style="col.allineamento !== 'left' ? `text-align: ${col.allineamento};` : null"
      >
        <!-- L'involucro `app-lista-cella` e' il tetto della cella (main.css §liste
             responsive): il contenuto non puo' allargare la colonna oltre la
             larghezza di catalogo. Il `title` porta il testo intero quando
             l'ellissi lo tronca. -->
        <template #body="{ data }">
          <div class="app-lista-cella" :title="titoloCella(col, data)">
            <CellaConfigurabile
              :col="col"
              :data="data"
              :cell-slot="$slots[`cell-${col.codice}`]"
            />
          </div>
        </template>
      </Column>

      <Column
        v-if="haAzioni"
        :header="t('common.col_azioni')"
        :exportable="false"
        class="app-col-actions"
      >
        <!-- ⭐ `CellaAzioniRiga` consegna `actionsCompact` a `RowActionsMenu`
             da se' (`useAzioniRigaCompatte`): il caller non deve piu' girare
             lo scope `compact`, e dimenticarlo non da' piu' la scrollbar.
             Lo scope resta, per i caller che rendono altro. -->
        <template #body="{ data }">
          <CellaAzioniRiga :compact="actionsCompact">
            <slot name="actions" :data="data" :compact="actionsCompact" />
          </CellaAzioniRiga>
        </template>
      </Column>

      <!-- Empty-state opzionale del caller: passthrough dello slot `#empty` di
           PrimeVue. Registrato SOLO quando il caller lo fornisce, cosi' le
           liste che non lo passano mantengono il default PrimeVue invariato. -->
      <template v-if="$slots.empty" #empty>
        <slot name="empty" />
      </template>

      <!-- Riga di espansione: le colonne ritirate dinamicamente (che riusano
           gli slot `cell-{codice}` del caller, cosi' la resa e' identica a
           quella a video) e SOTTO il dettaglio inline del caller. Le due cose
           condividono l'unica espansione che DataTable mette a disposizione,
           quindi coesistono qui invece di escludersi. -->
      <template
        v-if="colonneRitirate.length > 0 || haRowExpansion"
        #expansion="{ data }"
      >
        <div v-if="colonneRitirate.length > 0" class="lista-config-expansion">
          <div
            v-for="col in colonneRitirate"
            :key="col.codice"
            class="lista-config-expansion__item"
          >
            <span class="lista-config-expansion__label">{{ col.etichetta }}</span>
            <span class="lista-config-expansion__value">
              <CellaConfigurabile
                :col="col"
                :data="data"
                :cell-slot="$slots[`cell-${col.codice}`]"
              />
            </span>
          </div>
        </div>
        <div v-if="haRowExpansion" class="lista-config-dettaglio">
          <slot name="row-expansion" :data="data" />
        </div>
      </template>
    </DataTable>

    <ListaColonneModal
      v-model:visible="modalVisible"
      :codice="codice"
      :config="config"
      :catalogo="catalogo"
      :colonne-nuove="colonneNuove"
      :loading="configLoading"
      @apply="onApply"
      @reset="onReset"
    />
  </div>
</template>

<style scoped>
/* Gate di perimetro emittente: due righe di testo dentro il Message. */
.lista-perimetro-gate {
  padding: var(--app-space-sm) 0;
}

.lista-perimetro-gate__titolo {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.lista-perimetro-gate__testo {
  font-size: 0.9rem;
}

/* Gate di troncamento (`paginata: false` con righe incomplete): stessa forma
   del gate di perimetro — si prende il posto della tabella. */
.lista-troncamento-gate {
  padding: var(--app-space-sm) 0;
}

.lista-troncamento-gate__titolo {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.lista-troncamento-gate__testo {
  font-size: 0.9rem;
}

.lista-configurabile {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.lista-preset-aggiornato {
  margin-bottom: 0.5rem;
}

.lista-preset-aggiornato__row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.lista-preset-aggiornato__msg {
  flex: 1 1 auto;
  min-width: 12rem;
}

.lista-preset-aggiornato__actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* Dettaglio inline del caller: NON entra nella larghezza della tabella madre.
   La madre e' `width: max-content`, e la cella d'espansione vi contribuirebbe
   col max-content del dettaglio (una descrizione lunga, su una riga sola),
   allargando la lista oltre il contenitore: la scrollbar orizzontale
   all'apertura del kit. `width: 0` azzera il contributo, `min-width: 100%`
   gli ridà tutta la cella; se il dettaglio non ci sta, scorre la SUA tabella. */
.lista-config-dettaglio {
  width: 0;
  min-width: 100%;
}

/* Riga di espansione con le colonne ritirate dal packing responsive.
   Griglia label/valore compatta, riusa i colori app. */
.lista-config-expansion {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: 0.35rem 1.25rem;
  padding: 0.5rem 0.75rem 0.75rem;
}

.lista-config-expansion__item {
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
  min-width: 0;
}

.lista-config-expansion__label {
  flex: 0 0 auto;
  font-size: 0.78rem;
  color: var(--app-text-muted);
}

.lista-config-expansion__value {
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--app-table-font-size);
  overflow-wrap: anywhere;
}
</style>
