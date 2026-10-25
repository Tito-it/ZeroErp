<script setup>
// Scopo: Drawer di CONSULTAZIONE della fattura — il documento a video, nello
//        stesso formato degli altri documenti vendite: testata (cliente,
//        emittente, pagamento, totali) in alto, righe al centro, riepilogo IVA
//        in fondo.
//        Generico e richiamabile da più punti: dal kebab delle righe fatture
//        del `LottoDrawer` e dal registro `core/drawerEntita` (tappe Passaggi,
//        drill-down cruscotti); domani ricerca universale, portale.
//        SOLA LETTURA per costruzione: la fattura è prodotta dalla pipeline e
//        oltre la soglia di congelamento le righe sono congelate a DB
//        (`trgfn_fattura_satellite_guard_congelamento`; la soglia è un dato,
//        `config.stati_doc_fiscale.congela_fiscale`). Le azioni di processo
//        (emissione, numerazione, ristampa massiva) restano nel cockpit.
//        I dati arrivano dagli STESSI lettori che alimentano il contesto del
//        PDF: ciò che si vede qui è ciò che finisce nel documento fiscale.
//        Le righe vengono dalla vista della lista (`vw_fattura_righe_lista`),
//        la stessa del contesto di stampa dal 2026-09-30 (forma 2,
//        brief-db-documenti-versione-contesto-template §11).
//        Brief: docs/it/dev/work-done/brief-be-fe-drawer-fattura.md
//
// ⛔ NESSUN cancello ne' etichetta di perimetro emittente qui, ed e' una
//    decisione (P-2c del brief perimetro-emittente), non una dimenticanza.
//    Un DOCUMENTO SI DICHIARA: la testata mostra chi lo ha emesso, e non c'e'
//    niente accanto con cui confonderlo — l'ambiguita' che il cancello e le
//    etichette curano nasce dall'AFFIANCAMENTO di righe o dall'aggregazione di
//    numeri, che qui non c'e'.
//    Aggiungerlo «per coerenza» con liste e cruscotti significherebbe chiedere
//    all'operatore di scegliere un emittente per leggere un documento che gli
//    sta gia' dicendo da quale emittente viene.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { labelOrCode } from '../../core/utils/i18nLabel'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import NaturaDocTag from '../../core/components/NaturaDocTag.vue'
import PuntoEstensione from '../../core/components/PuntoEstensione.vue'
import { PUNTI_ESTENSIONE, precaricaPunto } from '../../core/estensioni'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import InputText from 'primevue/inputtext'
import RiepilogoIvaTable from '../../core/components/RiepilogoIvaTable.vue'
import ScadenzeSintesi from '../../core/components/ScadenzeSintesi.vue'
import PdfDocumentiSorgenteDialog from '../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import DocumentoCollegamentiBar from '../_shared/lineage/DocumentoCollegamentiBar.vue'
import FatturaNoteDrawer from './FatturaNoteDrawer.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useContatoreNote } from '../../core/composables/useContatoreNote'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useDocumentiPerSorgenteStore } from '../../documenti/stores/documentiPerSorgente'
import { SORGENTE_CODES } from '../../documenti/constants'
import {
  DRAWER_WIDTH,
  MANAGE_ICONS,
  READONLY_DOMAINS,
  READONLY_MODELS,
  STATUS_ICONS,
} from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate } from '../../core/utils/date'
import { formatCurrency, formatNumber, formatQuantita } from '../../core/utils/format'
import { statoDocFiscaleSeverity } from '../../core/utils/severity'
import { downloadBlob } from '../../core/utils/download'
import { exportRigheLista, getFatturaDettaglio } from '../api/fatture'
import { useFatturaRigheStore } from '../stores/fatturaRighe'
import GiornaleEntitaTab from '../_shared/giornale/GiornaleEntitaTab.vue'
import { useFatturaGiornaleStore } from '../stores/giornaleEntita'

const props = defineProps({
  visible: { type: Boolean, default: false },
  fatturaId: { type: [Number, null], default: null },
})

const emit = defineEmits(['update:visible'])
const { t, te } = useI18n()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
// I contributi al punto si caricano ora, non quando il punto si monta.
precaricaPunto(PUNTI_ESTENSIONE.FATTURA_DRAWER_SEZIONI)
const { execute } = useApiHandler()
const docStore = useDocumentiPerSorgenteStore()

