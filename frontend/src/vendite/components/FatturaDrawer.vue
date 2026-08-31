<script setup>
// Scopo: Drawer di CONSULTAZIONE della fattura — il documento a video, nello
//        stesso formato degli altri documenti vendite: testata (cliente,
//        emittente, pagamento, totali) in alto, righe al centro, riepilogo IVA
//        in fondo.
//        Generico e richiamabile da più punti: dal kebab delle righe fatture
//        del `LottoDrawer` e dal registry `documentoDrawers` (tappe Passaggi,
//        drill-down cruscotti); domani ricerca universale, portale.
//        SOLA LETTURA per costruzione: la fattura è prodotta dalla pipeline e
//        oltre la soglia di congelamento le righe sono congelate a DB
//        (`trgfn_fattura_satellite_guard_congelamento`; la soglia è un dato,
//        `config.stati_doc_fiscale.congela_fiscale`). Le azioni di processo
//        (emissione, numerazione, ristampa massiva) restano nel cockpit.
//        I dati arrivano dagli STESSI lettori che alimentano il contesto del
//        PDF: ciò che si vede qui è ciò che finisce nel documento fiscale.
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
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import SaldoPanel from '../../core/components/SaldoPanel.vue'
import { LIVELLO } from '../../core/composables/useSaldi'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import RiepilogoIvaTable from '../../core/components/RiepilogoIvaTable.vue'
import ScadenzeSintesi from '../../core/components/ScadenzeSintesi.vue'
import PdfDocumentiSorgenteDialog from '../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import DocumentoCollegamentiBar from '../_shared/lineage/DocumentoCollegamentiBar.vue'
import FatturaNoteDrawer from './FatturaNoteDrawer.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useDocumentiPerSorgenteStore } from '../../documenti/stores/documentiPerSorgente'
import { SORGENTE_CODES } from '../../documenti/constants'
import {
  DRAWER_WIDTH,
  MANAGE_ICONS,
  NATURA_DOC,
  READONLY_DOMAINS,
  READONLY_MODELS,
} from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { formatCurrency, formatIvaLabel, formatNumber } from '../../core/utils/format'
import {
  gravitaGiornaleSeverity,
  naturaDocSeverity,
  statoDocFiscaleSeverity,
} from '../../core/utils/severity'
import { downloadBlob } from '../../core/utils/download'
import { getFatturaDettaglio, getFatturaGiornale } from '../api/fatture'

const props = defineProps({
  visible: { type: Boolean, default: false },
  fatturaId: { type: [Number, null], default: null },
})

const emit = defineEmits(['update:visible'])
const { t, te } = useI18n()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
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
const righe = computed(() => dettaglio.value?.righe ?? [])
const riepilogoIva = computed(() => dettaglio.value?.riepilogo_iva ?? [])
const scadenze = computed(() => dettaglio.value?.scadenze ?? [])

// Counter note del badge. Ref e non computed sul dettaglio perché ha DUE
// fonti: il payload BE all'apertura (`contatori.note`, nessun round-trip
// aggiuntivo) e il sub-drawer note dopo ogni create/update/delete — che il
// totale aggiornato ce l'ha già e lo passa con `@saved`. Il conteggio BE usa
// lo stesso perimetro della lista note, quindi i due valori non divergono.
const noteCount = ref(0)

