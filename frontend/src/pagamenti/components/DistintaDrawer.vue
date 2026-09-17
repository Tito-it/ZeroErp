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
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
// ⚠️ DataTable grezza, ed e' l'eccezione ammessa dalla regola zero della lista:
//    sono le RIGHE DI UN DOCUMENTO dentro il suo master (frontend-standards
//    §Regola zero). 🔵 Debito dichiarato: la macchina a stati del master-detail
//    e' scritta qui invece di passare da `RigheMasterDetailTable` (28/08).
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'

import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import NaturaDocTag from '../../core/components/NaturaDocTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { bloccoAttivo, motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { statoDistintaSeverity, statoRigaContabileSeverity } from '../../core/utils/severity'
import { cambiaStatoDistinta, cambiaStatoRiga, eliminaRiga, getDistinta } from '../api/pagamenti'
import { formatCurrency } from '../../core/utils/format'
import { useEtichettePagamenti } from '../etichette'
import AbbinaRigaDialog from './AbbinaRigaDialog.vue'
import CorreggiDistintaDialog from './CorreggiDistintaDialog.vue'
import DistintaRigaForm from './DistintaRigaForm.vue'
import RatePickerDialog from './RatePickerDialog.vue'
import RegistraDistintaDialog from './RegistraDistintaDialog.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  distintaId: { type: [Number, null], default: null },
})
// ⭐ `apri-distinta` e non un secondo drawer annidato: la correzione produce un
//    DOCUMENTO NUOVO, e lo si apre al posto di questo — chi corregge deve
//    lavorare la correzione, non guardarla da dietro il documento sbagliato.
const emit = defineEmits(['update:visible', 'cambiata', 'apri-distinta'])

const { t, te } = useI18n()
const { rata: etichettaRata } = useEtichettePagamenti()
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
const registraVisible = ref(false)
const correggiVisible = ref(false)
// Il picker delle rate in modalita' MULTIPLA (D19-d): N rate → N righe.
const righeDaRateVisible = ref(false)

const distinta = computed(() => dettaglio.value?.distinta || null)
const righe = computed(() => dettaglio.value?.righe || [])
const statiDistinta = computed(() => dettaglio.value?.stati_distinta || [])
// ⭐ Il catalogo degli stati di RIGA viaggia nello stesso round-trip, e serve
//    davvero: porta `is_final`, che il singolo record di riga NON espone — la
//    riga porta solo `stato_is_postabile` e `stato_richiede_abbinamento`.
const statiRiga = computed(() => dettaglio.value?.stati_riga || [])
// ⭐ Le uscite ammesse DALLO STATO CORRENTE, per le due macchine: la matrice
//    del database ristretta a cio' che una persona puo' chiedere. Uno stato
//    senza uscite ha la lista vuota — e non e' un errore, e' un fatto.
const transizioniDistinta = computed(
  () => dettaglio.value?.transizioni?.distinta?.[distinta.value?.stato_codice] || [],
)
function transizioniRiga(riga) {
  return dettaglio.value?.transizioni?.riga?.[riga.stato_codice] || []
}

// ⚠️ Il CONTENUTO si lavora solo su una manuale in bozza (D17/D18). Il flag
//    viene dal DETTAGLIO: dedurlo dallo stato («BOZZA» + «MANUALE») sarebbe
//    una seconda copia della regola. ⛔ Fino al 14/09 era `!stato_is_final`:
//    sotto VALIDATA il form si apriva e il database rifiutava.
const modificabile = computed(
  () => !isReadonly.value && distinta.value?.contenuto_modificabile === true,
)

// ── quadratura ────────────────────────────────────────────────────
// ⚠️ `importo_dichiarato` NULL non e' zero: significa «non e' stato dichiarato
//    niente», quindi la quadratura NON SI APPLICA. Mostrare 0,00 direbbe
//    «quadra» di una distinta che nessuno ha mai quadrato. Tre esiti, non due.
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