// Livello oggetto: `vendite.fattura` è in `config.area_model_overrides` e il
// BE dichiara `model_permission` sia sul dettaglio sia sulle note — il drawer
// deve rispettarlo (brief §11). Il composable fa anche `provide()` ai figli:
// il `NoteDrawer` (via `useInjectReadonly`) eredita il readonly di OGGETTO,
// non solo quello d'area del provider a monte.
const { isReadonly, isBlocked } = useReadonlyMode(
  READONLY_DOMAINS.VENDITE, READONLY_MODELS.FATTURA,
)

// Guard di versione: il drawer è un'istanza unica riusata cambiando
// `fatturaId` — due aperture rapide su fatture diverse sono due fetch in volo
// sullo stesso `dettaglio`. Senza il tag, la risposta arrivata per ultima
// vince anche se è quella della fattura sbagliata.
const fv = useFetchVersion()

// ------------------------------------------------------------------ stato
const dettaglio = ref(null)
const loading = ref(false)
const pdfDialog = ref(false)
const noteDrawer = ref(false)
// Scheda attiva. ⚠️ CONTROLLATA e non fissa: il link del banner d'errore la
// cambia, e alla riapertura si riparte SEMPRE dal documento — un drawer che
// si apre in un punto diverso a ogni giro fa perdere il riferimento (stessa
// regola del `LottoDrawer`).
const tabAttiva = ref('documento')

const fattura = computed(() => dettaglio.value?.fattura ?? null)
// ⭐ Le righe COMPLETE del documento (dal dettaglio, vista `vw_fattura_righe_
//    lista`): le legge il drawer delle note per il selettore di riga. La
//    lista a video e' un'altra lettura della STESSA vista, paginata (sotto).
const righe = computed(() => dettaglio.value?.righe ?? [])

// ⭐ LE RIGHE A VIDEO SONO UNA LISTA STANDARD (brief-db-liste-righe-documento,
//    lotto C, 2026-09-28): `vendite.fattura_righe`, colonne dal catalogo con
//    ritiro nella riga espandibile, ricerca, export. Sola lettura: nessun form.
//    Prima era una `DataTable` grezza, che su tablet scorreva in orizzontale.
// ⭐ Il padre e' COMPOSTO: la fattura e il suo emittente (la PK). L'emittente
//    scioglie il cancello di perimetro della lista per chi vede piu'
//    emittenti — il documento lo dichiara, non lo si chiede all'operatore
//    (resta vero il «nessun cancello a video» scritto in testa).
// ⚠️ La fattura porta l'id SOLO a drawer aperto: il `null` alla chiusura
//    azzera la lista, o le righe della fattura precedente lampeggerebbero
//    sotto la prossima.
const righeStore = useFatturaRigheStore()
const {
  searchText: righeSearch, onPage: onRighePage, onSort: onRigheSort,
  paginatorProps: righePaginator, tablePage: righePage, listaRef: righeListaRef,
  dirty: righeDirty, onConfigLoaded: onRigheConfigLoaded, pageActions: righeActions,
  perimetroBloccato: righePerimetroBloccato,
  exportDialogVisible: righeExportVisible, exportLoading: righeExportLoading,
  onExportConfirm: onRigheExportConfirm,
} = useDrawerTabLista(righeStore, {
  parentId: {
    documentoId: () => (props.visible ? props.fatturaId : null),
    emittenteId: () => fattura.value?.emittente_fiscale_pk ?? null,
  },
  exportFn: (params) => exportRigheLista(props.fatturaId, params),
  getExportParams: (formato) => ({ formato, ...righeStore.paramsExport() }),
})
const riepilogoIva = computed(() => dettaglio.value?.riepilogo_iva ?? [])
const scadenze = computed(() => dettaglio.value?.scadenze ?? [])

// Il pulsante «Gestisci note» standard, col numero delle note (BB
// `useContatoreNote`, dal 2026-10-25 lo stesso di ogni documento): DUE fonti,
// il payload BE all'apertura (`contatori.note`, nessun round-trip aggiuntivo)
// e il sub-drawer note dopo ogni create/update/delete, che il totale
// aggiornato ce l'ha già e lo passa con `@saved`. Il conteggio BE usa lo
// stesso perimetro della lista note, quindi i due valori non divergono.
// ⚠️ Dopo un salvataggio il dettaglio NON si rilegge: ricaricarlo mentre il
//    drawer note è aperto sopra rigenererebbe `righe`, cioè le opzioni del
//    select riga che il figlio sta usando.
const contatoreNote = useContatoreNote(dettaglio)