// ⭐ LA STORIA DEL DOCUMENTO (Passo A del filone osservabilità). Fetch SUA,
// separata dal dettaglio: è un pannello di consultazione e non deve rallentare
// l'apertura del documento — se fallisce, il documento si vede lo stesso.
const giornale = ref([])
const giornaleTotale = ref(0)
const giornaleCaricato = ref(false)
// Quante righe il filtro nasconde: le segnalazioni RITIRATE, cioè quelle di
// un tentativo poi rifatto. ⛔ Il numero non è un di più — senza, «nessun
// evento» e «tre eventi, tutti superati» si leggono uguali.
const giornaleRitirate = ref(0)
// Quante righe stanno in una pagina. ⚠️ Non c'è paginatore: su un documento gli
// eventi sono pochi (misurato: 3 sul caso più mosso). Se un giorno saranno di
// più, la riga «mostrati N di M» qui sotto lo dice invece di tacerlo.
const GIORNALE_PAGE_SIZE = 50
// ⭐ L'ORDINE DI DEFAULT È LA GRAVITÀ (Tid, 2026-08-24, dopo la validazione
// in-app): davanti a un documento la prima domanda è «c'è qualcosa che non
// va?», non «cosa è successo per primo». La cronologia resta a un clic.
// ⚠️ `sortOrder` è la convenzione PrimeVue: -1 = DESC, 1 = ASC.
const giornaleSortField = ref('gravita')
const giornaleSortOrder = ref(-1)

// ⭐ L'ERRORE IN EVIDENZA. Un documento che non si è potuto numerare deve dirlo
// in testa, non in fondo alla terza schermata: chi apre la fattura la apre
// PROPRIO perché qualcosa non è andato.
// ⚠️ Si prende il PIÙ RECENTE, e la lista arriva già ordinata dal più nuovo:
// su un documento ripreso più volte gli errori si ripetono uguali, e mostrarli
// tutti direbbe che è successo N volte invece di una.
// ⭐ E non c'è più niente da dedurre: dal changeSet `20260824-14` la vista porta
// `disabilitato`, e le ritirate sono già state tolte dal SERVER — quindi qui
// dentro un ERROR è vivo per costruzione, non per inferenza sull'ordine.
const erroreVivo = computed(() => giornale.value.find((r) => r.gravita === 'ERROR') ?? null)

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

// Natura del documento (B5): si dichiara solo quando NON è una fattura — vedi
// il commento nel template. `FATTURA` è il default della colonna a DB, quindi
// una testata senza natura è una fattura, non un dato mancante.
const naturaNonOrdinaria = computed(() => {
  const codice = fattura.value?.natura_doc_codice_interno
  return !!codice && codice !== NATURA_DOC.FATTURA
})

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
const haLegameRiga = computed(() => righe.value.some((r) => r.riga_rettificata_id))

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
    noteCount.value = Number(dettaglio.value?.contatori?.note ?? 0)
  } finally {
    if (fv.isCurrent(my)) loading.value = false
  }
}

// Scopo: riordina la storia RICHIEDENDOLA AL SERVER.
// ⛔ Il `lazy` della tabella non è un dettaglio di resa: senza, PrimeVue
//    ordinerebbe l'array già caricato — cioè la sola pagina — e con più righe
//    del tetto «il più grave» diventerebbe «il più grave fra i primi 50». È il
//    difetto silenzioso di sempre: a video un elenco ordinato male e uno
//    ordinato bene si somigliano.
function onGiornaleSort(event) {
  giornaleSortField.value = event.sortField || 'gravita'
  giornaleSortOrder.value = event.sortOrder ?? -1
  loadGiornale()
}

