<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Il drawer OPERATIVO della distinta contabile — il foglio del denaro
//        raccolto in una giornata da un canale: testata, quadratura, righe, e i
//        verbi che le fanno avanzare fino alla registrazione.
//
// ⭐ I DUE CATALOGHI DI STATO arrivano dentro il dettaglio, in un round-trip
//    (`stati_distinta`, `stati_riga`), insieme alle TRANSIZIONI che una PERSONA
//    puo' chiedere DA OGNI STATO (`transizioni.{distinta,riga}`, lette dalle
//    matrici del database — BE-5, dal 14/09). ⛔ Non si riscrivono qui: il
//    giorno che nasce uno stato nuovo, una copia nel frontend lo nasconderebbe
//    senza dirlo — e `POSTATA` non e' fra le uscite proprio perche' la scrive
//    il posting, non un operatore. ⚠️ Fino al 14/09 viaggiava il solo
//    VOCABOLARIO e il drawer toglieva lo stato corrente: su una riga ABBINATA
//    proponeva SCARTATA, che il database rifiuta — il difetto del collaudo.
//
// ⚠️ Il CONTENUTO delle righe (nuove, fatti, eliminazioni) si lavora solo su
//    una MANUALE in BOZZA (`contenuto_modificabile`, D17/D18 — dal dettaglio,
//    non dedotto dallo stato): sotto VALIDATA il foglio e' «finito» e resta
//    aperto alle sole DECISIONI (abbina, sospendi, porta a). Su una distinta
//    FINALE (`stato_is_final`) non si fa piu' niente.
//
// ⭐ LE RIGHE SONO UNA LISTA STANDARD (2026-09-18, rilievo in-app di Tid):
//    `<DrawerTabLista codice="pagamenti.distinta_righe">` su
//    `useDrawerTabLista`, con paginazione, ricarica, «Personalizza colonne» ed
//    export CSV/Excel — cioe' «la contabile in un file». Fino a quel giorno
//    erano una `DataTable` grezza su `dettaglio.righe`, dichiarata «righe di
//    un documento»; ma le righe contabili hanno endpoint propri, una macchina
//    a stati propria e una coda propria: sono un'entita' con vita propria,
//    cioe' la PRIMA domanda del criterio in tre domande (piano PrimeVue 5
//    §Gruppo B), come i titoli IVA il 02/09. 🔵 Debito dichiarato che RESTA:
//    la macchina a stati del master-detail (form sotto la lista) e' scritta
//    qui invece di passare da `RigheMasterDetailTable` (28/08).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { statoDistintaSeverity, statoRigaContabileSeverity } from '../../core/utils/severity'
import { cambiaStatoDistinta, exportRigheDistinta, getDistinta } from '../api/pagamenti'
import { formatCurrency } from '../../core/utils/format'
import { MODO_ABBINA, useAzioniRigaContabile } from '../composables/useAzioniRigaContabile'
import { useDistintaRigheStore } from '../stores/distintaRighe'
import { AZIONE_REGISTRA_DISTINTA } from '../vocabolari'
import AbbinaRigaDialog from './AbbinaRigaDialog.vue'
import CorreggiDistintaDialog from './CorreggiDistintaDialog.vue'
import DistintaRigaForm from './DistintaRigaForm.vue'
import QuadraturaDistinta from './QuadraturaDistinta.vue'
import RatePickerDialog from './RatePickerDialog.vue'
import RegistraDistintaDialog from './RegistraDistintaDialog.vue'
import ValidaDistintaDialog from './ValidaDistintaDialog.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  distintaId: { type: [Number, null], default: null },
})
// ⭐ `apri-distinta` e non un secondo drawer annidato: la correzione produce un
//    DOCUMENTO NUOVO, e lo si apre al posto di questo — chi corregge deve
//    lavorare la correzione, non guardarla da dietro il documento sbagliato.
const emit = defineEmits(['update:visible', 'cambiata', 'apri-distinta'])