// ⭐ LA STORIA DEL DOCUMENTO (Passo A del filone osservabilità). Dal 2026-09-27
// è la lista a catalogo `vendite.giornale` filtrata sulla fattura, resa dal
// tab condiviso col `LottoDrawer` (`GiornaleEntitaTab`): qui resta solo lo
// store, da cui la scheda legge il suo conteggio. ⚠️ Il tab si monta con il
// documento (i pannelli di `Tabs` non sono lazy): la storia si chiede
// all'apertura, e il conteggio nell'etichetta c'è prima di entrarci.
const giornaleStore = useFatturaGiornaleStore()

// ⭐ L'ERRORE IN EVIDENZA. Un documento che non si è potuto numerare deve dirlo
// in testa, non in fondo alla terza schermata: chi apre la fattura la apre
// PROPRIO perché qualcosa non è andato.
// ⭐ FONTE SUA, NEL DETTAGLIO (`errore_vivo`, 2026-09-27): la riga ERROR più
// recente e non ritirata, scelta dal BACKEND. ⛔ Fino a quel giorno era «il
// primo ERROR della pagina della Storia», che era ordinata per gravità; da
// quando la Storia è la lista a catalogo, l'ordine lo decide il preset
// (`quando desc`) o l'operatore, e il banner avrebbe taciuto appena l'errore
// fosse scivolato a pagina 2 — un documento in errore che a video sembra sano.
const erroreVivo = computed(() => dettaglio.value?.errore_vivo ?? null)

// Scopo: il link del banner — porta sulla scheda dove l'errore è raccontato per
//        intero, invece di lasciare l'operatore a cercarlo.
function apriStoria() {
  tabAttiva.value = 'storia'
}

// Numero fiscale: una fattura in DRAFT ha `numero` NULL — il progressivo si
// assegna alla numerazione. Renderlo esplicito, mai una cella vuota: in un
// documento fiscale un vuoto si legge come dato perso, non come stato del
// processo.
// Scopo: il numero fiscale in una stringa — «1234 - R1».
// ⛔ QUESTA NON E' PIU' LA SEDE DEL FORMATO, e la riga qui sopra diceva di
//    esserlo: la sede e' `vendite.fn_numero_documento_fattura` (20260829-15), e
//    qui si legge soltanto. La ragione per cui la sede dev'essere una sola non
//    e' cambiata — due copie mostrerebbero lo STESSO documento in due modi
//    diversi nella stessa schermata alla prima modifica — e' cambiato DOVE
//    sta: nel database, dove la vedono anche il grafo e le altre schermate.
// ⛔ QUI NON SI COMPONE PIU'. Il numero documento di una fattura ha UNA sede,
// ed e' `vendite.fn_numero_documento_fattura` (20260829-15): forma
// `numero - serie`, senza anno perche' accanto c'e' sempre la data. Prima
// questa funzione ne produceva una sua (`serie numero/anno`), il drawer del
// lotto un'altra e la dashboard competenza una terza — tre schermate, tre modi
// di scrivere lo stesso documento.
// ⚠️ Il ripiego resta QUI, e non a DB: il backend risponde NULL su un documento
// non ancora numerato, e la frase da mostrare la sceglie chi rende — questa
// dice «non numerata», il drawer del lotto un trattino. Un placeholder scritto
// a DB avrebbe tolto la scelta a entrambi.
function numeroDocumento(doc) {
  return doc?.numero_documento || t('vendite.fatture.non_numerata')
}

const numeroDisplay = computed(() =>
  fattura.value ? numeroDocumento(fattura.value) : '',
)

// Legame documentale (B7/F5). Il backend risponde nei due versi; a video se ne
// mostra UNO — quello che questo documento «è»:
//   · una nota di credito dice cosa RETTIFICA,
//   · una fattura dice da quali note è stata RETTIFICATA.
// ⚠️ Non si sommano le due liste: sarebbero due frasi diverse sotto la stessa
// etichetta, e l'operatore non saprebbe in che verso leggerla.
// I due versi si mostrano ENTRAMBI se entrambi hanno righe. ⚠️ La prima
// versione ne rendeva uno solo («quello che il documento è») e nel caso —
// raro ma ammesso dal modello — di un documento che rettifica ed è a sua volta
// rettificato ne avrebbe nascosto uno **in silenzio**. Ogni blocco porta la
// propria etichetta, quindi il verso resta leggibile.
const blocchiCollegati = computed(() => {
  const r = dettaglio.value?.rettifiche ?? {}
  return [
    { verso: 'rettifica', labelKey: 'vendite.fatture.rettifica_di', documenti: r.rettifica ?? [] },
    { verso: 'rettificata_da', labelKey: 'vendite.fatture.rettificata_da', documenti: r.rettificata_da ?? [] },
  ].filter((b) => b.documenti.length)
})