// Scopo: carica la storia del documento. ⚠️ Silenziosa e best-effort: un
//        giornale che non arriva non deve impedire di leggere la fattura, e il
//        pannello lo dice da sé restando sullo stato «non caricato» invece di
//        affermare «non è successo niente».
// ⛔ `giornaleCaricato` non è un dettaglio: senza, un elenco vuoto perché la
//    fetch è fallita e uno vuoto perché non è successo nulla si leggono uguali.
async function loadGiornale() {
  if (!props.fatturaId) return
  const my = fv.tag()
  try {
    const res = await execute(
      () =>
        getFatturaGiornale(props.fatturaId, {
          pageSize: GIORNALE_PAGE_SIZE,
          sortBy: giornaleSortField.value,
          sortDir: giornaleSortOrder.value === 1 ? 'asc' : 'desc',
        }),
      { silent: true },
    )
    if (!fv.isCurrent(my) || res == null) return
    // ⚠️ `execute` restituisce il payload GIA' SCARTATO dall'envelope
    // (`response.data.data`), non la response axios: qui si legge `res.results`,
    // non `res.data.data.results`. ⛔ Difetto pagato il 2026-08-24: con
    // l'unwrap di troppo l'elenco restava vuoto E `giornaleCaricato` andava
    // comunque a `true` — cioe' il pannello affermava «nessun evento
    // registrato» su una fattura che ne aveva tre. Il vuoto positivo che
    // questo flag esiste per impedire, prodotto dal flag stesso.
    // 📌 `loadDettaglio` qui sopra legge `res.data?.data` perche' passa da
    // `loadDetailOrClose`, che la response axios la restituisce intera: i due
    // non si copiano a vicenda.
    giornale.value = res.results ?? []
    giornaleTotale.value = Number(res.count ?? 0)
    giornaleRitirate.value = Number(res.ritirate_count ?? 0)
    giornaleCaricato.value = true
  } catch {
    // Volutamente muto: vedi sopra.
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
    noteCount.value = 0
    giornale.value = []
    giornaleTotale.value = 0
    giornaleCaricato.value = false
    giornaleRitirate.value = 0
    tabAttiva.value = 'documento'
    await loadDettaglio()
    // Dopo il dettaglio, non insieme: se la fattura non è accessibile il
    // drawer si è già chiuso, e questa non deve partire su un id negato.
    if (dettaglio.value) await loadGiornale()
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

// Scopo: sconto riga — percentuale formattata it-IT solo se > 0, '—'
//        altrimenti. NB: dal BE i numeric arrivano come STRINGA ("0.00" è
//        truthy): il confronto va fatto sul numero, mai sulla stringa.
function scontoLabel(row) {
  const v = Number(row.sconto_percentuale)
  if (!Number.isFinite(v) || v === 0) return '—'
  return `${formatNumber(row.sconto_percentuale, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}%`
}

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
  {
    key: 'note',
    kind: 'manage',
    label: t('vendite.fatture.azione_note'),
    icon: MANAGE_ICONS.NOTE,
    // Badge solo se ci sono note: `null` = nessun badge (il BB nasconde la
    // pillola su null/''), 0 stamperebbe uno zero che non informa.
    badge: noteCount.value > 0 ? noteCount.value : null,
    disabled: !props.fatturaId,
    command: () => { noteDrawer.value = true },
  },
])

// Scopo: allinea il badge al totale note comunicato dal sub-drawer dopo un
//        create/update/delete. Nessuna rilettura del dettaglio: ricaricarlo
//        mentre il drawer note è aperto sopra rigenererebbe `righe`, cioè le
//        opzioni del select riga che il figlio sta usando.
function onNoteSaved(total) {
  if (typeof total === 'number' && Number.isFinite(total)) noteCount.value = total
}