const quadraturaApplicabile = computed(() => distinta.value?.importo_dichiarato != null)
const scarto = computed(() => distinta.value?.scarto_dichiarato ?? null)
const quadra = computed(
  () => quadraturaApplicabile.value && Number(scarto.value || 0) === 0,
)

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
        command: () => onCambiaStato(codice, stato?.descrizione || codice, stato?.is_final),
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
      action: 'registra_distinta',
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
  if (!distinta.value.stato_is_final) {
    azioni.push({
      key: 'registra',
      kind: 'primary',
      label: t('pagamenti.registra.azione'),
      icon: 'pi pi-lock',
      severity: 'danger',
      hideWhenReadonly: true,
      // ⚠️ Il cancello vero e' il backend (`post_permission = registra_distinta`);
      //    qui si evita solo di PROPORRE cio' che verrebbe rifiutato.
      action: 'registra_distinta',
      command: () => { registraVisible.value = true },
    })
  }
  return azioni
})

const pageActionsRighe = computed(() => [
  {
    key: 'nuova-riga',
    kind: 'primary',
    label: t('pagamenti.righe.nuova'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    visible: modificabile.value && formMode.value === null,
    command: () => { rigaInModifica.value = null; formMode.value = 'create' },
  },
  // ⭐ «Righe da rate»: si scelgono le rate dallo scadenzario e ogni rata
  //    diventa una riga (D1 reso a video). Stesso cancello di «Nuova riga»:
  //    e' un altro modo di scriverne, non un altro permesso.
  {
    key: 'righe-da-rate',
    // Inline accanto a «Nuova riga» (non nel kebab): e' il gesto principale
    // della distinta manuale, non un'azione rara.
    severity: 'primary',
    label: t('pagamenti.rate.righe_da_rate'),
    icon: 'pi pi-list-check',
    hideWhenReadonly: true,
    visible: modificabile.value && formMode.value === null,
    command: () => { righeDaRateVisible.value = true },
  },
])

// ── azioni di riga ────────────────────────────────────────────────
// ⭐ «Permesso ⇒ nascondi, stato ⇒ disabilita col motivo»: qui e' lo STATO a
//    decidere, quindi le voci non applicabili si disabilitano con la ragione
//    invece di sparire — una voce che sparisce non spiega niente.
//
// ⭐ Le transizioni della riga vengono dalla MATRICE, per lo stato in cui la
//    riga si trova (`transizioni.riga[stato]`), esattamente come quelle della
//    testata. ⛔ La prima stesura ne scriveva DUE a mano; la seconda offriva il
//    vocabolario intero meno lo stato corrente, e su una riga ABBINATA
//    proponeva SCARTATA — che la matrice non ammette e il database rifiutava.
//    Un vocabolario offerto per intero non e' una matrice (brief §8).
//
// ⛔ L'UNICA esclusa e' quella che ha un VERBO PROPRIO: ad `ABBINATA` non ci si
//    porta cambiando stato — ci si arriva scegliendo la fattura. Offrirla come
//    transizione darebbe un pulsante che il database rifiuta, e il rifiuto
//    parlerebbe di un campo che a video non si e' mai visto.
const STATO_RIGA_CON_VERBO_PROPRIO = 'ABBINATA'

// ⭐ Le icone delle transizioni. ⚠️ E' una mappa COSMETICA, e la differenza col
//    codice cablato di prima e' tutta qui: se il catalogo cresce, uno stato
//    sconosciuto prende l'icona generica e **funziona lo stesso** — mentre
//    prima uno stato sconosciuto semplicemente non compariva. Stessa forma e
//    stessa ragione della mappa dei colori in `core/utils/severity.js`.
// ⛔ Senza, le voci sarebbero tre spunte identiche: nella variante desktop il
//    menu e' icon-only, e tre icone uguali non si distinguono.
// ⛔ SCARTATA NON E' IL CESTINO (D17-e, 14/09): «scarta» vuol dire «denaro
//    arrivato, non nostro» e conta nella quadratura; «elimina» toglie una riga
//    digitata male. Col cestino su «scarta» Tid ha letto uno stato di dominio
//    come un'eliminazione — la stessa lezione di `UNDO` in `constants.js`
//    (19/08). Il cestino da oggi e' di «Elimina», e basta. L'icona e'
//    letterale perche' ha un lettore solo (frontend-standards §«dove vive il
//    nome di un'icona»).
const ICONA_TRANSIZIONE_RIGA = {
  DA_ABBINARE: 'pi pi-link',
  SOSPESA: 'pi pi-pause',
  SCARTATA: 'pi pi-ban',
}

// Scopo: la riga di catalogo dello stato in cui la riga si trova.
// ⚠️ `is_final` viene da li' e NON si deduce dal nome: `POSTATA` non e' l'unico
//    stato terminale del catalogo, e un confronto col nome avrebbe lasciato
//    lavorabile una riga terminale — cioe' offerto gesti che finiscono in
//    errore.
function catalogoRiga(codice) {
  return statiRiga.value.find((s) => s.codice_interno === codice) || null
}

function buildRowActions(riga) {
  // ⛔ In sola lettura si NASCONDE: li' non e' lo stato, e' il permesso — e
  //    «non hai il permesso» non e' qualcosa che l'operatore possa risolvere da
  //    li'. ⚠️ `RowActionsMenu` non conosce `hideWhenReadonly` (lo onora
  //    `DrawerActionsBar`, non lui): il filtro va fatto qui.
  if (isReadonly.value) return []

  const finale = catalogoRiga(riga.stato_codice)?.is_final === true
  const foglioChiuso = distinta.value?.stato_is_final === true
  const bloccata = finale || foglioChiuso
  // ⭐ Il motivo dice QUALE dei due blocchi e' scattato: «la riga e' gia'
  //    registrata» e «il foglio e' chiuso» si rimediano in due modi diversi, e
  //    una voce grigia senza spiegazione non si rimedia affatto.
  const motivoFinale = finale
    ? t('pagamenti.righe.gia_registrata')
    : foglioChiuso
      ? t('pagamenti.distinte.foglio_chiuso')
      : undefined

  const transizioni = transizioniRiga(riga)
    .filter((codice) => codice !== STATO_RIGA_CON_VERBO_PROPRIO)
    .map((codice) => {
      const stato = catalogoRiga(codice)
      const descrizione = stato?.descrizione || codice
      return {
        key: `stato-${codice}`,
        label: t('pagamenti.righe.porta_a', { stato: descrizione }),
        icon: ICONA_TRANSIZIONE_RIGA[codice] || MANAGE_ICONS.CONFIRM,
        severity: stato?.is_final ? 'danger' : undefined,
        disabled: bloccata,
        tooltip: motivoFinale,
        command: () => onCambiaStatoRiga(riga, codice, descrizione, stato?.is_final),
      }
    })

  // ⭐ ELIMINA (D17): il cestino, spento COL MOTIVO che manda il database —
  //    la stessa check che il guard chiama per rifiutare, quindi tooltip e
  //    409 non possono dire due cose diverse. La terna la legge il BB
  //    `bloccoMotivo` (prefisso `elimina_blocco`, flag `can_eliminare`).
  //    ⛔ Nessun `if stato === ...` qui: sotto VALIDATA, su una GENERATA, su
  //    una CHIUSA il motivo e' del database, e cambia frase da solo.
  const eliminaBloccata = bloccoAttivo(riga, 'elimina_blocco', 'can_eliminare')
  const elimina = {
    key: 'elimina',
    label: t('pagamenti.righe.elimina'),
    icon: MANAGE_ICONS.DELETE,
    severity: 'danger',
    disabled: eliminaBloccata,
    tooltip: eliminaBloccata ? motivoBloccoRiga(t, te, riga, 'elimina_blocco') : undefined,
    command: () => onEliminaRiga(riga),
  }

  return [
    {
      key: 'abbina',
      label: t('pagamenti.abbina.azione'),
      icon: MANAGE_ICONS.BILLING_ACCOUNT,
      disabled: bloccata,
      tooltip: motivoFinale,
      command: () => { rigaDaAbbinare.value = riga; abbinaVisible.value = true },
    },
    ...transizioni,
    elimina,
  ]
}

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

// Scopo: ricarica dopo un gesto e avvisa la lista, che mostra i contatori.
async function ricarica() {
  formMode.value = null
  rigaInModifica.value = null
  await loadDetail()
  emit('cambiata')
}

function onCambiaStato(codice, descrizione, terminale) {
  confirmAction({
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

function onCambiaStatoRiga(riga, codice, descrizione, terminale) {
  confirmAction({
    // ⚠️ La conferma NOMINA lo stato: «vuoi cambiare stato?» non basta a
    //    decidere, adesso che le transizioni possibili sono piu' di due.
    message: t('pagamenti.righe.conferma_stato_a', { stato: descrizione || codice }),
    // ⛔ Era `codice === 'SCARTATA'`, e il modello dice il contrario: nel
    //    catalogo `SCARTATA` NON e' terminale (`is_final = false`), quindi
    //    quel rosso allarmava per un gesto reversibile. Il catalogo decide.
    danger: terminale === true,
    onAccept: async () => {
      const esito = await execute(
        () => cambiaStatoRiga(riga.id, codice),
        { successMessage: t('pagamenti.righe.stato_cambiato') },
      )
      if (esito !== null) ricarica()
    },
  })
}

// Scopo: elimina una riga (attivo = false) dopo conferma. ⭐ Rossa: la riga
//        sparisce dall'elenco e dalla quadratura. Il rifiuto — se il foglio
//        non e' piu' in bozza — arriva dal database con la sua frase.
function onEliminaRiga(riga) {
  confirmAction({
    message: t('pagamenti.righe.conferma_elimina', {
      importo: formatCurrency(riga.importo),
      riferimento: riga.riferimento_ente || '—',
    }),
    danger: true,
    onAccept: async () => {
      const esito = await execute(
        () => eliminaRiga(riga.id),
        { successMessage: t('pagamenti.righe.eliminata') },
      )
      if (esito !== null) ricarica()
    },
  })
}

// ⚠️ Il click sulla riga apre la MODIFICA solo se il contenuto si lavora: su
//    una distinta validata o chiusa aprirebbe un form che il database rifiuta.
function onRigaClick(evento) {
  if (!modificabile.value) return
  rigaInModifica.value = evento.data
  formMode.value = 'edit'
}

watch(
  () => [props.visible, props.distintaId],
  ([vis]) => {
    if (vis && props.distintaId) {
      formMode.value = null
      rigaInModifica.value = null
      loadDetail()
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
          <Tag :value="distinta.codice" severity="secondary" />
          <!-- ⭐ DI CHI E', a colpo d'occhio (FE-2 del brief distinta-numerata-
               sul-registro): la sigla sta gia' dentro il codice nuovo
               (`DIS-<SIGLA>-…`), ma non nel pregresso `VC_…`, e comunque una
               sigla non e' un nome. Si mostra la ragione sociale, e si ripiega
               sulla sigla se il nome non e' arrivato — mai un vuoto che si
               leggerebbe come «di nessuno». -->
          <span
            v-if="distinta.emittente_ragione_sociale || distinta.emittente_fiscale_codice"
            class="app-drawer-header-muted"
            v-tooltip.bottom="distinta.emittente_fiscale_codice || undefined"
          >
            {{ distinta.emittente_ragione_sociale || distinta.emittente_fiscale_codice }}
          </span>
          <span class="app-drawer-header-muted">
            {{ displayDate(distinta.data_contabile) }}
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

        <!-- ══ La quadratura ══ -->
        <div class="app-drawer-section">
          <h4>{{ t('pagamenti.distinte.sezione_quadratura') }}</h4>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('pagamenti.distinte.col_importo_dichiarato') }}</label>
            <span>{{ formatCurrency(distinta.importo_dichiarato) }}</span>
          </div>
          <div class="form-field">
            <label>{{ t('pagamenti.distinte.col_totale_righe') }}</label>
            <span>{{ formatCurrency(distinta.totale_righe) }}</span>
          </div>
          <div class="form-field">
            <label>{{ t('pagamenti.distinte.col_scarto_dichiarato') }}</label>
            <!-- ⭐ Tre esiti, non due: quadra · non quadra · non si applica. -->
            <span v-if="!quadraturaApplicabile" class="app-text-muted">
              {{ t('pagamenti.distinte.quadratura_non_applicabile') }}
            </span>
            <Tag v-else-if="!quadra" :value="formatCurrency(scarto)" severity="warn" />
            <Tag v-else :value="t('pagamenti.distinte.quadra')" severity="success" />
          </div>
          <div class="form-field">
            <label>{{ t('pagamenti.distinte.col_righe_registrabili') }}</label>
            <span>
              {{ distinta.righe_registrabili ?? 0 }} / {{ distinta.righe_totali ?? 0 }}
            </span>
          </div>
        </div>

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

        <div class="app-page-toolbar">
          <div class="app-page-filters" />
          <PageActionsBar :actions="pageActionsRighe" />
        </div>

        <DataTable
          :value="righe"
          class="app-datatable app-datatable--inner"
          data-key="id"
          scrollable
          scroll-height="flex"
          @row-click="onRigaClick"
        >
          <Column field="data_pagamento" :header="t('pagamenti.righe.col_data_pagamento')">
            <template #body="{ data }">{{ displayDate(data.data_pagamento) }}</template>
          </Column>
          <Column field="riferimento_ente" :header="t('pagamenti.righe.col_riferimento_ente')">
            <template #body="{ data }">{{ data.riferimento_ente || '—' }}</template>
          </Column>
          <Column
            field="importo"
            :header="t('pagamenti.righe.col_importo')"
            style="text-align: right;"
          >
            <template #body="{ data }">{{ formatCurrency(data.importo) }}</template>
          </Column>
          <Column
            field="billing_account_descrizione"
            :header="t('pagamenti.righe.col_billing_account_descrizione')"
          >
            <template #body="{ data }">{{ data.billing_account_descrizione || '—' }}</template>
          </Column>
          <!-- ⭐ IL DOCUMENTO, NON IL CONTATORE (D19-b): il numero parlante
               viene dalla sede unica a DB (`fattura_numero_documento`), e non
               si compone qui — `fattura_numero` da solo e' ambiguo (una
               fattura 1 e una nota di credito 1 nello stesso anno). La natura
               si segnala quando non e' una fattura. -->
          <Column field="fattura_numero_documento" :header="t('pagamenti.righe.col_documento')">
            <template #body="{ data }">
              <template v-if="data.fattura_id != null">
                <span>{{ data.fattura_numero_documento || t('fattura_lookup.senza_numero') }}</span>
                <NaturaDocTag
                  :codice="data.fattura_natura_doc_codice_interno"
                  :descrizione="data.fattura_natura_doc_descrizione"
                  class="ml-05"
                />
              </template>
              <template v-else>—</template>
            </template>
          </Column>
          <!-- La rata: «n. · scadenza». Vuota sulla riga senza rata — il fondo
               fattura e' cosi', non e' un dato perso. -->
          <Column field="scadenza_numero_rata" :header="t('pagamenti.righe.col_rata')">
            <template #body="{ data }">
              <template v-if="data.scadenza_id != null">
                {{ etichettaRata({ numero_rata: data.scadenza_numero_rata, data_scadenza: data.scadenza_data }) }}
              </template>
              <template v-else>—</template>
            </template>
          </Column>
          <Column field="stato_descrizione" :header="t('pagamenti.righe.col_stato')">
            <template #body="{ data }">
              <Tag
                :value="data.stato_descrizione || data.stato_codice"
                :severity="statoRigaContabileSeverity(data.stato_codice)"
              />
              <!-- ⭐ La forzatura resta SCRITTA sulla riga ed e' cio' che
                   l'elenco delle rate fuori capienza legge: qui si vede, o la
                   riga racconta meno di quello che e' successo. -->
              <Tag
                v-if="data.forzata"
                :value="t('pagamenti.righe.forzata')"
                severity="warn"
              />
            </template>
          </Column>
          <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
            <template #body="{ data }">
              <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
            </template>
          </Column>
          <template #empty>
            <div class="app-empty-state">
              <i class="pi pi-list" />
              <p>{{ t('pagamenti.distinte.nessuna_riga') }}</p>
            </div>
          </template>
        </DataTable>

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

    <AbbinaRigaDialog
      v-model:visible="abbinaVisible"
      :riga="rigaDaAbbinare"
      @abbinata="ricarica"
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