// Scopo: il documento collegato in una stringa sola, scritto come
//        `numeroDisplay` scrive il documento corrente — così i due si leggono
//        uguale. ⭐ Adesso lo garantisce il backend e non piu' questo file:
//        testata e legami portano entrambi `numero_documento` dalla stessa
//        funzione DB.
function documentoLabel(d) {
  const numero = numeroDocumento(d)
  return d.data ? `${numero} — ${displayDate(d.data)}` : numero
}

// ------------------------------------------------------------------ load
// Scopo: carica il documento; 404/fuori scope → toast + chiusura (il BE non
//        distingue inesistente da fuori scope, e il drawer non deve provarci).
async function loadDettaglio() {
  if (!props.fatturaId) return
  const my = fv.tag()
  loading.value = true
  try {
    const res = await loadDetailOrClose(() => getFatturaDettaglio(props.fatturaId))
    if (!fv.isCurrent(my)) return
    if (res == null) return
    dettaglio.value = res.data?.data ?? null
  } finally {
    if (fv.isCurrent(my)) loading.value = false
  }
}

watch(
  () => [props.visible, props.fatturaId],
  async ([visible]) => {
    // Dialog documenti e drawer note sono teleported (fuori dal DOM di questo
    // drawer): senza chiusura esplicita resterebbero aperti orfani quando il
    // padre si chiude. Stesso presidio del `LottoDrawer`.
    pdfDialog.value = false
    noteDrawer.value = false
    if (!visible || !props.fatturaId) {
      // Invalida le fetch in volo: una risposta tardiva non deve ripopolare
      // il drawer chiuso (o quello riaperto su un'altra fattura).
      fv.invalidate()
      return
    }
    dettaglio.value = null
    tabAttiva.value = 'documento'
    // ⚠️ La storia NON si chiede qui: la chiede il tab quando si monta, cioè
    // dopo il dettaglio (sta dentro `v-if="fattura"`) — se la fattura non è
    // accessibile il drawer si è già chiuso, e nessuna lettura parte su un id
    // negato.
    await loadDettaglio()
  },
  { immediate: true },
)

// Campi della testata come DATI e non come markup ripetuto: dodici blocchi
// label/valore copiati a mano sono dodici occasioni di sbagliare una chiave
// senza che nulla se ne accorga (a video comparirebbe solo un '—').
// ⚠️ `labelKey` con la chiave i18n COMPLETA e LETTERALE, mai costruita a
// pezzi: è la forma che `scripts/check_i18n_keys.py` sa verificare
// (`RE_KEYPROP`). Un `t(\`vendite.fatture.${k}\`)` diventerebbe un "punto
// cieco" del guard, cioè esattamente il difetto silenzioso che quel guard
// esiste per intercettare.
const campiCliente = computed(() => {
  const f = fattura.value ?? {}
  return [
    { labelKey: 'vendite.fatture.cliente', value: f.ragione_sociale_completa },
    { labelKey: 'vendite.fatture.id_fiscale', value: f.id_fiscale_univoco_cf_piva },
    { labelKey: 'vendite.fatture.indirizzo', value: f.cliente_indirizzo },
    { labelKey: 'vendite.fatture.ba', value: f.ba_codice },
  ]
})

const campiDocumento = computed(() => {
  const f = fattura.value ?? {}
  return [
    { labelKey: 'vendite.fatture.tipo_doc', value: f.tipo_doc_fiscale_descrizione },
    { labelKey: 'vendite.fatture.emittente', value: f.emittente_denominazione },
    { labelKey: 'vendite.fatture.pagamento', value: f.pagamento_modalita_codice },
    {
      labelKey: 'vendite.fatture.data_contabilizzazione',
      value: f.data_contabilizzazione ? displayDate(f.data_contabilizzazione) : null,
    },
  ]
})

// Totali di CHIUSURA, resi sotto il riepilogo IVA: imponibile e imposta NON si
// ripetono qui — sono già il footer di quadratura di `RiepilogoIvaTable`.
// Restano bollo e arrotondamento (solo se valorizzati: sono rettifiche, non
// voci fisse del documento) e le due righe forti di totale.
// ⚠️ `totale_doc` NON è la somma del riepilogo IVA: include bollo e
// arrotondamento. È il numero della testata, l'unico autorevole.
const campiTotali = computed(() => {
  const f = fattura.value ?? {}
  const arrotondamento = Number(f.arrotondamento_attuale ?? 0)
  return [
    {
      labelKey: 'vendite.fatture.bollo',
      importo: f.bollo_importo,
      visible: f.bollo_applicato === true,
    },
    {
      labelKey: 'vendite.fatture.arrotondamento',
      importo: f.arrotondamento_attuale,
      visible: arrotondamento !== 0,
    },
    { labelKey: 'vendite.fatture.totale_doc', importo: f.totale_doc, forte: true },
    { labelKey: 'vendite.fatture.totale_a_pagare', importo: f.totale_a_pagare, forte: true },
  ].filter((c) => c.visible !== false)
})