</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    @update:visible="(v) => { if (!v) onClose() }"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :title="t('vendite.fatture.drawer_titolo')" :icon="NAV_ICONS.FATTURE" />
    </template>

    <!-- Livello oggetto BLOCCATO: pannello sostitutivo (safety net — il BE
         risponde comunque 403 sul dettaglio). -->
    <AccessoBloccatoPanel v-if="isBlocked" />

    <div v-else class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">
        <div v-if="loading && !fattura" class="app-loading">
          <i class="pi pi-spin pi-spinner" />
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
                     fattura. ⚠️ Mostrarla sempre («Fattura» su una fattura)
                     aggiungerebbe rumore al caso normale e toglierebbe forza
                     al caso che conta. ⛔ E mai `danger`: una nota di credito
                     non è un errore, è un documento di segno opposto — il
                     totale negativo è il suo contenuto, non un difetto. -->
                <Tag
                  v-if="naturaNonOrdinaria"
                  :value="fattura.natura_doc_descrizione || fattura.natura_doc_codice_interno"
                  :severity="naturaDocSeverity(fattura.natura_doc_codice_interno)"
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
            :doc-id="fatturaId"
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
                class="app-mr-1"
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
                <template v-if="giornaleTotale"> ({{ giornaleTotale }})</template>
              </Tab>
            </TabList>
            <TabPanels>
              <TabPanel value="documento">
          <!-- ⭐ IL SALDO PER PRIMO: «questa fattura e' stata pagata?» e' la
               domanda per cui si apre questo drawer, e sta sopra i dati
               anagrafici perche' e' quella che si fa entrando.
               ⛔ DUE numeri e non tre (Q-6): l'«incassato» risponde a una
               domanda di tesoreria, non a «questa fattura e' a posto?». Il
               pannello lo sa mostrare — e' la stessa base — ma questa
               schermata non lo accende.
               ⚠️ Il pannello legge da se' e si rilegge al cambio di fattura:
               il drawer e' un'istanza sola riusata cambiando `fatturaId`. -->
          <div class="app-drawer-section"><h4>{{ t('vendite.fatture.sez_saldo') }}</h4></div>
          <SaldoPanel
            :livello="LIVELLO.DOCUMENTO"
            :riferimento-id="fatturaId"
            :mostra="['residuo', 'in_lavorazione']"
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

          <!-- Righe. Fonte: vw_fattura_righe_esposte (kit già risolti). -->
          <div class="app-drawer-section"><h4>{{ t('vendite.fatture.sez_righe') }}</h4></div>
          <!-- Niente `data-key`: le righe KIT_PADRE sono sintetiche della
               vista e hanno `id` NULL — usarlo come chiave produrrebbe
               duplicati. Si lascia il fallback per indice di PrimeVue. -->
          <DataTable
            :value="righe"
            class="app-datatable app-datatable--inner"
            striped-rows
            size="small"
          >
            <Column field="riga_nr" :header="t('vendite.fatture.col_riga')" style="width: 60px;" />
            <Column field="descrizione" :header="t('vendite.fatture.col_descrizione')">
              <template #body="{ data }">
                <!-- `livello` è il contratto della vista: 0 = riga di primo
                     livello (NORMALE o KIT_PADRE), 1 = componente di kit, che
                     va rientrato sotto il padre. -->
                <span :class="{ 'app-fattura-componente': data.livello === 1 }">
                  <span v-if="data.articolo_codice" class="app-fattura-articolo">
                    {{ data.articolo_codice }}
                  </span>
                  {{ data.descrizione || data.articolo_descrizione || '—' }}
                </span>
              </template>
            </Column>
            <Column field="quantita" :header="t('vendite.fatture.col_qta')" style="width: 80px;">
              <template #body="{ data }">
                <!-- Quantità NULL sui KIT_PADRE (la vista non le somma): '—',
                     mai un finto zero. max 6 decimali = precisione colonna. -->
                {{ formatNumber(data.quantita, { placeholder: '—', minimumFractionDigits: 0, maximumFractionDigits: 6 }) }}
              </template>
            </Column>
            <Column field="uom_codice" :header="t('vendite.fatture.col_uom')" style="width: 70px;" />
            <Column field="prezzo_unitario" :header="t('vendite.fatture.col_prezzo')" style="width: 110px;">
              <template #body="{ data }">
                {{ formatCurrency(data.prezzo_unitario, { placeholder: '—', minimumFractionDigits: 2, maximumFractionDigits: 6 }) }}
              </template>
            </Column>
            <Column field="sconto_percentuale" :header="t('vendite.fatture.col_sconto')" style="width: 80px;">
              <template #body="{ data }">{{ scontoLabel(data) }}</template>
            </Column>
            <Column field="iva_codice" :header="t('vendite.fatture.col_iva')" style="width: 80px;">
              <template #body="{ data }">
                <!-- BB formatIvaLabel: aliquota > 0 → "22%", esente → codice
                     IVA parlante; fallback natura di riga (snapshot). -->
                {{ formatIvaLabel(data, { placeholder: data.iva_natura || '—' }) }}
              </template>
            </Column>
            <!-- La riga gemella: è ciò che rende verificabile l'importo della
                 rettifica senza aprire l'altro documento. Colonna presente solo
                 se almeno una riga ha il legame — su una fattura ordinaria
                 sarebbe una colonna di trattini. -->
            <Column
              v-if="haLegameRiga"
              field="riga_rettificata_id"
              :header="t('vendite.fatture.col_rettifica_riga')"
              style="width: 130px;"
            >
              <template #body="{ data }">
                <span v-if="data.riga_rettificata_id">
                  {{ t('vendite.fatture.rettifica_riga_valore', {
                       numero: data.riga_rettificata_fattura_numero ?? '—',
                       riga: data.riga_rettificata_nr ?? '—',
                     }) }}
                </span>
                <span v-else>—</span>
              </template>
            </Column>
            <Column field="importo_riga" :header="t('vendite.fatture.col_imponibile')" style="width: 110px;">
              <template #body="{ data }">
                {{ formatCurrency(data.importo_riga, { placeholder: '—' }) }}
              </template>
            </Column>
            <template #empty>
              <div class="app-empty-state">
                <i class="pi pi-inbox" /><p>{{ t('vendite.fatture.nessuna_riga') }}</p>
              </div>
            </template>
          </DataTable>

          <!-- Riepilogo IVA: BB condiviso con preventivi/ordini/DDT (titolo,
               label esenti con natura, footer di quadratura, totale documento).
               Lettura pura da fatture_riepiloghi_iva: nessun ricalcolo qui. -->
          <RiepilogoIvaTable :items="riepilogoIva" show-esigibilita show-subtitle />

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
               Sorgente: `script.vw_giornale_entita`, la vista che cuce i
               registri di evento; per la fattura oggi risponde `fatture_log`.
               ⛔ Non è il pannello «Collegamenti»: quello dice con quali ALTRI
               documenti la fattura è legata, questo cosa le è successo.
               ⚠️ NON interattivo di proposito: sta dentro `app-drawer-content`,
               che diventa `.app-readonly` quando l'area è in LETTURA — un
               pannello con controlli qui dentro sarebbe visibile e non
               cliccabile (memoria `feedback_app_escape_pannelli_processo`).
               Finché è sola lettura non serve `app-escape`. -->
          <div class="app-drawer-section"><h4>{{ t('vendite.fatture.sez_giornale') }}</h4></div>
          <DataTable
            v-if="giornale.length"
            :value="giornale"
            data-key="riga_key"
            class="app-datatable app-datatable--inner"
            size="small"
            lazy
            :sort-field="giornaleSortField"
            :sort-order="giornaleSortOrder"
            @sort="onGiornaleSort"
          >
            <Column
              field="quando"
              sortable
              :header="t('vendite.fatture.col_giornale_quando')"
              style="width: 150px;"
            >
              <template #body="{ data }">{{ displayTimestamp(data.quando) }}</template>
            </Column>
            <Column
              field="gravita"
              sortable
              :header="t('vendite.fatture.col_giornale_gravita')"
              style="width: 110px;"
            >
              <template #body="{ data }">
                <!-- ⚠️ `gravita` può essere NULL, e la vista lo dichiara come il
                     segnale che «un vincolo si è allargato e la mappa è rimasta
                     indietro»: si mostra il buco, non lo si nasconde. -->
                <Tag
                  :value="data.gravita ?? '—'"
                  :severity="gravitaGiornaleSeverity(data.gravita)"
                />
              </template>
            </Column>
            <Column field="cosa" :header="t('vendite.fatture.col_giornale_cosa')">
              <!-- ⭐ Il FATTO, tradotto quando il catalogo lo dichiara — stessa
                   decodifica della scheda Storia del lotto, stesso ripiego
                   fail-visible sul codice grezzo. -->
              <template #body="{ data }">
                <span class="app-giornale-cosa">
                  {{ labelOrCode(t, te, data.etichetta_key, data.cosa) }}
                </span>
              </template>
            </Column>
            <Column :header="t('vendite.fatture.col_giornale_chi')" style="width: 130px;">
              <template #body="{ data }">{{ data.user_insert ?? '—' }}</template>
            </Column>
          </DataTable>

          <!-- ⛔ I due vuoti NON sono lo stesso vuoto: «non è successo niente»
               è un'informazione, «non sono riuscito a chiederlo» no. -->
          <!-- ⛔ TRE vuoti diversi, e vanno detti diversi: «non è successo
               niente», «è successo tutto ed è stato superato», «non sono
               riuscito a chiederlo». Il secondo su un elenco filtrato è il
               caso in cui la distinzione conta di più. -->
          <div v-else class="app-empty-state">
            <i :class="giornaleCaricato ? 'pi pi-check-circle' : 'pi pi-inbox'" />
            <p v-if="!giornaleCaricato">{{ t('vendite.fatture.giornale_non_caricato') }}</p>
            <p v-else-if="giornaleRitirate > 0">
              {{ t('vendite.fatture.giornale_solo_ritirate', { n: giornaleRitirate }) }}
            </p>
            <p v-else>{{ t('vendite.fatture.giornale_vuoto') }}</p>
          </div>

          <!-- Il conto di ciò che il filtro toglie. Compare solo quando c'è
               qualcosa da dichiarare E qualcosa da mostrare: sull'elenco vuoto
               lo dice già il messaggio qui sopra, e ripeterlo sarebbe rumore. -->
          <p
            v-if="giornaleRitirate > 0 && giornale.length"
            class="app-drawer-header-muted"
          >
            {{ t('vendite.fatture.giornale_ritirate', { n: giornaleRitirate }) }}
          </p>

          <!-- Il conto, quando la pagina non basta: un elenco troncato che non
               lo dice si legge come completo. -->
          <p v-if="giornaleTotale > giornale.length" class="app-drawer-header-muted">
            {{ t('vendite.fatture.giornale_parziale', {
              n: giornale.length, tot: giornaleTotale,
            }) }}
          </p>
              </TabPanel>
            </TabPanels>
          </Tabs>

        </template>
      </template>

      <FormFooter close-only @cancel="onClose" />
    </div>

    <!-- Archivio PDF generati + allegati (motore documentale, sorgente
         FATTURA). Niente `allow-allegati` hardcoded: l'append è una capability
         governata dagli stati (`pdf_allow_allegati`), non una decisione del
         drawer — stessa porta del `LottoDrawer`. -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialog"
      :sorgente-code="SORGENTE_CODES.FATTURA"
      :sorgente-id="fatturaId"
      :title="t('vendite.fatture.documenti_titolo', { numero: numeroDisplay })"
    />

    <!-- Note della fattura (BB partizionato). Il readonly di oggetto arriva
         al NoteDrawer via provide/inject (useReadonlyMode sopra). -->
    <FatturaNoteDrawer
      v-model:visible="noteDrawer"
      :fattura-id="fatturaId"
      :righe="righe"
      @saved="onNoteSaved"
    />
  </Drawer>
</template>

<style scoped>
/* Solo decorazione della tabella righe: il layout della scheda (campi
   label/valore, totali di chiusura) vive nelle classi globali `app-doc-*`. */
.app-fattura-articolo {
  color: var(--app-text-muted);
  margin-right: 0.4rem;
}
.app-fattura-componente {
  padding-left: 1.2rem;
}
</style>