const { t, te } = useI18n()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const { execute } = useApiHandler()
const { confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()
// ⚠️ Guard anti-race: aprire due distinte in rapida successione farebbe
//    atterrare la risposta piu' lenta DOPO quella piu' recente, e a video
//    resterebbe il documento sbagliato — senza nessun errore.
const { tag, isCurrent, invalidate } = useFetchVersion()

const dettaglio = ref(null)
const loading = ref(false)
// `null` = elenco · `'create'` · `'edit'` (pattern master-detail inline).
const formMode = ref(null)
const rigaInModifica = ref(null)
const abbinaVisible = ref(false)
const rigaDaAbbinare = ref(null)
// Il MODO del dialogo di abbinamento: «abbina» o «abbina e registra» (la
// tardiva, sotto una distinta registrata) — lo decide il composable delle
// azioni di riga dai fatti della testata.
const modoAbbina = ref(MODO_ABBINA.ABBINA)
const registraVisible = ref(false)
// Il dialog di validazione (FE-1): la transizione verso lo stato
// `is_registrabile`, coi numeri davanti e spenta col motivo.
const validaVisible = ref(false)
const statoDiValidazione = ref(null)
const correggiVisible = ref(false)
// Il picker delle rate in modalita' MULTIPLA (D19-d): N rate → N righe.
const righeDaRateVisible = ref(false)

const distinta = computed(() => dettaglio.value?.distinta || null)
const statiDistinta = computed(() => dettaglio.value?.stati_distinta || [])
// ⭐ Il catalogo degli stati di RIGA viaggia nello stesso round-trip, e serve
//    davvero: porta `is_final`, che il singolo record di riga NON espone — la
//    riga porta solo `stato_is_postabile` e `stato_richiede_abbinamento`.
const statiRiga = computed(() => dettaglio.value?.stati_riga || [])
// ⭐ Le uscite ammesse DALLO STATO CORRENTE della testata: la matrice del
//    database ristretta a cio' che una persona puo' chiedere. Uno stato senza
//    uscite ha la lista vuota — e non e' un errore, e' un fatto. (Quelle di
//    RIGA le legge il composable delle azioni di riga, dalla stessa mappa.)
const transizioniDistinta = computed(
  () => dettaglio.value?.transizioni?.distinta?.[distinta.value?.stato_codice] || [],
)

// ⚠️ Il CONTENUTO si lavora solo su una manuale in bozza (D17/D18). Il flag
//    viene dal DETTAGLIO: dedurlo dallo stato («BOZZA» + «MANUALE») sarebbe
//    una seconda copia della regola. ⛔ Fino al 14/09 era `!stato_is_final`:
//    sotto VALIDATA il form si apriva e il database rifiutava.
const modificabile = computed(
  () => !isReadonly.value && distinta.value?.contenuto_modificabile === true,
)

// ── quadratura e correzione ───────────────────────────────────────
// La quadratura a tre esiti e' il BB di dominio `QuadraturaDistinta` (una
// sede col dialog di validazione); qui restano i campi PROPRI del drawer.
// ⭐ Si corregge cio' che e' REGISTRATO, e lo stato si legge dal CATALOGO:
//    `CHIUSA` e' il nome di oggi, `stato_is_postabile`/`is_final` sono i fatti.
//    ⚠️ Qui serve proprio «registrata», che fra gli stati finali e' l'unico —
//    `ANNULLATA` e' finale ma non ha prodotto movimenti, e correggerla non
//    vuol dire niente. Il dato che li distingue e' `data_conferma`: la scrive
//    il posting, quindi c'e' se e solo se dei movimenti sono nati.
// ⚠️ Il readonly NON sta qui: lo toglie `hideWhenReadonly` sulla barra, come
//    per la registrazione. Ripeterlo in due punti significa che il giorno in cui
//    uno dei due cambia l'altro resta indietro — e questo predicato risponde a
//    una domanda sola: «questo documento e' correggibile?».
const correggibile = computed(
  () => distinta.value != null
    && distinta.value.stato_is_final
    && distinta.value.data_conferma != null,
)

// ⭐ «Di cui non nostre» (D20-c): le SCARTATA contano nel totale delle righe —
//    quel denaro e' arrivato — ma non sono nostre, e la quadratura lo dice.
//    I due numeri li deriva il backend dalle righe per stato, con lo stesso
//    codice con cui la lista le nasconde: qui si mostrano. Zero = niente da
//    dire.
const righeScartate = computed(() => Number(distinta.value?.righe_scartate || 0))

// ── il verbo «valida» e il suo motivo (FE-1, D20-a) ──────────────────
// ⭐ «Posso?» lo dice il flag del backend (`can_validare`), la frase la compone
//    il BB dalla terna `validazione_blocco_*` — la STESSA check che il guard
//    chiama per rifiutare. `null` = il verbo non e' fra le uscite dello stato
//    corrente, e non c'e' niente da spegnere.
const validazioneBloccata = computed(() => distinta.value?.can_validare === false)
const motivoValidazione = computed(() => (
  validazioneBloccata.value
    ? motivoBloccoRiga(t, te, distinta.value, 'validazione_blocco')
    : undefined
))

// ── i verbi della testata ─────────────────────────────────────────
// ⭐ Le transizioni vengono dalla MATRICE (le uscite dallo stato corrente) e
//    si INCROCIANO col catalogo, che dice come si chiamano a video. Nessuno
//    dei due si scrive qui. ⚠️ Lo stato corrente non c'e' per costruzione: la
//    matrice ha un CHECK «da ≠ a».
const drawerActions = computed(() => {
  if (!distinta.value) return []
  const azioni = transizioniDistinta.value
    .map((codice) => {
      const stato = statiDistinta.value.find((s) => s.codice_interno === codice)
      // ⭐ LA VALIDAZIONE HA UN DIALOGO SUO (FE-1): la transizione verso lo
      //    stato «pronta da registrare» — quello che il CATALOGO marca
      //    `is_registrabile` (D20-d), non il nome VALIDATA scritto qui — apre
      //    i numeri invece del confirm generico, e si spegne COL MOTIVO del
      //    database quando ogni riga non e' stata guardata (D20-a).
      const validazione = stato?.is_registrabile === true
      return {
        key: `stato-${codice}`,
        kind: 'state',
        label: t('pagamenti.distinte.porta_a', {
          stato: stato?.descrizione || codice,
        }),
        icon: MANAGE_ICONS.CONFIRM,
        // ⭐ Il rosso lo decide il CATALOGO: `is_final` vuol dire «da qui non si
        //    torna», ed e' esattamente cio' che merita un pulsante d'allarme.
        //    ⛔ Prima era `codice === 'ANNULLATA'`: vero oggi per coincidenza,
        //    falso il giorno di un secondo stato terminale richiedibile.
        severity: stato?.is_final ? 'danger' : undefined,
        hideWhenReadonly: true,
        disabled: validazione && validazioneBloccata.value,
        tooltip: validazione ? motivoValidazione.value : undefined,
        command: validazione
          ? () => { statoDiValidazione.value = stato; validaVisible.value = true }
          : () => onCambiaStato(codice, stato?.descrizione || codice, stato?.is_final),
      }
    })

  // ⭐ LA CORREZIONE GUIDATA (Q-7), e vive sull'ALTRA meta' della vita del
  //    documento: si propone solo su una distinta gia' REGISTRATA, dove la
  //    registrazione non ha piu' senso. Le due non compaiono mai insieme.
  // ⛔ Non si chiama «storno»: `STORNATA` e' fuori dal catalogo dal 21/08.
  // ⚠️ Il cancello e' lo stesso della registrazione (`registra_distinta`): un
  //    gesto che rovescia del denaro non puo' avere una porta piu' larga di
  //    quello che lo ha scritto.
  if (correggibile.value) {
    azioni.push({
      key: 'correggi',
      kind: 'secondary',
      label: t('pagamenti.correggi.azione'),
      icon: MANAGE_ICONS.CORREZIONE,
      severity: 'warn',
      hideWhenReadonly: true,
      action: AZIONE_REGISTRA_DISTINTA,
      // ⚠️ Gia' corretta: si DISABILITA col motivo invece di sparire — e il
      //    motivo nomina la correzione che c'e', che e' il documento su cui
      //    andare a lavorare.
      disabled: distinta.value.correzione_id != null,
      tooltip: distinta.value.correzione_id != null
        ? t('pagamenti.correggi.gia_corretta', {
            codice: distinta.value.correzione_codice || '',
          })
        : undefined,
      command: () => { correggiVisible.value = true },
    })
  }

  // ⛔ La registrazione e' l'unico gesto irreversibile: sta in fondo, e non e'
  //    una transizione di stato come le altre — apre l'anteprima.
  // ⚠️ Si propone solo su un foglio non finale: su una distinta gia' chiusa il
  //    pulsante direbbe che c'e' ancora qualcosa da fare.
  // ⭐ E si SPEGNE COL MOTIVO dove lo stato non e' registrabile (FE-2, D20-d):
  //    la bandiera e' del catalogo (`stato_is_registrabile`), e fino al 18/09
  //    «Registra» in bozza era acceso e finiva in 409. Permesso ⇒ nascondi
  //    (`action`), stato ⇒ disabilita col motivo.
  if (!distinta.value.stato_is_final) {
    const registrabile = distinta.value.stato_is_registrabile === true
    azioni.push({
      key: 'registra',
      kind: 'primary',
      label: t('pagamenti.registra.azione'),
      icon: MANAGE_ICONS.REGISTRA,
      severity: 'danger',
      hideWhenReadonly: true,
      // ⚠️ Il cancello vero e' il backend (`post_permission = registra_distinta`);
      //    qui si evita solo di PROPORRE cio' che verrebbe rifiutato.
      action: AZIONE_REGISTRA_DISTINTA,
      disabled: !registrabile,
      tooltip: registrabile ? undefined : t('pagamenti.registra.blocco.stato'),
      command: () => { registraVisible.value = true },
    })
  }
  return azioni
})

// ── la lista delle righe ──────────────────────────────────────────
// ⚠️ `parentId` porta l'id SOLO a drawer aperto, e il `null` non e' un
//    dettaglio: e' quello che dice allo scaffolding di chiamare `store.reset()`
//    alla chiusura. Senza, le righe della distinta precedente resterebbero in
//    memoria e lampeggerebbero sotto la prossima che si apre — righe vere di un
//    documento sbagliato, che e' il difetto che non fallisce (la stessa ragione
//    dell'`invalidate()` sul dettaglio, qui sotto).
// ⛔ La fetch delle righe NON si scrive piu' in `loadDetail`: il watch dello
//    scaffolding e' `immediate` e riscrive padre, offset e ricerca nell'ordine
//    giusto. Un secondo caricamento a mano sarebbe una seconda sede.
const storeRighe = useDistintaRigheStore()

// ⭐ «Nuova riga» e «Righe da rate» entrano nella barra della lista come azioni
//    del caller (`extraActions`), accanto a ricarica / personalizza / esporta:
//    una barra sola, non due. ⚠️ Non passano da `onNew` perche' hanno una
//    CONDIZIONE (`visible`): il contenuto si scrive solo su una manuale in bozza
//    e non mentre il form e' aperto, e l'azione standard «Nuovo» non la sa.
// ⭐ «Righe da rate»: si scelgono le rate dallo scadenzario e ogni rata diventa
//    una riga (D1 reso a video). Stesso cancello di «Nuova riga»: e' un altro
//    modo di scriverne, non un altro permesso. Inline (non nel kebab): e' il
//    gesto principale della distinta manuale, non un'azione rara.
const azioniRighe = computed(() => [
  {
    key: 'righe-da-rate',
    severity: 'primary',
    label: t('pagamenti.rate.righe_da_rate'),
    icon: 'pi pi-list-check',
    hideWhenReadonly: true,
    visible: modificabile.value && formMode.value === null,
    command: () => { righeDaRateVisible.value = true },
  },
  {
    key: 'nuova-riga',
    kind: 'primary',
    label: t('pagamenti.righe.nuova'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    visible: modificabile.value && formMode.value === null,
    command: () => { rigaInModifica.value = null; formMode.value = 'create' },
  },
])

const {
  onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm, reloadAll,
} = useDrawerTabLista(storeRighe, {
  parentId: () => (props.visible ? props.distintaId : null),
  parentField: 'contabileId',
  exportFn: (params) => exportRigheDistinta(props.distintaId, params),
  // L'export segue la lista a video — ordinamento compreso — dalla sede unica
  // dello store (`paramsFiltro`), non da un ripiego ricopiato qui.
  getExportParams: (formato) => ({ formato, ...storeRighe.paramsFiltro() }),
  extraActions: () => azioniRighe.value,
  // ⭐ «Ricarica» della barra ricarica anche la TESTATA: totali e quadratura
  //    dipendono dalle righe, e una barra che riallinea meta' pagina e' peggio
  //    di nessuna — l'operatore crede di aver riallineato tutto.
  fetchExtra: () => loadDetail(),
})

// ⭐ «MOSTRA SCARTATE (N)» (FE-3, D20-c): la scartata — «non e' nostra» —
//    resta nella distinta ma esce dal lavoro, nascosta di default; il numero
//    lo dichiara il backend (`scartateCount`), e il legame con lo store e' il
//    BB `bindToggle` (`true` acceso, `null` spento: il core manda solo i
//    filtri `!= null`). Il cambio ricarica da pagina 1.
const { bindToggle } = useStoreFilterBindings(storeRighe, applyFilters)
const { value: mostraScartate, onChange: onMostraScartateChange } = bindToggle('scartate')
// L'interruttore compare solo quando ha qualcosa da dire: scartate nascoste
// da mostrare, o gia' mostrate da nascondere. Su una distinta senza scartate
// sarebbe un controllo che non fa niente.
const interruttoreScartate = computed(
  () => mostraScartate.value || storeRighe.scartateCount > 0,
)

// ── azioni di riga ────────────────────────────────────────────────
// ⭐ Vengono dal composable di dominio `useAzioniRigaContabile` (una sede per
//    il drawer e per la coda): la matrice dice quali voci, il catalogo come si
//    chiamano, i fatti della testata cambiano il verbo («Abbina e registra»
//    sotto una distinta registrata), il database spegne il cestino col suo
//    motivo. Qui restano solo i fatti che il drawer conosce.
//
const { buildRowActions } = useAzioniRigaContabile({
  statiRiga: () => statiRiga.value,
  transizioniRiga: () => dettaglio.value?.transizioni?.riga || {},
  // I fatti della testata, dal dettaglio: finale (`stato_is_final`) e
  // registrata (`data_conferma`, scritta dal posting). ⚠️ E' la stessa
  // lettura di `correggibile`: registrata = finale con la conferma.
  testataDi: () => ({
    finale: distinta.value?.stato_is_final === true,
    registrata: distinta.value?.data_conferma != null,
  }),
  readonly: () => isReadonly.value,
  onAbbina: (riga, modo) => {
    rigaDaAbbinare.value = riga
    modoAbbina.value = modo
    abbinaVisible.value = true
  },
  ricarica: () => ricarica(),
  // «Elimina» c'e': il drawer e' la superficie dove il contenuto si lavora
  // (e il database lo spegne dove non si puo').
  conElimina: true,
})

// ── caricamento ───────────────────────────────────────────────────
async function loadDetail() {
  if (!props.distintaId) return
  const mio = tag()
  loading.value = true
  try {
    const res = await loadDetailOrClose(() => getDistinta(props.distintaId))
    if (!isCurrent(mio)) return
    dettaglio.value = res?.data?.data || null
  } finally {
    if (isCurrent(mio)) loading.value = false
  }
}

// Scopo: ricarica dopo un gesto — testata E righe — e avvisa la lista delle
//        distinte, che mostra i contatori.
// ⚠️ `reloadAll` e non `loadDetail`: le righe vivono nel loro store, e un gesto
//    su una riga (stato, abbinamento, eliminazione) cambia sia la pagina sia i
//    totali della testata. Ricaricarne una sola lascerebbe l'altra ferma.
function ricarica() {
  formMode.value = null
  rigaInModifica.value = null
  reloadAll()
  emit('cambiata')
}

function onCambiaStato(codice, descrizione, terminale) {
  confirmAction({
    header: t('confirm.cambio_stato_title'),
    message: t('pagamenti.distinte.conferma_stato', { stato: descrizione }),
    // ⭐ Rosso = si va in uno stato TERMINALE, e lo dice il catalogo.
    danger: terminale === true,
    onAccept: async () => {
      const esito = await execute(
        () => cambiaStatoDistinta(props.distintaId, codice),
        { successMessage: t('pagamenti.distinte.stato_cambiato') },
      )
      if (esito !== null) ricarica()
    },
  })
}

// ⚠️ Il click sulla riga apre la MODIFICA solo se il contenuto si lavora: su
//    una distinta validata o chiusa aprirebbe un form che il database rifiuta.
// ⭐ La firma e' quella del BB: arriva la RIGA, non l'evento PrimeVue.
function onRigaClick(riga) {
  if (!modificabile.value) return
  rigaInModifica.value = riga
  formMode.value = 'edit'
}

// ⚠️ Il CARICAMENTO non sta qui: lo fa il watch dello scaffolding della lista
//    (`useDrawerTabLista`, `fetchExtra`), che ricarica testata e righe insieme
//    al cambio di distinta. Qui restano il reset del form all'apertura e la
//    pulizia alla chiusura — due cose che la lista non conosce.
watch(
  () => [props.visible, props.distintaId],
  ([vis]) => {
    if (vis && props.distintaId) {
      formMode.value = null
      rigaInModifica.value = null
    } else if (!vis) {
      // ⚠️ Si azzera alla CHIUSURA: senza, riaprendo su un'altra distinta si
      //    vedrebbe per un istante quella di prima — e su documenti di denaro
      //    un lampo del documento sbagliato non e' un dettaglio estetico.
      dettaglio.value = null
      invalidate()
    }
  },
  { immediate: true },
)
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    @update:visible="(v) => emit('update:visible', v)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :title="t('pagamenti.distinte.titolo_singolare')"
        :icon="NAV_ICONS.DISTINTE"
      />
    </template>

    <div class="app-drawer-content">
      <!-- ⚠️ Il caricamento si DICE. Un drawer che si apre vuoto e resta vuoto
           per mezzo secondo si legge come «questa distinta non ha niente», che
           e' un'affermazione — e per giunta falsa. -->
      <div v-if="loading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="contentReady && distinta">
        <DrawerEntityHeader>
          <!-- ⭐ «DIS-… del 18/09/2026», e basta (decisione di Tid, 2026-09-18).
               Fino a quel giorno fra codice e data stava la ragione sociale
               dell'emittente (FE-2 del brief distinta-numerata-sul-registro:
               «di chi e', a colpo d'occhio»): tolta dalla riga, resta nel
               tooltip del codice — la sigla e' gia' dentro `DIS-<SIGLA>-…`, e
               chi vuole il nome intero lo trova senza che occupi la testata.
               ⚠️ La lista delle distinte non ha una colonna emittente: il
               tooltip e' l'unico posto del drawer in cui il nome si legge. -->
          <Tag
            :value="distinta.codice"
            severity="secondary"
            v-tooltip.bottom="distinta.emittente_ragione_sociale || undefined"
          />
          <span class="app-drawer-header-muted">
            {{ t('pagamenti.distinte.del_data', { data: displayDate(distinta.data_contabile) }) }}
          </span>
          <span v-if="distinta.centro_descrizione">{{ distinta.centro_descrizione }}</span>
          <span v-if="distinta.ente_descrizione" class="app-drawer-header-muted">
            {{ distinta.ente_descrizione }}
          </span>

          <template #status>
            <Tag
              :value="distinta.stato_descrizione || distinta.stato_codice"
              :severity="statoDistintaSeverity(distinta.stato_codice)"
            />
          </template>
        </DrawerEntityHeader>

        <!-- ⭐ La riga «dove sono» (FE-9): «bozza: si digita» · «validata:
             pronta da registrare, il denaro non e' ancora registrato» ·
             «registrata». La CHIAVE arriva dal `meta` dello stato via backend
             (`stato_info_key`), come negli otto drawer di vendite: qui non
             c'e' nessun `v-if` sullo stato — sarebbe la regola scritta due
             volte. Finche' il seed (brief §4 P-8) non e' applicato, e' vuota. -->
        <DrawerActionsBar
          :actions="drawerActions"
          :info-key="distinta?.stato_info_key || ''"
        />

        <!-- ⭐ IL LEGAME DELLA CORREZIONE, nei due versi. Senza, due documenti
             gemelli di segno opposto stanno nell'elenco senza niente che dica
             che uno rovescia l'altro — e chi li trova fra sei mesi non ha modo
             di saperlo. Sono cliccabili perche' il gesto ovvio, letta la riga,
             e' andare a vedere l'altro documento. -->
        <Message
          v-if="distinta.contabile_corretta_id"
          severity="warn"
          :closable="false"
          size="small"
        >
          <Button
            link
            size="small"
            :label="t('pagamenti.correggi.e_la_correzione_di', {
              codice: distinta.contabile_corretta_codice || distinta.contabile_corretta_id,
            })"
            @click="emit('apri-distinta', distinta.contabile_corretta_id)"
          />
        </Message>
        <Message
          v-if="distinta.correzione_id"
          severity="info"
          :closable="false"
          size="small"
        >
          <Button
            link
            size="small"
            :label="t('pagamenti.correggi.e_stata_corretta_da', {
              codice: distinta.correzione_codice || distinta.correzione_id,
            })"
            @click="emit('apri-distinta', distinta.correzione_id)"
          />
        </Message>

        <!-- ══ La quadratura ══ — il BB di dominio (tre esiti), coi campi
             propri del drawer nello slot. -->
        <QuadraturaDistinta :distinta="distinta">
          <div class="form-field">
            <label>{{ t('pagamenti.distinte.col_righe_registrabili') }}</label>
            <span>
              {{ distinta.righe_registrabili ?? 0 }} / {{ distinta.righe_totali ?? 0 }}
            </span>
          </div>
          <!-- ⭐ «Di cui non nostre» (D20-c): le scartate contano nel totale —
               quel denaro e' arrivato — ma non sono nostre. Senza questa riga
               «dichiarato 1000 · righe 1000» con 200 di scartate dentro si
               leggerebbe come «tutto nostro». Compare solo se ce ne sono. -->
          <div v-if="righeScartate > 0" class="form-field">
            <label>{{ t('pagamenti.distinte.di_cui_non_nostre') }}</label>
            <span>
              {{ t('pagamenti.distinte.non_nostre_valore', {
                n: righeScartate,
                importo: formatCurrency(distinta.totale_scartate),
              }) }}
            </span>
          </div>
        </QuadraturaDistinta>

        <!-- ══ Chi e quando ha registrato ══ -->
        <template v-if="distinta.data_conferma">
          <div class="app-drawer-section">
            <h4>{{ t('pagamenti.distinte.sezione_registrazione') }}</h4>
          </div>
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('pagamenti.distinte.col_data_conferma') }}</label>
              <span>{{ displayTimestamp(distinta.data_conferma) }}</span>
            </div>
            <div class="form-field">
              <label>{{ t('pagamenti.distinte.col_user_conferma') }}</label>
              <span>{{ distinta.user_conferma || '—' }}</span>
            </div>
          </div>
        </template>

        <!-- ══ Le righe ══ -->
        <div class="app-drawer-section">
          <h4>{{ t('pagamenti.distinte.sezione_righe') }}</h4>
        </div>

        <!-- ⚠️ Il foglio chiuso lo si DICE: senza, l'assenza dei verbi si legge
             come un'interfaccia rotta invece che come uno stato. E lo stesso
             vale per il foglio VALIDATO (D18): niente righe nuove ne' fatti,
             ma abbinare e sospendere si puo' — e va detto, o il pulsante
             «Nuova riga» che manca sembra un difetto. -->
        <Message
          v-if="distinta.stato_is_final"
          severity="info"
          :closable="false"
          size="small"
        >
          {{ t('pagamenti.distinte.foglio_chiuso') }}
        </Message>
        <Message
          v-else-if="!distinta.contenuto_modificabile && !isReadonly"
          severity="info"
          :closable="false"
          size="small"
        >
          {{ t('pagamenti.distinte.contenuto_fermo') }}
        </Message>

        <!-- ⛔ «Non sono riuscito a leggere le righe» non e' «non ce ne sono»:
             a lista vuota il BB mostrerebbe lo stesso empty-state per entrambi,
             quindi la distinzione vive qui, sopra la lista, e lo stato lo tiene
             lo store (`erroreCaricamento`). Su un foglio di denaro «vuoto» e'
             un'affermazione su cui qualcuno registra. -->
        <Message
          v-if="storeRighe.erroreCaricamento"
          severity="warn"
          :closable="false"
          size="small"
        >
          {{ t('pagamenti.distinte.righe_non_lette') }}
        </Message>

        <!-- ⭐ LISTA STANDARD dal 2026-09-18 (decisione di Tid), col pacchetto
             intero: pagine, ricarica, «Personalizza colonne», export CSV/Excel.
             Le colonne vengono dal catalogo (`ui.lista_colonna`, lista 69):
             qui restano solo gli slot che una cella non sa rendere da sola.
             ⚠️ Niente `#cell-natura`: e' il `formato = natura_doc` del catalogo
             (`CellaConfigurabile` → `NaturaDocTag`), come nelle altre quattro
             liste con la natura. Uno slot qui sarebbe la quinta copia. -->
        <DrawerTabLista
          ref="listaRef"
          codice="pagamenti.distinta_righe"
          :store="storeRighe"
          :rows="storeRighe.items"
          :total="storeRighe.totalRecords"
          :loading="storeRighe.loading"
          :paginator-options="paginatorProps"
          :page="tablePage"
          :sort-field="paginatorProps.sortField"
          :sort-order="paginatorProps.sortOrder"
          :page-actions="pageActions"
          :dirty="dirty"
          :perimetro-bloccato="perimetroBloccato"
          @page="onPage"
          @sort="onSort"
          @row-click="onRigaClick"
          @config-loaded="onConfigLoaded"
        >
          <!-- ⭐ «Mostra scartate (N)» (FE-3): il BB `FiltroToggle` col conteggio
               del backend, come «Mostra annullati» sui lotti. Solo quando ha
               qualcosa da dire — e il `v-if` sta sul `<template>`, non sul
               widget: condizionato dentro, lo slot esisterebbe comunque e in
               modalita' compatta comparirebbe l'imbuto su un drawer vuoto.
               ⭐ Dal 2026-09-23 sta nei FILTRI della lista, non in una barra
               sua sopra di essa: e' un filtro di quelle righe, quindi sotto i
               1024px scende nel drawer dal basso e conta nel segno. -->
          <template v-if="interruttoreScartate" #filtri>
            <FiltroToggle
              v-model="mostraScartate"
              :label="t('pagamenti.distinte.mostra_scartate')"
              :hint="t('pagamenti.distinte.mostra_scartate_hint')"
              :count="storeRighe.scartateCount"
              @change="onMostraScartateChange"
            />
          </template>

          <!-- La frase del dominio al posto dell'empty-state generico.
               ⛔ MA SOLO SE LA LETTURA E' RIUSCITA: con `erroreCaricamento` la
               tabella e' vuota per un'altra ragione, e «non ha ancora righe»
               sotto un avviso che dice «non sono riuscito a leggerle» sarebbe
               una contraddizione. -->
          <template #empty>
            <div v-if="!storeRighe.erroreCaricamento" class="app-empty-state">
              <i class="pi pi-list" />
              <p>{{ t('pagamenti.distinte.nessuna_riga') }}</p>
            </div>
          </template>

          <!-- ⚠️ I nomi degli slot sono i `codice` delle colonne A CATALOGO, non
               i `campo_sorgente`: la colonna si chiama `stato` e il campo che
               legge e' `stato_descrizione`. Uno slot col nome sbagliato non da'
               nessun errore — la cella ripiega sul testo e il Tag sparisce. -->
          <template #cell-stato="{ data }">
            <Tag
              :value="data.stato_descrizione || data.stato_codice"
              :severity="statoRigaContabileSeverity(data.stato_codice)"
            />
            <!-- ⭐ La forzatura resta SCRITTA sulla riga ed e' cio' che
                 l'elenco delle rate fuori capienza legge: qui si vede, o la
                 riga racconta meno di quello che e' successo. (La colonna
                 `forzata` a catalogo, spenta di default, la porta anche nel
                 file.) -->
            <Tag
              v-if="data.forzata"
              :value="t('pagamenti.righe.forzata')"
              severity="warn"
              class="ml-05"
            />
          </template>

          <template #actions="{ data }">
            <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
          </template>
        </DrawerTabLista>

        <!-- Master-detail inline: il form vive SOTTO la lista, mai in un drawer
             annidato (pattern di progetto). -->
        <DistintaRigaForm
          v-if="formMode"
          :contabile-id="distintaId"
          :riga="rigaInModifica"
          @salvata="ricarica"
          @annulla="formMode = null; rigaInModifica = null"
        />
      </template>
    </div>

    <!-- ⚠️ In form mode il footer sparisce: il form ha gia' Annulla/Salva, e un
         «Chiudi» in fondo spingerebbe il form sotto il fold. -->
    <FormFooter v-if="!formMode" close-only @cancel="onClose" />

    <!-- ⭐ Un dialogo, due modi: «abbina» sotto una distinta aperta, «abbina e
         registra» (la tardiva) sotto una registrata. Il modo lo decide il
         composable delle azioni di riga dai fatti della testata. -->
    <AbbinaRigaDialog
      v-model:visible="abbinaVisible"
      :riga="rigaDaAbbinare"
      :modo="modoAbbina"
      @abbinata="ricarica"
    />

    <!-- ⭐ La validazione coi numeri davanti (FE-1): quadratura e righe per
         stato, spenta col motivo del database quando non si puo'. -->
    <ValidaDistintaDialog
      v-model:visible="validaVisible"
      :distinta="distinta"
      :stato-codice="statoDiValidazione?.codice_interno ?? null"
      :stato-descrizione="statoDiValidazione?.descrizione ?? null"
      @validata="ricarica"
    />

    <!-- «La contabile in CSV/Excel»: il dialog chiede solo il formato, il
         download lo fa lo scaffolding (`onExportConfirm`). -->
    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />
    <!-- ⛔ SOLO `apri-distinta`, non anche `cambiata`: chi lo riceve porta il
         drawer sulla distinta nuova E ricarica gia' l'elenco. Emetterli
         entrambi manderebbe DUE richieste identiche, e due risposte possono
         tornare in ordine inverso. -->
    <CorreggiDistintaDialog
      v-model:visible="correggiVisible"
      :distinta="distinta"
      @corretta="(id) => emit('apri-distinta', id)"
    />

    <RegistraDistintaDialog
      v-model:visible="registraVisible"
      :distinta-id="distintaId"
      @registrata="ricarica"
    />

    <!-- ⚠️ `readonly` esplicito: e' il readonly da PERMESSI, non il combinato
         con lo stato — l'azione e' gia' filtrata da `modificabile`. -->
    <RatePickerDialog
      v-model:visible="righeDaRateVisible"
      modalita="multipla"
      :contabile-id="distintaId"
      :readonly="isReadonly"
      @righe-create="ricarica"
    />
  </Drawer>
</template>