// Utility del billing account: qualificatore di contesto della fattura, reso
// sotto lo stato. Descrizione con fallback sul codice (`utility_codice` è
// sempre valorizzato, la descrizione può mancare su config incomplete).
const utilityLabel = computed(() => {
  const f = fattura.value ?? {}
  return f.utility_descrizione || f.utility_codice || null
})

// ------------------------------------------------------------------ azioni
// Nessun verbo di modifica: consultazione, stampa, archivio PDF e note. La
// stampa è una LETTURA (render on-the-fly, nessun record): disponibile anche
// in sola lettura, come nel `LottoDrawer` (C-8).

// Scopo: anteprima PDF sincrona on-the-fly («Vedi stampa», brief §4): render
//        della fattura corrente via motore documentale, download immediato.
async function anteprimaFattura() {
  docStore.setSorgente(SORGENTE_CODES.FATTURA, props.fatturaId)
  const result = await execute(() => docStore.anteprima({}))
  if (result) downloadBlob(result.blob, result.fileName)
}

const drawerActions = computed(() => [
  {
    key: 'anteprima',
    kind: 'manage',
    label: t('vendite.fatture.azione_anteprima'),
    icon: MANAGE_ICONS.PDF,
    disabled: !props.fatturaId,
    command: anteprimaFattura,
  },
  {
    key: 'documenti',
    kind: 'manage',
    label: t('vendite.fatture.azione_documenti'),
    icon: MANAGE_ICONS.ARCHIVE,
    disabled: !props.fatturaId,
    command: () => { pdfDialog.value = true },
  },
  contatoreNote.azione({
    label: t('vendite.fatture.azione_note'),
    disabled: !props.fatturaId,
    command: () => { noteDrawer.value = true },
  }),
])

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <!-- Livello oggetto BLOCCATO: pannello sostitutivo (safety net — il BE
       risponde comunque 403 sul dettaglio). -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.fatture.drawer_titolo')"
    :icon="NAV_ICONS.FATTURE"
    :width="DRAWER_WIDTH.WIDE"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <AccessoBloccatoPanel v-if="isBlocked" />
    <template v-else>
      <div v-if="loading && !fattura" class="app-loading">
        <i :class="STATUS_ICONS.CARICAMENTO" />
      </div>

      <template v-if="fattura">
        <!-- Header: numero e data emissione etichettati (in un documento
             fiscale un valore nudo non dice quale dei due è). Il cliente non
             sta qui: è la prima voce della sezione Cliente. -->
        <DrawerEntityHeader>
          <span class="app-drawer-header-muted">{{ t('vendite.fatture.label_numero') }}</span>
          <Tag :value="numeroDisplay" severity="secondary" />
          <template v-if="fattura.data">
            <span class="app-drawer-header-muted">
              {{ t('vendite.fatture.data_emissione') }}
            </span>
            <span>{{ displayDate(fattura.data) }}</span>
          </template>
          <template #status>
            <!-- Stato in alto, utility sotto: è il contesto del documento
                 (quale servizio si sta fatturando), non un suo stato. -->
            <div class="app-drawer-header-status-stack">
              <!-- Natura del documento: si dichiara solo quando NON è una
                   fattura (B5) — lo decide il BB, che tace sulla ordinaria.
                   ⚠️ Mostrarla sempre («Fattura» su una fattura)
                   aggiungerebbe rumore al caso normale e toglierebbe forza
                   al caso che conta. -->
              <NaturaDocTag
                :codice="fattura.natura_doc_codice_interno"
                :descrizione="fattura.natura_doc_descrizione"
              />
              <Tag
                v-if="fattura.stato_descrizione"
                :value="fattura.stato_descrizione"
                :severity="statoDocFiscaleSeverity(fattura.stato_codice_interno)"
              />
              <Tag v-if="utilityLabel" :value="utilityLabel" severity="info" />
            </div>
          </template>
        </DrawerEntityHeader>

        <DrawerActionsBar :actions="drawerActions" />

        <!-- Collegamenti del documento (genealogia), lo stesso BB degli altri
             sei domini. La fattura ci arriva ultima (2026-08-21) perche' era
             stata classificata «capolinea senza superficie propria»: aveva un
             drawer da luglio, e da ieri ha anche un discendente — l'arco N
             verso la nota di credito che la rettifica.
             ⭐ QUI SI LEGGE AL CONTRARIO degli altri: una fattura non ha archi
             in avanti nel grafo forward, quindi il valore e' la direzione
             INDIETRO — da quali commesse, ordini e preventivi viene. Misurato
             sulla fattura 835: sette tappe a monte, tre commesse distinte.
             ⚠️ E NON DUPLICA il blocco «documenti collegati» qui sotto, che
             legge `vendite.fatture_rettifiche`: quel ponte lo popola un task
             DOPO la numerazione, mentre il grafo ricostruisce il legame dalle
             RIGHE ed e' gia' pieno prima. Nella finestra fra emissione e
             numerazione questa barra e' l'unica delle due che parla. -->
        <DocumentoCollegamentiBar
          base-path="/vendite/fatture"
          :versione="dettaglio"
          :doc-id="fatturaId"
          @documento-chiuso="loadDettaglio"
          :readonly="isReadonly" />

        <!-- F5 · IL LEGAME DOCUMENTALE. «Questo accredito vale 12 € perché la
             riga 7 della fattura 2026/1234 valeva 12 €»: qui la prima metà,
             sulle righe la seconda. Nei DUE versi — una nota di credito dice
             cosa rettifica, una fattura dice da quali note è stata
             rettificata: chi guarda la fattura ha lo stesso diritto di
             saperlo.
             ⚠️ La proiezione la scrive il task di pipeline dopo la
             NUMERAZIONE: su un documento non ancora numerato è
             legittimamente vuota, e infatti qui non compare niente. -->
        <div
          v-for="b in blocchiCollegati"
          :key="b.verso"
          class="app-doc-campo app-mt-1"
        >
          <span class="app-doc-campo-label">{{ t(b.labelKey) }}</span>
          <span>
            <Tag
              v-for="d in b.documenti"
              :key="d.id"
              class="mr-05"
              severity="info"
              :value="documentoLabel(d)"
            />
          </span>
        </div>

        <!-- ⭐ LA SEGNALAZIONE IN TESTA. Se il documento porta un errore, lo
             dice QUI: chi apre una fattura in errore la apre proprio per
             quello, e farglielo cercare in fondo a una scheda e' il difetto
             che questo pannello esiste per togliere.
             ⚠️ Il pulsante e' interattivo dentro `app-drawer-content`, che
             diventa `.app-readonly` quando l'area e' in LETTURA: senza
             `app-escape` si vedrebbe e non si potrebbe cliccare (memoria
             `feedback_app_escape_pannelli_processo`). -->
        <Message v-if="erroreVivo" severity="error" :closable="false" class="app-mb-1">
          <!-- ⚠️ E' una riga del giornale come quelle della scheda Storia:
               si decodifica allo stesso modo, o lo stesso fatto avrebbe due
               nomi diversi a due centimetri di distanza. -->
          <div class="app-giornale-cosa">
            {{ labelOrCode(t, te, erroreVivo.etichetta_key, erroreVivo.cosa) }}
          </div>
          <Button
            class="app-escape"
            link
            size="small"
            :label="t('vendite.fatture.giornale_vai')"
            @click="apriStoria"
          />
        </Message>

        <!-- ⭐ DUE SCHEDE e non una pagina sola da scorrere (decisione di Tid,
             2026-08-24): il documento e la sua storia rispondono a due
             domande diverse, e chi cerca la seconda non deve attraversare la
             prima. Stessa forma del `LottoDrawer`. -->
        <Tabs v-model:value="tabAttiva" class="app-mt-1">
          <TabList>
            <Tab value="documento">{{ t('vendite.fatture.tab_documento') }}</Tab>
            <!-- Il CONTEGGIO nell'etichetta: dice se vale la pena entrare,
                 senza doverci entrare. -->
            <Tab value="storia">
              {{ t('vendite.fatture.tab_storia') }}
              <template v-if="giornaleStore.totalRecords"> ({{ giornaleStore.totalRecords }})</template>
            </Tab>
          </TabList>
          <TabPanels>
            <TabPanel value="documento">
        <!-- ⭐ IL SALDO PER PRIMO: «questa fattura e' stata pagata?» e' la
             domanda per cui si apre questo drawer, e sta sopra i dati
             anagrafici perche' e' quella che si fa entrando. La sezione la
             contribuisce pagamenti (core/estensioni.js): qui si offre il
             punto, non si conosce chi ci scrive. -->
        <PuntoEstensione
          :punto="PUNTI_ESTENSIONE.FATTURA_DRAWER_SEZIONI"
          :fattura-id="fatturaId"
        />

        <!-- Cliente e Documento affiancati (`form-grid-2col`, collassa a una
             colonna su schermi stretti): due schede corte, nessuna ragione di
             incolonnarle su un drawer WIDE. -->
        <div class="form-grid-2col">
          <div>
            <div class="app-drawer-section"><h4>{{ t('vendite.fatture.sez_cliente') }}</h4></div>
            <div v-for="c in campiCliente" :key="c.labelKey" class="app-doc-campo">
              <span class="app-doc-campo-label">{{ t(c.labelKey) }}</span>
              <span>{{ c.value || '—' }}</span>
            </div>
          </div>

          <div>
            <div class="app-drawer-section"><h4>{{ t('vendite.fatture.sez_documento') }}</h4></div>
            <div v-for="c in campiDocumento" :key="c.labelKey" class="app-doc-campo">
              <span class="app-doc-campo-label">{{ t(c.labelKey) }}</span>
              <span>{{ c.value || '—' }}</span>
            </div>
            <!-- Scadenza: la prossima rata PER DATA, col chip che apre il
                 piano completo. Non è uno stato di pagamento — il modello non
                 sa quale rata sia stata incassata (vedi useScadenzeSintesi). -->
            <div class="app-doc-campo">
              <span class="app-doc-campo-label">
                {{ t('vendite.fatture.prossima_rata') }}
              </span>
              <ScadenzeSintesi :scadenze="scadenze" />
            </div>
          </div>
        </div>

        <!-- Righe: la lista `vendite.fattura_righe`. Il padre di un kit porta
             i suoi componenti esposti (`componenti`), che si leggono nella
             riga espandibile: paginazione e ordinamento spostano il kit
             intero. La chiave e' `riga_key` (il padre non ha un id). -->
        <div class="app-drawer-section app-drawer-section--senza-bordo">
          <h4>{{ t('vendite.fatture.sez_righe') }}</h4>
        </div>
        <Message v-if="righeStore.erroreCaricamento" severity="warn" :closable="false" size="small">
          {{ t('common.righe_non_lette') }}
        </Message>
        <DrawerTabLista
          ref="righeListaRef"
          codice="vendite.fattura_righe"
          :store="righeStore"
          :emittente-esplicito="fattura.emittente_fiscale_pk ?? null"
          :rows="righeStore.items"
          :total="righeStore.totalRecords"
          :loading="righeStore.loading"
          :paginator-options="righePaginator"
          :page="righePage"
          :sort-field="righePaginator.sortField"
          :sort-order="righePaginator.sortOrder"
          :page-actions="righeActions"
          :dirty="righeDirty"
          :perimetro-bloccato="righePerimetroBloccato"
          data-key="riga_key"
          @page="onRighePage"
          @sort="onRigheSort"
          @config-loaded="onRigheConfigLoaded"
        >
          <template #filtri-sempre>
            <InputText v-model="righeSearch" class="app-filter-w-lg" :placeholder="t('common.search')" />
          </template>
          <!-- La riga gemella di una nota di credito: il documento parlante
               e la riga. E' cio' che rende verificabile l'importo della
               rettifica senza aprire l'altro documento. -->
          <template #cell-riga_rettificata="{ data }">
            <span v-if="data.riga_rettificata_id">
              {{ t('vendite.fatture.rettifica_riga_valore', {
                   numero: data.riga_rettificata_documento ?? '—',
                   riga: data.riga_rettificata_nr ?? '—',
                 }) }}
            </span>
            <span v-else>—</span>
          </template>
          <template #row-expansion="{ data }">
            <ul v-if="data.componenti?.length" class="app-fattura-componenti">
              <li v-for="c in data.componenti" :key="c.fatture_righe_id">
                <span v-if="c.articolo_codice" class="app-fattura-articolo">{{ c.articolo_codice }}</span>
                {{ c.descrizione || '—' }}
                <!-- Quantita' al massimo alla precisione della colonna (6). -->
                <span class="app-text-muted">
                  · {{ formatQuantita(c.quantita, { placeholder: '—' }) }}
                  {{ c.uom_codice || '' }}
                </span>
                <!-- Il VALORIZZATO porta prezzo, sconto e importo suoi, fuori
                     dal totale del padre (dal 2026-10-01): si leggono qui,
                     sotto il kit a cui resta legato. Il DESCRITTIVO li ha
                     NULL — il suo valore e' nel padre — e non mostra niente:
                     un «—» farebbe leggere «a costo zero». Per lo stesso
                     motivo un padre con importo vuoto e' un kit senza resto
                     (tutti valorizzati), non un errore; e un padre con
                     quantita' e prezzo vuoti e' un kit i cui componenti non
                     dicono lo stesso numero di kit (nota di credito
                     parziale, dal 2026-10-02): ha il suo importo e basta. -->
                <span v-if="c.importo_riga != null" class="app-fattura-componente-importo">
                  × {{ formatCurrency(c.prezzo_unitario, { placeholder: '—' }) }}
                  <template v-if="Number(c.sconto_percentuale) > 0">
                    − {{ formatNumber(c.sconto_percentuale, { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }}%
                  </template>
                  = <strong>{{ formatCurrency(c.importo_riga) }}</strong>
                </span>
              </li>
            </ul>
          </template>
          <template #empty>
            <span v-if="!righeStore.erroreCaricamento">{{ t('vendite.fatture.nessuna_riga') }}</span>
          </template>
        </DrawerTabLista>

        <!-- Riepilogo IVA: BB condiviso con preventivi/ordini/DDT (titolo,
             label esenti con natura, footer di quadratura, totale documento).
             Lettura pura da fatture_riepiloghi_iva: nessun ricalcolo qui. -->
        <RiepilogoIvaTable :items="riepilogoIva" show-subtitle />

        <!-- Chiusura del documento: bollo/arrotondamento se ci sono, poi i
             due totali. `totale_doc` e `totale_a_pagare` entrambi perché
             divergono quando ci sono fondi/acconti applicati, e mostrarne uno
             solo lascia l'operatore senza spiegazione. Placeholder '—' sugli
             importi assenti: NULL non è zero, e su un documento fiscale uno
             zero inventato è un'informazione falsa. -->
        <div class="app-doc-totali">
          <div
            v-for="c in campiTotali"
            :key="c.labelKey"
            class="app-doc-totali-riga"
            :class="{ 'app-doc-totali-riga--forte': c.forte }"
          >
            <span class="app-doc-totali-label">{{ t(c.labelKey) }}</span>
            <span class="app-doc-totali-value">
              {{ formatCurrency(c.importo, { placeholder: '—' }) }}
            </span>
          </div>
        </div>
            </TabPanel>
            <TabPanel value="storia">

        <!-- ⭐ LA STORIA DEL DOCUMENTO — «cosa è successo a questa fattura».
             La lista a catalogo `vendite.giornale` sulla sola fattura
             (sorgente `script.vw_giornale_entita`; per la fattura oggi
             risponde `fatture_log`), nel tab condiviso col `LottoDrawer`.
             ⛔ Non è il pannello «Collegamenti»: quello dice con quali ALTRI
             documenti la fattura è legata, questo cosa le è successo.
             ⭐ L'emittente del documento scioglie il cancello di perimetro
             della lista: chi vede più emittenti non deve sceglierne uno per
             leggere la storia di un documento che lo dichiara. -->
        <GiornaleEntitaTab
          :store="giornaleStore"
          :entita-id="fatturaId"
          :emittente-soggetto-ruolo-id="fattura.emittente_soggetto_ruolo_id"
        />
            </TabPanel>
          </TabPanels>
        </Tabs>

      </template>
    </template>

    <ExportDialog
      v-model:visible="righeExportVisible"
      :loading="righeExportLoading"
      @export="onRigheExportConfirm"
    />

    <!-- Archivio PDF generati + allegati (motore documentale, sorgente
         FATTURA). Niente `allow-allegati` hardcoded: l'append è una capability
         governata dagli stati (`pdf_allow_allegati`), non una decisione del
         drawer — stessa porta del `LottoDrawer`. -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialog"
      :sorgente-code="SORGENTE_CODES.FATTURA"
      :sorgente-id="fatturaId"
      :emittente-fiscale-id="fattura?.emittente_fiscale_pk ?? null"
      :title="t('vendite.fatture.documenti_titolo', { numero: numeroDisplay })"
    />

    <!-- Note della fattura (BB partizionato). Il readonly di oggetto arriva
         al NoteDrawer via provide/inject (useReadonlyMode sopra). -->
    <FatturaNoteDrawer
      v-model:visible="noteDrawer"
      :fattura-id="fatturaId"
      :righe="righe"
      @saved="contatoreNote.aggiorna"
    />
  </AppDrawer>
</template>

<style scoped>
/* Solo decorazione della tabella righe: il layout della scheda (campi
   label/valore, totali di chiusura) vive nelle classi globali `app-doc-*`. */
.app-fattura-articolo {
  color: var(--app-text-muted);
  margin-right: 0.4rem;
}
.app-fattura-componenti {
  margin: 0;
  padding-left: 1.2rem;
}
.app-fattura-componente-importo {
  margin-left: 0.4rem;
}
</style>
