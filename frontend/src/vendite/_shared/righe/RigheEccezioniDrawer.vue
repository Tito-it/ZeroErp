<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Building block — il sub-drawer delle RIGHE di un documento con
//        listino ed eccezioni (contratto, offerta commerciale): la lista
//        configurabile delle righe operative (righe del listino con l'overlay
//        OVERRIDE/ESCLUSIONE, piu' le AGGIUNTA), i verbi di riga del DB, e il
//        form inline di OVERRIDE e AGGIUNTA con componenti BoM e flusso L2.
//        Pattern master-detail inline: lista sopra, form sotto.
//
// ⭐ REGOLA DEL 2 (2026-10-05, ok Tid, brief-db-righe-esclusione-solo-non-si-
//    vende §8.1). Nato dal corpo vivo di `ContrattoRigheDrawer`: il giorno in
//    cui l'offerta ha avuto la sua lista coi verbi del DB
//    (`vendite.offerta_righe`, 106, sulla stessa funzione comune
//    `vendite.fn_documento_righe_preview`), il suo drawer sarebbe stato la
//    seconda copia della stessa logica. Prima di quel giorno l'offerta aveva
//    una `DataTable` in memoria sulla tabella cruda, il tipo di eccezione
//    scelto in una tendina, l'esclusione nel form e il toggle «attivo»: tutte
//    regole decise qui invece che dal DB, e gia' divergenti dal contratto.
//    `ContrattoRigheDrawer` e `OffertaRigheDrawer` sono involucri: passano lo
//    store della lista, le scritture, le API dei componenti, l'intestazione e
//    gli avvisi propri (il contesto pricing e' del solo contratto).
//
// ⭐ I VERBI DELLA RIGA LI DICE IL DB (colonna `azioni`, capability di riga):
//    il drawer li RENDE, non li decide. DA_LISTINO → SOVRASCRIVI_PREZZO (click),
//    ESCLUDI e ADERISCI; OVERRIDE → MODIFICA (click) e RIPRISTINA_LISTINO;
//    ESCLUSIONE → RIPRISTINA_ARTICOLO; AGGIUNTA → MODIFICA (click) e RIMUOVI;
//    ADESIONE → MODIFICA (click) e RIMUOVI_ADESIONE. «Escludi»
//    spento porta il motivo (`escludi_blocco_codice`, lo stesso predicato del
//    guard). Il tipo di eccezione non si sceglie: lo da' il gesto che apre il
//    form (riga del listino → OVERRIDE o ADESIONE, «Nuovo» → AGGIUNTA), e
//    l'ESCLUSIONE non passa dal form (one-click, vuota: il DB la rifiuta con
//    un dato).
//
// ⭐ I TESTI, DUE SEDI. Il VOCABOLARIO delle righe (origini, tipi, fonti,
//    erogazioni, motivi di «Escludi», etichette dei campi) e' lo stesso sui due
//    documenti e sta in `vendite.contratti.*`, dove nacque — come i codici
//    errore del DB che dicono «CONTRATTO» per storia e valgono per l'offerta.
//    I soli testi che NOMINANO IL DOCUMENTO («Rimuovi dal contratto») passano
//    da `i18nDocumento` (`vendite.contratti` / `vendite.offerte`): sono le
//    chiavi passate a `td(...)`, e ogni dominio le scrive tutte. ⚠️ La chiave
//    e' costruita, quindi `check_i18n_keys` non la vede: le presidia
//    `RigheEccezioniDrawer.spec.js`, che le legge da questo sorgente.
//
// ⭐ COME SI EROGA UNA RIGA LO DICE IL DB, DALL'ARTICOLO (brief-db-offerta-
//    emissione-ed-erogazione B-R4, 2026-10-07): le erogazioni e le fonti che il
//    form propone sono le combinazioni di `vendite.fn_documento_riga_erogazioni`
//    (prop `erogazioniArticolo`), la stessa sede che il DB legge per l'eredita'
//    e per il guard del perimetro. In creazione il form preseleziona la
//    combinazione di default, cioe' quella che il DB scriverebbe. ⛔ Fino a quel
//    giorno la matrice erogazione × fonte era ricopiata qui
//    (`fontiQuantitaErogazione.js`, ritirato) e non sapeva niente di tipologia
//    ne' di utility: su una utility BASE proponeva «Da letture utility».
import { ref, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../../core/composables/useDrawerFormPreserve'
import { useDrawerTabLista } from '../../../core/composables/useDrawerTabLista'
import { useFormInline } from '../../../core/composables/useFormInline'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useFetchVersion } from '../../../core/composables/useFetchVersion'
import { useInjectReadonly } from '../../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../../stores/auth'
import { useLimitiPricing } from '../../composables/useLimitiPricing'
import {
  AZIONE_RIGA_CONTRATTO, FONTE_QUANTITA_ATTESA, PRICING_ACTIONS, TIPO_ECCEZIONE, TIPO_EROGAZIONE,
} from '../../constants'
import PeriodicitaSelect from '../canoni/PeriodicitaSelect.vue'
import { opzioniGenerazioneCanone } from '../canoni/campiCanone'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../../core/constants'
import { useArticoloUomOptions } from '../../../catalogo/composables/useArticoloUomOptions'
import {
  combinazioneDefault, fonteDopoCambioErogazione, opzioniErogazione, opzioniFonte,
} from './erogazioniRiga'
import AppDrawer from '../../../core/components/AppDrawer.vue'
import DrawerTabLista from '../../../core/components/DrawerTabLista.vue'
import ExportDialog from '../../../core/components/ExportDialog.vue'
import FormFooter from '../../../core/components/FormFooter.vue'
import ArticoloLookup from '../../../catalogo/components/ArticoloLookup.vue'
import { rowComponenti, hasBundleComponenti } from '../componenti/rowComponenti'
import ComponentiCreateActionsPanel from '../componenti/ComponentiCreateActionsPanel.vue'
import ComponentiDialog from '../componenti/ComponentiDialog.vue'
import { useComponentiDialog } from '../componenti/useComponentiDialog'
import ComponentiPanel from '../componenti/ComponentiPanel.vue'
import L2ErrorBanner from '../pricing/L2ErrorBanner.vue'
import { useL2SaveFlow } from '../pricing/useL2SaveFlow'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'

// Il vocabolario delle righe: una sede per i due documenti (vedi testata).
const VOC = 'vendite.contratti'

const props = defineProps({
  visible: Boolean,
  documentoId: { type: Number, required: true },
  // Il documento, come lo nomina `config.tipi_entita` (`OFFERTA_COMMERCIALE`,
  // `CONTRATTO`): lo chiede il picker degli articoli, che giudica la riga con
  // la check dei guard di quel documento.
  documento: { type: String, required: true },
  // L'emittente del documento (PK di `anagrafiche.emittenti_fiscali`): il
  // lasciapassare del cancello di perimetro della lista. Finche' manca la
  // lista e' in attesa, non vuota (padre composto di `useListaStoreCore`).
  emittenteFiscaleId: { type: Number, default: null },
  // Il codice della lista configurabile (`vendite.contratto_righe`, 103;
  // `vendite.offerta_righe`, 106).
  listaCodice: { type: String, required: true },
  // Lo store della lista: UNA istanza per drawer (`storePerIstanza` +
  // `createRigheListaStore`), creata dall'involucro.
  righeStore: { type: Object, required: true },
  // Le scritture delle righe del dominio, gia' scartate dalla risposta axios
  // (azioni dello store del documento):
  //   { crea(docId, payload), aggiorna(docId, rigaId, payload), elimina(docId, rigaId) }
  scritture: { type: Object, required: true },
  // L'export della lista: (docId, params) → il file.
  esportaRighe: { type: Function, required: true },
  // Le API dei componenti BoM della riga: { anteprima, elenco, aggiorna, elimina }.
  apiComponenti: { type: Object, required: true },
  // Come si puo' erogare un articolo su una riga del documento:
  // (docId, articoloId) → la risposta axios, envelope `data.results` con le
  // combinazioni { tipo_erogazione, fonte_quantita_attesa, e_default, … }, il
  // default in testa (`GET …/righe/erogazioni/`).
  erogazioniArticolo: { type: Function, required: true },
  // L'entita' del bus dei tab (`TAB_ENTITIES.*`) per il pannello componenti.
  tabEntity: { type: String, required: true },
  // Il namespace dei testi che nominano il documento (le chiavi di `td`).
  i18nDocumento: { type: String, required: true },
  // Sola lettura in piu' della catena dei permessi: un documento non in bozza.
  // L'involucro lo passa quando la catena non lo porta gia'.
  bloccato: { type: Boolean, default: false },
  // Una lettura da rifare insieme alla lista (padre completo, «Ricarica»): il
  // contesto pricing del contratto. Facoltativa.
  fetchExtra: { type: Function, default: null },
})

const emit = defineEmits(['update:visible', 'changed'])

const { t } = useI18n()
// Il testo di una chiave del vocabolario delle righe.
const tv = (chiave, valori) => t(`${VOC}.${chiave}`, valori)
// Il testo di una chiave che nomina il documento.
const td = (chiave, valori) => t(`${props.i18nDocumento}.${chiave}`, valori)

const { execute, loading, campiErrati } = useApiHandler()
// Le letture del form (le combinazioni dell'articolo) hanno il loro handler:
// `execute` azzera `campiErrati` e accende `loading`, che appartengono al
// salvataggio.
const { execute: executeLettura } = useApiHandler()
const { confirmDelete, confirmAction } = useConfirmAction()
const readonlyCatena = useInjectReadonly()
const isReadonly = computed(() => readonlyCatena.value || props.bloccato)

// L2 autorizzazioni prezzi: codici BE che il drawer intercetta per mostrare
// un banner inline invece del toast standard, con CTA "Richiedi approvazione"
// (workflow L3). Elenco da `useLimitiPricing`, come i preventivi.
const { L2_ERROR_CODES } = useLimitiPricing()
const l2Error = ref(null)

// Gate L1 delle azioni di riga che negoziano (decisione 2026-05-18): codename
// DB `prezzo_override_manuale`. Vale per «Modifica prezzo», «Aggiungi
// articolo» ed «Escludi» (l'esclusione modifica il rapporto commerciale col
// cliente, non e' meno sensibile). Senza permesso le azioni sono
// `visible:false`; il backend re-blocca (defense-in-depth).
const auth = useAuthStore()
const canVariarePrezzi = computed(() => auth.isActionAllowed(PRICING_ACTIONS.OVERRIDE))

// === Form inline ===
// ⭐ La macchina del form inline e' il BB `useFormInline`: `formMode`
//    null/'create'/'edit', la riga in modifica, la conferma al cambio di riga
//    (D-8) e la chiusura al cambio di documento. Prima della lista: le sue
//    azioni leggono «Nuova riga» da qui.
const {
  formMode, rigaInModifica, nuovaRiga, apriRiga, chiudiForm, ancoraForm, azioneNuovaRiga,
} = useFormInline({
  padre: () => (props.visible ? props.documentoId : null),
  puoModificare: () => !isReadonly.value,
  // D-8: letto al clic — la fotografia nasce piu' sotto.
  confermaCambio: (procedi) => chiudiConConferma(procedi),
})
// L'id della riga eccezione in modifica: nella sorgente della lista e'
// `override_riga_id` (vuoto sulle righe che vengono solo dal listino).
const rigaEditId = computed(() => rigaInModifica.value?.override_riga_id ?? null)
// La riga del listino da cui e' partito un prezzo forzato: il form e' una
// CREAZIONE (nessuna riga in modifica), ma a video va evidenziata quella.
const rigaListinoAperta = ref(null)
// La riga evidenziata nella lista (`riga_key`): quella in modifica, o quella
// del listino da cui nasce il prezzo forzato.
const rigaAttiva = computed(() => rigaInModifica.value?.riga_key ?? rigaListinoAperta.value)

// === Lista righe ===
// ⭐ Il padre e' COMPOSTO: il documento e il suo emittente. Solo a drawer
//    aperto: il `null` alla chiusura azzera la lista, o le righe del documento
//    precedente lampeggerebbero sotto il prossimo.
const righeStore = props.righeStore
const {
  searchText, onPage, onSort, paginatorProps, tablePage, listaRef,
  dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm,
} = useDrawerTabLista(righeStore, {
  parentId: {
    documentoId: () => (props.visible ? props.documentoId : null),
    emittenteId: () => (props.visible ? props.emittenteFiscaleId : null),
  },
  fetchExtra: () => props.fetchExtra?.(),
  exportFn: (params) => props.esportaRighe(props.documentoId, params),
  getExportParams: (formato) => ({ formato, ...righeStore.paramsExport() }),
  // L'unica creazione dalla toolbar e' «Aggiungi articolo» (AGGIUNTA:
  // articolo fuori listino). OVERRIDE ed ESCLUSIONE nascono sulle righe del
  // listino. Gate L1 come le azioni di riga. «Nuovo» del BB: nascosto a form
  // aperto (un secondo ingresso butterebbe la riga in scrittura) e in sola
  // lettura.
  // ⚠️ Arrow lazy: la legge il computed delle azioni, non il setup.
  extraActions: () => [
    azioneNuovaRiga({
      key: 'aggiungi-articolo',
      label: t('common.new'),
      tooltip: td('aggiungi_articolo_tooltip'),
      visible: canVariarePrezzi.value,
      command: onAggiungiArticolo,
    }),
  ],
})

// Scopo: rilegge la pagina corrente delle righe e avvisa il padre (dopo ogni
//        scrittura: la testata conta le righe).
async function rileggiRighe() {
  await righeStore.fetchList()
  emit('changed')
}

// Scopo: il prezzo della riga composita riletto dopo che il ComponentiPanel ha
//        GIA' salvato i componenti. E' un dato del server, non una modifica
//        dell'operatore: se il form era pulito resta pulito (si rifissa la
//        fotografia), o uscire chiederebbe «modifiche non salvate» per niente.
function allineaPrezzoDalServer(prezzo) {
  const eraPulito = !modificato.value
  form.value.prezzo_unitario = Number(prezzo)
  if (eraPulito) fissa()
}

// Scopo: dopo il PATCH di un componente il trigger DB `_z90_ricalcola_padre`
//        ha riscritto il prezzo della riga madre: si rilegge la lista e si
//        riallinea il solo prezzo del form, senza chiudere l'EDIT.
// ⚠️ Se la riga non sta nella pagina riletta il prezzo resta com'e': il
//    componente e' salvato, il form lo mostra alla prossima apertura.
async function onComponentiPanelChanged() {
  await rileggiRighe()
  if (formMode.value !== 'edit' || rigaEditId.value == null) return
  const fresca = righeStore.items.find((r) => r.override_riga_id === rigaEditId.value)
  if (fresca?.override_prezzo != null) allineaPrezzoDalServer(fresca.override_prezzo)
}

// === Form state ===
const form = ref({})

// Articolo selezionato corrente con flag `is_composito` (dal lookup o
// ricostruito in `_onEditRigaPersistita`). Driver dell'auto-apertura della
// ComponentiDialog e della visibilita' del ComponentiPanel.
const articoloObj = ref(null)

// === ComponentiDialog (BB `useComponentiDialog`) ===
// In CREATE l'auto-open scatta su articolo composito + UoM + qta valida
// (`qta_operativa <> 0`, che il form parte da 1); in EDIT i componenti
// persistiti stanno nel pannello sotto, senza Dialog.
const {
  componentiDialogVisible,
  componentiPayload,
  showComponentiDialog,
  apriComponentiDialog,
  onComponentiConfirm,
  resetComponentiDialog,
} = useComponentiDialog({
  form,
  isCreate: () => formMode.value === 'create',
  // Il form non vede mai un'ESCLUSIONE: nasce dal one-click «Escludi» e non
  // ha il verbo MODIFICA.
  isComposito: () => articoloObj.value?.is_composito === true,
  isPadreComposito: () => articoloObj.value?.is_composito === true,
})

// Modifiche non salvate del form inline: la fotografia vive finche' il form e'
// aperto e comprende i componenti BoM confermati nel dialog, che stanno fuori
// dal form ma partono col Salva (`componenti_overrides`). `articolo_obj` lo
// ignora il BB (suffisso `_obj`) — ⚠️ solo perche' il form e' fotografato
// APPIATTITO: annidato sotto una chiave, il BB confronterebbe l'oggetto intero.
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(
  computed(() => ({ ...form.value, componenti_confermati: componentiPayload.value })),
  { visibile: () => props.visible && formMode.value != null },
)

// Componenti della riga del listino cliccata, in forma preview (jsonb della
// funzione). Popolato quando si apre l'OVERRIDE da una riga DA_LISTINO
// composita: i suoi componenti vivono nel listino, non nella tabella dei
// componenti del documento, quindi l'`api-list` del ComponentiPanel sarebbe
// vuota. Li mostriamo read-only. Vuoto per «Aggiungi articolo».
const selectedRowComponenti = ref([])

// Reset banner L2 se l'utente modifica prezzo o articolo: segnale di retry
// con contesto potenzialmente diverso.
watch(
  () => [form.value.prezzo_unitario, form.value.articolo_id],
  () => { if (l2Error.value) l2Error.value = null },
)

// === UoM operative dell'articolo selezionato ===
const {
  uomOptions, uomLoading, loadUomPerArticolo, pickBaseUomId, resetUomOptions,
} = useArticoloUomOptions()

function uomLabel(item) {
  return item.is_base ? `${item.uom_codice} (base)` : item.uom_codice
}

async function caricaUomConPickBase(articoloId) {
  const list = await loadUomPerArticolo(articoloId)
  if (formMode.value && !form.value.uom_operativa_id) {
    form.value.uom_operativa_id = pickBaseUomId(list)
  }
}

// === Come si eroga l'articolo (dal DB) ===
// Le combinazioni (erogazione, fonte) che una riga con l'articolo del form puo'
// avere su questo documento, il default in testa. `null` = non ancora lette (o
// nessun articolo); `[]` = l'articolo non si vende su questo documento (la sua
// tipologia non e' fra quelle della utility).
const erogazioni = ref(null)
const { tag: tagErogazioni, isCurrent: erogazioniCorrenti, invalidate: invalidaErogazioni } = useFetchVersion()

// Scopo: legge le combinazioni dell'articolo. Con `preseleziona` (creazione)
//        mette nel form la combinazione di default, cioe' quella che il DB
//        erediterebbe; in modifica la riga resta com'e' scritta.
async function caricaErogazioni(articoloId, { preseleziona = false } = {}) {
  invalidaErogazioni()
  erogazioni.value = null
  if (!articoloId) return
  const token = tagErogazioni()
  const data = await executeLettura(() => props.erogazioniArticolo(props.documentoId, articoloId))
  // Arrivata tardi (l'articolo e' cambiato, o il form si e' chiuso): si scarta.
  if (!erogazioniCorrenti(token) || formMode.value == null) return
  // ⛔ Lettura fallita (`execute` → null, toast gia' mostrato): resta `null`,
  // «non lette». Diventare `[]` direbbe «l'articolo non si vende qui» per un
  // 403 o un 500, e spegnerebbe il Salva con un motivo falso.
  if (data == null) return
  erogazioni.value = data.results ?? []
  if (!preseleziona) return
  const predefinita = combinazioneDefault(erogazioni.value)
  const eraPulito = !modificato.value
  form.value.tipo_erogazione = predefinita?.tipo_erogazione ?? null
  form.value.fonte_quantita_attesa = predefinita?.fonte_quantita_attesa ?? null
  // La proposta del DB non e' una modifica dell'operatore.
  if (eraPulito) fissa()
}

// L'articolo non si vende su questo documento: nessuna combinazione. ⭐ Solo
// in CREAZIONE: il guard del perimetro scatta all'INSERT e quando cambiano
// articolo, erogazione o fonte (B-D6). Una riga gia' scritta fuori perimetro
// si aggiorna negli altri campi (il prezzo), e le tendine le tengono il valore
// scritto (`erogazioniRiga`, `opzioni`).
const articoloNonAmmesso = computed(() => formMode.value === 'create'
  && Array.isArray(erogazioni.value) && erogazioni.value.length === 0)

// Le tendine dalle combinazioni del DB (BB `erogazioniRiga`: mette in forma,
// non decide).
const tipoErogazioneOptions = computed(() => opzioniErogazione(
  erogazioni.value,
  form.value?.tipo_erogazione,
  (v) => tv(`tipo_erogazione_${v.toLowerCase()}`),
))

const fonteQuantitaOptions = computed(() => opzioniFonte(
  erogazioni.value,
  form.value?.tipo_erogazione,
  form.value?.fonte_quantita_attesa,
  (v) => tv(`fonte_quantita_value_${v.toLowerCase()}`),
))

// Q.ta operativa visibile/obbligatoria solo per fonte FISSA. Per le altre
// fonti il valore nasce downstream (documento, timesheet, letture) o dai
// componenti (trigger DB `z90_propaga_qta_componenti`).
const showQtaOperativa = computed(() => form.value?.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA)

// L'ADESIONE (G-0-ter): l'articolo del listino al prezzo del listino. Il form
// non ha il prezzo ne' i componenti, che vengono dal listino.
const isAdesione = computed(() => form.value?.tipo_eccezione === TIPO_ECCEZIONE.ADESIONE)

// La riga a canone (D-6, D-7): periodicita' e generazione si vedono e si
// mandano solo qui. Che la periodicita' sia obbligatoria lo dice il DB; la
// generazione vuota = «come la testata».
const isCanone = computed(() => form.value?.tipo_erogazione === TIPO_EROGAZIONE.CANONE)
const opzioniGenerazione = computed(() => opzioniGenerazioneCanone(t))

// Il tipo di eccezione non e' una scelta dell'operatore: lo da' l'azione che
// apre il form («Nuovo» → AGGIUNTA, riga del listino → OVERRIDE o ADESIONE). Il form lo
// mostra come Tag. Default AGGIUNTA: l'ingresso piu' generico.
function defaultForm(overrides = {}) {
  return {
    articolo_id: null,
    articolo_obj: null,
    tipo_eccezione: TIPO_ECCEZIONE.AGGIUNTA,
    // Erogazione e fonte partono VUOTE: le propone il DB quando l'articolo e'
    // noto (`caricaErogazioni`, la combinazione di default dell'articolo).
    tipo_erogazione: null,
    fonte_quantita_attesa: null,
    prezzo_unitario: null,
    qta_operativa: 1,
    uom_operativa_id: null,
    ordine: 10,
    periodicita: null,
    generazione_canone: null,
    ...overrides,
  }
}

// Reset dello stato dei componenti BoM: `closeForm` e gli ingressi CREATE.
// Tiene insieme `articoloObj` e lo stato della Dialog.
function resetComponentiState() {
  articoloObj.value = null
  resetComponentiDialog()
  selectedRowComponenti.value = []
}

// === Lifecycle ===
// Righe ed extra li legge la lista quando il padre e' completo
// (`useDrawerTabLista`): qui solo il form, che all'apertura riparte chiuso.
watch(() => props.visible, (v) => {
  if (v) closeForm()
})

// Al cambio di erogazione la fonte resta se l'articolo la ammette ancora con
// la nuova; altrimenti la prima che il DB elenca, cioe' quella che il DB
// scriverebbe (`fonteDopoCambioErogazione`, §D.4 punto 1).
watch(() => form.value?.tipo_erogazione, (nuovoTipo, vecchioTipo) => {
  if (!nuovoTipo || nuovoTipo === vecchioTipo || !erogazioni.value) return
  form.value.fonte_quantita_attesa = fonteDopoCambioErogazione(
    erogazioni.value, nuovoTipo, form.value.fonte_quantita_attesa,
  )
})

// === Azioni ===

// Scopo: ingresso CREATE «Aggiungi articolo» (toolbar): articolo libero,
//        tipo AGGIUNTA (articolo fuori listino).
function onAggiungiArticolo() {
  form.value = defaultForm({ tipo_eccezione: TIPO_ECCEZIONE.AGGIUNTA })
  nuovaRiga()
  rigaListinoAperta.value = null
  resetUomOptions()
  resetComponentiState()
  // Dopo il giro di watch: anche la creazione conta, un campo scritto e' gia'
  // una modifica da non perdere.
  nextTick(fissa)
}

// Scopo: l'apertura del form da una riga del LISTINO, comune a «Modifica
//        prezzo» (OVERRIDE) e «Aderisci» (ADESIONE): articolo (immutabile) e
//        UoM dalla riga, la composizione del bundle del listino in sola
//        lettura, le UoM e l'erogazione di default dal DB. Il chiamante dice
//        il tipo e i campi propri (`overrides` di `defaultForm`).
function apriFormDaRigaListino(row, overrides) {
  form.value = defaultForm({
    articolo_id: row.articolo_id,
    articolo_obj: {
      id: row.articolo_id,
      codice: row.articolo_codice,
      descrizione: row.articolo_descrizione,
      is_composito: row.is_composito === true,
      _display: `${row.articolo_codice} — ${row.articolo_descrizione}`,
    },
    uom_operativa_id: row.uom_id ?? null,
    // Sulla riga del listino la preview porta la periodicita' del listino
    // (D-7): e' la proposta di «Aderisci», e quella che il DB metterebbe
    // comunque senza indicazione (L4b).
    periodicita: row.periodicita ?? null,
    ...overrides,
  })
  nuovaRiga()
  rigaListinoAperta.value = row.riga_key
  // `resetComponentiState` azzera anche `articoloObj`: voluto (impedisce
  // l'auto-open della Dialog). La composizione del bundle del listino si
  // mostra read-only da `selectedRowComponenti`, DOPO il reset.
  resetComponentiState()
  selectedRowComponenti.value = rowComponenti(row)
  // Le UoM dell'articolo, o il Select mostrerebbe vuoto il valore gia' scelto.
  loadUomPerArticolo(row.articolo_id)
  nextTick(fissa)
  // Come si eroga, dal DB: la combinazione di default nel form.
  caricaErogazioni(row.articolo_id, { preseleziona: true })
}

// Scopo: ingresso CREATE «Modifica prezzo» dal click su una riga del listino
//        (verbo SOVRASCRIVI_PREZZO). Prezzo iniziale = quello del listino:
//        l'operatore lo cambia. Tipo OVERRIDE.
function onModificaPrezzo(row) {
  apriFormDaRigaListino(row, {
    tipo_eccezione: TIPO_ECCEZIONE.OVERRIDE,
    // Number() per InputNumber (il Decimal arriva come stringa).
    prezzo_unitario: row.prezzo_listino != null ? Number(row.prezzo_listino) : null,
    qta_operativa: row.qta_operativa != null ? Number(row.qta_operativa) : 1,
  })
}

// Scopo: «Escludi» dal menu di una riga del listino: conferma e salvataggio
//        diretto di un'ESCLUSIONE vuota. Niente form: la sola scelta
//        dell'operatore e' SI/NO.
function onEscludi(row) {
  confirmAction({
    header: td('escludi_dialog_titolo'),
    message: tv('escludi_dialog_messaggio', { articolo: etichettaRiga(row) }),
    acceptLabel: tv('escludi_dialog_conferma'),
    danger: true,
    onAccept: async () => {
      // ⛔ L'articolo e il tipo, NIENT'ALTRO: un'esclusione non porta dati di
      // fatturazione, e il DB rifiuta quantita', UdM, fonte o erogazione col
      // campo (E_RIGA_ESCLUSIONE_CON_DATI, brief-db-righe-esclusione-solo-non-si-vende).
      const payload = {
        articolo_id: row.articolo_id,
        tipo_eccezione: TIPO_ECCEZIONE.ESCLUSIONE,
      }
      const result = await execute(
        () => props.scritture.crea(props.documentoId, payload),
        { successMessage: td('articolo_escluso') },
      )
      if (result !== null) await rileggiRighe()
    },
  })
}

// Scopo: «Aderisci» dal menu di una riga del listino (verbo ADERISCI, G-0-ter,
//        D-4 di Tid): il form dell'ADESIONE pre-compilato, quantita' 1.
//        Niente prezzo: l'adesione addebita il prezzo del listino, e i
//        componenti di un kit aderito sono quelli del listino. La periodicita',
//        se il form non la dice, la mette il DB dalla riga di listino
//        (`trgfn_righe_default_periodicita_da_listino`).
function onAderisci(row) {
  apriFormDaRigaListino(row, { tipo_eccezione: TIPO_ECCEZIONE.ADESIONE, qta_operativa: 1 })
}

// Scopo: il click di riga e' il verbo che la riga ammette (colonna `azioni`
//        del DB), non una scelta per origine (frontend-standards §"Pattern
//        lista": modifica = click riga, kebab per le azioni secondarie):
//        - readonly: niente
//        - SOVRASCRIVI_PREZZO (riga del listino): form OVERRIDE pre-compilato.
//          Muta un prezzo: vuole lo stesso permesso di «Nuovo» ed «Escludi»
//        - MODIFICA (OVERRIDE/AGGIUNTA/ADESIONE salvata): l'edit. ⛔ Un'ESCLUSIONE non
//          ce l'ha: «un'esclusione non si modifica», e lo decide il DB
// ⭐ Riceve la RIGA, non l'evento PrimeVue: e' la firma di `row-click` di
//    `DrawerTabLista`.
function onRowClick(r) {
  if (isReadonly.value || !r) return
  const azioni = r.azioni || []
  // E' una CREAZIONE: la conferma col form aperto e modificato si chiede qui
  // (`apriRiga`, sotto, la chiede da se').
  if (azioni.includes(AZIONE_RIGA_CONTRATTO.SOVRASCRIVI_PREZZO)) {
    if (canVariarePrezzi.value) chiudiConConferma(() => onModificaPrezzo(r))
    return
  }
  if (azioni.includes(AZIONE_RIGA_CONTRATTO.MODIFICA)) _onEditRigaPersistita(r)
}

// Scopo: il form EDIT di una riga eccezione salvata (OVERRIDE/AGGIUNTA).
function _onEditRigaPersistita(r) {
  // `apriRiga` apre la modifica (l'id lo deriva `rigaEditId`) e, se un'altra
  // riga e' aperta e modificata, prima chiede: il riempimento sta in `poi`.
  apriRiga(r, () => {
    rigaListinoAperta.value = null
    form.value = {
      articolo_id: r.articolo_id,
      articolo_obj: { id: r.articolo_id, codice: r.articolo_codice, descrizione: r.articolo_descrizione, _display: `${r.articolo_codice} — ${r.articolo_descrizione}` },
      // tipo_eccezione: immutabile (lock di colonna a DB), mostrato come Tag.
      // Il form vede OVERRIDE, AGGIUNTA e ADESIONE: un'ESCLUSIONE non ha MODIFICA.
      tipo_eccezione: r.tipo_eccezione,
      // Com'e' scritta: OVERRIDE e AGGIUNTA ce l'hanno per vincolo DB.
      tipo_erogazione: r.tipo_erogazione,
      // Obbligatoria su OVERRIDE/AGGIUNTA (vuota solo sull'ESCLUSIONE, che qui
      // non arriva): niente ripiego.
      fonte_quantita_attesa: r.fonte_quantita_attesa,
      // Il prezzo scritto sulla riga eccezione.
      prezzo_unitario: r.override_prezzo != null ? Number(r.override_prezzo) : null,
      qta_operativa: r.qta_operativa != null ? Number(r.qta_operativa) : 1,
      // ⭐ UdM e ordine COSI' COME SONO SCRITTI sulla riga (§9.11, R-D2 di
      //    brief-db-liste-righe-documento): il form li rimanda al PATCH, senza
      //    ripieghi. NULL resta NULL.
      uom_operativa_id: r.uom_operativa_id ?? null,
      ordine: r.ordine ?? null,
      // ⭐ Com'e' scritta (D-7): il form le rimanda al PATCH, e vuote
      //    cancellerebbero una periodicita' o una generazione forzata.
      periodicita: r.periodicita ?? null,
      generazione_canone: r.generazione_canone ?? null,
    }
    articoloObj.value = {
      id: r.articolo_id,
      codice: r.articolo_codice,
      descrizione: r.articolo_descrizione,
      is_composito: r.is_composito === true,
    }
    // EDIT: nessuna Dialog stantia; i componenti persistiti stanno nel
    // pannello sotto il form. ⭐ L'ADESIONE non ha componenti suoi: quelli del
    // kit aderito vengono dal listino, e si mostrano in sola lettura.
    resetComponentiDialog()
    selectedRowComponenti.value = r.tipo_eccezione === TIPO_ECCEZIONE.ADESIONE
      ? rowComponenti(r)
      : []
    // UoM gia' scritta: niente autopick, solo le opzioni.
    loadUomPerArticolo(r.articolo_id)
    nextTick(fissa)
    // Le combinazioni dell'articolo per le tendine; la riga resta com'e'.
    caricaErogazioni(r.articolo_id)
  })
}

function onArticoloSelected(item) {
  form.value.articolo_id = item?.id || null
  form.value.uom_operativa_id = null
  // Fotografia dell'articolo (col flag `is_composito` del lookup) per
  // l'auto-apertura della ComponentiDialog dopo l'autopick della UoM.
  articoloObj.value = item || null
  // Cambio articolo: la Dialog si puo' riaprire sul nuovo.
  resetComponentiDialog()
  caricaUomConPickBase(item?.id)
  // Come si eroga il nuovo articolo: la combinazione di default nel form.
  caricaErogazioni(item?.id, { preseleziona: true })
}

function closeForm() {
  chiudiForm()
  rigaListinoAperta.value = null
  invalidaErogazioni()
  erogazioni.value = null
  form.value = {}
  resetUomOptions()
  resetComponentiState()
}

// === Validazione ===
const canSave = computed(() => {
  if (isReadonly.value) return false
  if (!formMode.value) return false
  if (!form.value.articolo_id) return false
  // L'articolo non si vende su questo documento: il DB rifiuterebbe la riga
  // (E_RIGA_TIPOLOGIA_FUORI_UTILITY), il form lo dice prima.
  if (articoloNonAmmesso.value) return false
  // Erogazione obbligatoria: il form vede solo OVERRIDE e AGGIUNTA, righe che
  // si fatturano (guard DB E_RIGA_EROGAZIONE_OBBLIGATORIA).
  if (!form.value.tipo_erogazione) return false
  // L'UdM e' la misura della QUANTITA': obbligatoria dove la riga ha una
  // quantita' (fonte FISSA). Una riga senza quantita' puo' non averla (vale la
  // base dell'articolo): il form non la inventa (§9.11).
  if (form.value.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA
      && !form.value.uom_operativa_id) return false
  // Fonte obbligatoria sulle righe che si fatturano (CHECK DB). Per FISSA
  // serve una quantita' diversa da zero (CHECK `qta_operativa <> 0`: negativi
  // ammessi); per le altre fonti la quantita' arriva dopo.
  if (!form.value.fonte_quantita_attesa) return false
  if (form.value.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA
      && (form.value.qta_operativa == null || Number(form.value.qta_operativa) === 0)) {
    return false
  }
  // Prezzo obbligatorio su OVERRIDE/AGGIUNTA, tranne gli articoli compositi:
  // il prezzo della madre = SUM(componenti), lo scrive il trigger DB.
  // L'ADESIONE non ha prezzo: lo da' il listino.
  const prezzoMancante = form.value.prezzo_unitario == null
    || form.value.prezzo_unitario === ''
  if (!isAdesione.value && !articoloObj.value?.is_composito && prezzoMancante) return false
  // In CREATE su composito il Salva aspetta la conferma della Dialog.
  if (showComponentiDialog.value && componentiPayload.value == null) return false
  return true
})

const formTitle = computed(() => {
  if (formMode.value === 'create') return tv('nuova_riga')
  if (formMode.value === 'edit') return tv('modifica_riga')
  return ''
})

// === Salvataggio ===

// Scopo: il payload di onSave e di onRichiediApprovazione. `extra` inietta il
//        flag opt-in `richiesta_approvazione: true` del retry L3.
function buildRigaPayload(extra = {}) {
  const f = form.value
  // `qta_operativa` solo per fonte FISSA: per le altre la fonte e' il driver,
  // e un valore qui sarebbe fuorviante.
  const isFissa = f.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA
  const payload = {
    tipo_erogazione: f.tipo_erogazione || null,
    fonte_quantita_attesa: f.fonte_quantita_attesa || null,
    qta_operativa: (isFissa && f.qta_operativa != null) ? String(f.qta_operativa) : null,
    uom_operativa_id: f.uom_operativa_id || null,
    ordine: f.ordine != null ? Number(f.ordine) : null,
    // Solo sulla riga a canone: su un'altra erogazione non hanno senso.
    periodicita: isCanone.value ? (f.periodicita || null) : null,
    generazione_canone: isCanone.value ? (f.generazione_canone || null) : null,
    ...extra,
  }
  // ⛔ L'ADESIONE non manda il prezzo: la colonna resta vuota per vincolo
  //    (`chk_*_prezzo_per_tipo_eccezione`), e il prezzo e' quello del listino.
  if (!isAdesione.value) {
    payload.prezzo_unitario = f.prezzo_unitario != null ? String(f.prezzo_unitario) : null
  }
  if (formMode.value === 'create') {
    payload.articolo_id = f.articolo_id
    // Sempre valorizzato dal gesto che ha aperto il form (`defaultForm`):
    // nessun ripiego, che direbbe un tipo diverso dal default del form.
    payload.tipo_eccezione = f.tipo_eccezione
    // Articolo composito: i `componenti_overrides` confermati nella Dialog.
    if (articoloObj.value?.is_composito === true
        && componentiPayload.value?.overrides) {
      payload.componenti_overrides = componentiPayload.value.overrides
    }
  }
  return payload
}

function submitRiga(payload) {
  return formMode.value === 'create'
    ? props.scritture.crea(props.documentoId, payload)
    : props.scritture.aggiorna(props.documentoId, rigaEditId.value, payload)
}

// Save + richiedi-approvazione con gate L2 via BB condiviso (B12, regola del 2).
// Successo: rilettura delle righe + changed + chiusura del form.
const { save: onSave, richiediApprovazione: onRichiediApprovazione } = useL2SaveFlow({
  persist: submitRiga,
  buildPayload: buildRigaPayload,
  onSuccess: async () => {
    await rileggiRighe()
    closeForm()
  },
  messages: {
    success: () => (formMode.value === 'create' ? tv('riga_creata') : tv('riga_salvata')),
    approvalRequested: tv('richiesta_approvazione_inviata'),
    error: td('errore_generico'),
  },
  l2Error,
  loading,
  l2ErrorCodes: L2_ERROR_CODES,
})

// Scopo: l'etichetta di una riga nei messaggi di conferma.
function etichettaRiga(r) {
  return r.articolo_codice
    ? `${r.articolo_codice} — ${r.articolo_descrizione}`
    : r.articolo_descrizione
}

// Scopo: cancella la riga eccezione dietro la riga di lista (il suo
//        `override_riga_id`) e rilegge. E' lo stesso gesto per «rimuovi» e
//        per i due «ripristina»: cambia solo cio' che si dice all'operatore.
async function cancellaRiga(r, successMessage) {
  const rigaId = r.override_riga_id
  const result = await execute(
    () => props.scritture.elimina(props.documentoId, rigaId),
    { successMessage },
  )
  if (result === null) return
  // Se stavo modificando questa riga, chiudi il form.
  if (rigaEditId.value === rigaId) closeForm()
  await rileggiRighe()
}

// AGGIUNTA: «Elimina» e' il nome giusto — l'articolo non e' nel listino,
// sparisce davvero dal documento.
function onDelete(r) {
  confirmDelete(
    r.articolo_codice || r.articolo_descrizione || `#${r.override_riga_id}`,
    () => cancellaRiga(r, tv('riga_eliminata')),
  )
}

// Scopo: il ripristino di un'eccezione. Stessa cancellazione di onDelete, con
//        un messaggio che dice il vero effetto: l'articolo non sparisce, torna
//        al listino. OVERRIDE → «Ripristina prezzo di listino» (vocabolario);
//        ESCLUSIONE → «Ripristina articolo nel <documento>» (testi del
//        documento).
function onRipristinaListino(r) {
  confirmAction({
    header: tv('ripristina_listino_dialog_titolo'),
    message: tv('ripristina_listino_dialog_messaggio', { articolo: etichettaRiga(r) }),
    acceptLabel: tv('ripristina_listino_dialog_conferma'),
    danger: false,
    onAccept: () => cancellaRiga(r, tv('riga_ripristinata')),
  })
}

// ADESIONE: la cancellazione non toglie l'articolo dal listino, smette di
// addebitarlo.
function onRimuoviAdesione(r) {
  confirmAction({
    header: tv('rimuovi_adesione_dialog_titolo'),
    message: tv('rimuovi_adesione_dialog_messaggio', { articolo: etichettaRiga(r) }),
    acceptLabel: tv('rimuovi_adesione_dialog_conferma'),
    danger: false,
    onAccept: () => cancellaRiga(r, tv('riga_ripristinata')),
  })
}

function onRipristinaArticolo(r) {
  confirmAction({
    header: td('ripristina_articolo_dialog_titolo'),
    message: td('ripristina_articolo_dialog_messaggio', { articolo: etichettaRiga(r) }),
    acceptLabel: tv('ripristina_articolo_dialog_conferma'),
    danger: false,
    onAccept: () => cancellaRiga(r, tv('riga_ripristinata')),
  })
}

// L'Annulla del form inline chiude solo il form, chiedendo se ci sono
// modifiche. Le uscite dal drawer (X, ESC, clic fuori, «Chiudi») passano da
// AppDrawer con la stessa conferma (`conferma-uscita`).
const annullaForm = () => chiudiConConferma(closeForm)

// Scopo: le voci del menu di riga, una per VERBO della colonna `azioni`.
//        SOVRASCRIVI_PREZZO e MODIFICA non sono qui: sono il click sulla riga.
//   - ESCLUDI (riga del listino): one-click ESCLUSIONE con conferma. Spento
//     col motivo quando il DB lo rifiuterebbe (`escludi_blocco_codice`: lo
//     stesso predicato del guard, es. un componente di un bundle del listino).
//   - RIPRISTINA_LISTINO (OVERRIDE): DELETE → torna al prezzo di listino.
//   - RIPRISTINA_ARTICOLO (ESCLUSIONE): DELETE → l'articolo torna disponibile.
//   - RIMUOVI (AGGIUNTA): DELETE → l'articolo sparisce dal documento.
//   - ADERISCI (riga del listino): il form dell'ADESIONE.
//   - RIMUOVI_ADESIONE (ADESIONE): DELETE → torna una riga del listino, che il
//     documento non addebita.
// ⚠️ Un verbo nuovo del DB senza voce qui non compare: e' un'azione che il
//    drawer non sa ancora fare, non una da inventare.
const VOCI_MENU_RIGA = {
  [AZIONE_RIGA_CONTRATTO.ESCLUDI]: (r) => ({
    key: 'escludi',
    label: tv('azione_escludi'),
    icon: MANAGE_ICONS.ESCLUDI,
    severity: 'warn',
    // Gate L1 (`prezzo_override_manuale`): l'esclusione e' negoziazione.
    visible: canVariarePrezzi.value,
    disabled: !!r.escludi_blocco_codice,
    tooltip: r.escludi_blocco_codice
      ? tv(`escludi_blocco.${r.escludi_blocco_codice.toLowerCase()}`)
      : '',
    command: () => onEscludi(r),
  }),
  // ADERISCI (riga del listino): il form dell'ADESIONE. Nessun gate prezzi:
  // l'adesione non scrive un prezzo, prende quello del listino.
  [AZIONE_RIGA_CONTRATTO.ADERISCI]: (r) => ({
    key: 'aderisci',
    label: tv('azione_aderisci'),
    icon: MANAGE_ICONS.ADERISCI,
    severity: 'success',
    command: () => chiudiConConferma(() => onAderisci(r)),
  }),
  [AZIONE_RIGA_CONTRATTO.RIMUOVI_ADESIONE]: (r) => ({
    key: 'rimuovi-adesione',
    label: tv('azione_rimuovi_adesione'),
    icon: MANAGE_ICONS.RIPRISTINA_LISTINO,
    severity: 'secondary',
    command: () => onRimuoviAdesione(r),
  }),
  [AZIONE_RIGA_CONTRATTO.RIPRISTINA_LISTINO]: (r) => ({
    key: 'ripristina-listino',
    label: tv('azione_ripristina_listino'),
    icon: MANAGE_ICONS.RIPRISTINA_LISTINO,
    severity: 'secondary',
    command: () => onRipristinaListino(r),
  }),
  [AZIONE_RIGA_CONTRATTO.RIPRISTINA_ARTICOLO]: (r) => ({
    key: 'ripristina-articolo',
    label: td('azione_ripristina_articolo'),
    icon: MANAGE_ICONS.RIPRISTINA_LISTINO,
    severity: 'secondary',
    command: () => onRipristinaArticolo(r),
  }),
  [AZIONE_RIGA_CONTRATTO.RIMUOVI]: (r) => ({
    key: 'rimuovi-aggiunta',
    label: td('azione_rimuovi_aggiunta'),
    icon: MANAGE_ICONS.DELETE,
    severity: 'danger',
    command: () => onDelete(r),
  }),
}

function buildRigaActions(r) {
  return (r.azioni || [])
    .filter((verbo) => VOCI_MENU_RIGA[verbo])
    .map((verbo) => VOCI_MENU_RIGA[verbo](r))
}

// Scopo: severity del Tag per origine della riga (cella `origine`): DA_LISTINO
//        neutra, OVERRIDE info (prezzo personalizzato), AGGIUNTA e ADESIONE
//        success (si addebitano), ESCLUSIONE warn (articolo tolto dal listino).
function origineSeverity(origine) {
  if (origine === TIPO_ECCEZIONE.OVERRIDE) return 'info'
  if (origine === TIPO_ECCEZIONE.AGGIUNTA) return 'success'
  if (origine === TIPO_ECCEZIONE.ADESIONE) return 'success'
  if (origine === TIPO_ECCEZIONE.ESCLUSIONE) return 'warn'
  if (origine === TIPO_ECCEZIONE.DA_LISTINO) return 'secondary'
  return null
}
</script>

<template>
  <!-- ⭐ `proteggi-corpo` spento (come le altre liste dentro un drawer: distinta,
       BoM): in sola lettura il drawer protegge NASCONDENDO le scritture — menu
       di riga non montato, click di riga inerte, «Nuovo» nascosto, pannello
       componenti `readonly` —, e la lista resta consultabile per intero,
       export e colonne compresi. -->
  <AppDrawer
    :visible="props.visible"
    :title="td('drawer_righe_titolo')"
    :icon="MANAGE_ICONS.RIGHE"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.WIDE_PLUS"
    :readonly="props.bloccato"
    :proteggi-corpo="false"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="formMode ? 'nessuno' : 'chiudi'"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <!-- L'intestazione del documento (BB DrawerContextHeader), dell'involucro. -->
    <slot name="intestazione" />

    <!-- Gli avvisi del documento sopra la lista (il contesto pricing del
         contratto), dell'involucro. -->
    <slot name="avvisi" />

    <!-- === MASTER: la lista configurabile delle righe ===
         Colonne dal catalogo, ricerca ed export dal backend, chiave `riga_key`
         dal DB. ⛔ «Non sono riuscito a leggere le righe» non e' «non ce ne
         sono»: a lista vuota la tabella mostrerebbe lo stesso stato. -->
    <Message v-if="righeStore.erroreCaricamento" severity="warn" :closable="false" size="small">
      {{ t('common.righe_non_lette') }}
    </Message>
    <DrawerTabLista
      ref="listaRef"
      :codice="props.listaCodice"
      :store="righeStore"
      :emittente-esplicito="emittenteFiscaleId"
      :rows="righeStore.items"
      :total="righeStore.totalRecords"
      :loading="righeStore.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      :page-actions="pageActions"
      :dirty="dirty"
      :perimetro-bloccato="perimetroBloccato"
      data-key="riga_key"
      :riga-attiva="rigaAttiva"
      :righe-cliccabili="!isReadonly"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      @config-loaded="onConfigLoaded"
    >
      <!-- La ricerca: codice e descrizione articolo (`ricerca_full` a
           catalogo), lato server. L'export porta la stessa `search`. -->
      <template #filtri-sempre>
        <InputText v-model="searchText" class="app-filter-w-lg"
          :placeholder="tv('filtro_articolo_placeholder')" />
      </template>

      <template #cell-origine="{ data }">
        <Tag v-if="data.origine"
          :value="tv(`origine_${data.origine.toLowerCase()}`)"
          :severity="origineSeverity(data.origine)" />
      </template>

      <!-- I componenti di un bundle, nella riga espandibile: arrivano gia'
           aggregati nel jsonb `componenti` della funzione, tanto per i bundle
           del listino quanto per le aggiunte. `ComponentiPanel` in modalita'
           data-driven (`initialData`): niente fetch. -->
      <template #row-expansion="{ data }">
        <div v-if="hasBundleComponenti(data)" class="righe-eccezioni-componenti-espansi">
          <ComponentiPanel
            :initial-data="rowComponenti(data)"
            i18n-prefix="vendite.componenti.panel" />
        </div>
      </template>

      <!-- In sola lettura (documento fuori bozza, o permesso LETTURA) nessuna
           voce: lo slot condizionato non monta la colonna. -->
      <template v-if="!isReadonly" #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRigaActions(data)" />
      </template>
    </DrawerTabLista>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />

    <!-- === DETAIL: form inserimento/modifica === -->
    <template v-if="formMode">
      <div :ref="ancoraForm" class="app-drawer-section">
        <h4>{{ formTitle }}</h4>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ tv('field_articolo') }} *</label>
          <!-- L'articolo e' libero SOLO per «Aggiungi articolo» (AGGIUNTA
               fuori listino). Per «Modifica prezzo» (OVERRIDE) e in EDIT e'
               gia' identificato dalla riga. -->
          <ArticoloLookup
            v-model="form.articolo_obj"
            @update:modelValue="onArticoloSelected"
            :disabled="formMode === 'edit' || form.tipo_eccezione !== TIPO_ECCEZIONE.AGGIUNTA"
            :documento="documento"
            :documento-id="documentoId"
            :tipo-eccezione="form.tipo_eccezione"
            :placeholder="tv('select_articolo')"
          />
          <!-- Nessuna combinazione: la tipologia dell'articolo non e' fra
               quelle della utility del documento. -->
          <small v-if="articoloNonAmmesso" class="app-field-error">
            {{ tv('erogazioni_articolo_non_ammesso') }}
          </small>
        </div>
        <div class="form-field">
          <!-- Il tipo di eccezione lo da' il gesto che ha aperto il form: Tag
               in sola lettura, in CREATE come in EDIT. -->
          <label>{{ tv('field_tipo_eccezione') }}</label>
          <div>
            <Tag :value="tv(`tipo_eccezione_${form.tipo_eccezione}`)"
              severity="secondary" />
          </div>
        </div>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <!-- Obbligatoria solo dove la riga ha una quantita' (fonte FISSA):
               la stessa regola di `canSave`. -->
          <label>{{ tv('field_uom') }}<span v-if="showQtaOperativa"> *</span></label>
          <Select v-model="form.uom_operativa_id"
            :options="uomOptions"
            option-value="uom_id"
            :option-label="uomLabel"
            :placeholder="form.articolo_id ? tv('select_uom') : tv('uom_select_articolo_first')"
            :disabled="!form.articolo_id || uomLoading"
            :loading="uomLoading"
            />
        </div>
        <div class="form-field">
          <label>{{ tv('field_tipo_erogazione') }} *</label>
          <Select v-model="form.tipo_erogazione" :options="tipoErogazioneOptions"
            option-label="label" option-value="value"
            :placeholder="tv('select_tipo_erogazione')"
            :invalid="campiErrati.includes('tipo_erogazione')" />
        </div>
      </div>

      <!-- Erogazione e fonte: le combinazioni che l'articolo ammette, dal DB
           (`fn_documento_riga_erogazioni`); la fonte filtrata per erogazione. -->
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ tv('field_fonte_quantita_attesa') }} *</label>
          <Select v-model="form.fonte_quantita_attesa"
            :options="fonteQuantitaOptions"
            option-label="label" option-value="value"
            :placeholder="tv('select_fonte_quantita')"
            :invalid="campiErrati.includes('fonte_quantita_attesa')"
            />
        </div>
        <!-- L'ADESIONE non ha prezzo suo: un Tag dice da dove arriva. -->
        <div class="form-field" v-if="isAdesione">
          <label>{{ tv('field_prezzo_unitario') }}</label>
          <div>
            <Tag severity="info" :value="tv('prezzo_da_listino')"
              v-tooltip.top="tv('prezzo_da_listino_tooltip')" />
          </div>
        </div>
        <div class="form-field" v-else>
          <label>
            {{ tv('field_prezzo_unitario') }}
            <!-- Obbligatorio per OVERRIDE/AGGIUNTA non composito. -->
            <span v-if="!articoloObj?.is_composito">*</span>
            <Tag v-if="articoloObj?.is_composito"
              severity="info"
              :value="t('vendite.componenti.panel.padre_calcolato')"
              v-tooltip.top="t('vendite.componenti.panel.padre_calcolato_tooltip')"
              class="righe-eccezioni-padre-tag" />
          </label>
          <InputNumber v-model="form.prezzo_unitario"
            :disabled="articoloObj?.is_composito === true"
            :min-fraction-digits="2" :max-fraction-digits="4" showButtons />
        </div>
      </div>

      <!-- La riga a canone (D-6, D-7): ogni quanto si addebita e come. La
           periodicita' sulla riga del listino arriva proposta dal listino; la
           generazione vuota segue la testata. -->
      <div class="form-grid-2col" v-if="isCanone">
        <div class="form-field">
          <label>{{ t('vendite.canoni.field_periodicita') }}</label>
          <PeriodicitaSelect v-model="form.periodicita"
            :placeholder="t('vendite.canoni.select_periodicita')"
            :invalid="campiErrati.includes('periodicita')" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.canoni.field_generazione_canone') }}</label>
          <Select v-model="form.generazione_canone"
            :options="opzioniGenerazione"
            option-label="label" option-value="value" show-clear
            :placeholder="t('vendite.canoni.generazione_come_testata')"
            :invalid="campiErrati.includes('generazione_canone')" />
        </div>
      </div>

      <!-- Q.ta operativa solo per fonte FISSA; per le altre un Tag dice da dove
           arrivera' il valore. -->
      <div class="form-grid-2col">
        <div class="form-field" v-if="showQtaOperativa">
          <label>{{ td('field_qta_operativa_fissa') }} *</label>
          <InputNumber v-model="form.qta_operativa"
            :min="0.0001" :min-fraction-digits="0" :max-fraction-digits="4" showButtons />
        </div>
        <div class="form-field" v-else-if="form.fonte_quantita_attesa">
          <label>{{ tv('field_qta_operativa') }}</label>
          <Tag severity="info"
            :value="tv(`fonte_quantita_tag_${form.fonte_quantita_attesa.toLowerCase()}`)"
            v-tooltip.top="tv('fonte_quantita_tag_tooltip')" />
        </div>
        <div class="form-field">
          <label>{{ tv('field_ordine') }}</label>
          <InputNumber v-model="form.ordine" :min="0"
            :invalid="campiErrati.includes('ordine')"
          />
        </div>
      </div>

      <!-- Componenti BoM. CREATE: il payload della Dialog parte col Salva
           (`componenti_overrides`). EDIT: il pannello carica i componenti
           persistiti e li rende modificabili. -->
      <template v-if="articoloObj?.is_composito && !isAdesione">
        <ComponentiCreateActionsPanel
          v-if="formMode === 'create'"
          :disabled="!form.articolo_id || !form.uom_operativa_id
            || (showQtaOperativa && (form.qta_operativa || 0) <= 0)"
          :componenti-payload="componentiPayload"
          @apri-dialog="apriComponentiDialog"
        />
        <template v-else>
          <div class="app-drawer-section">
            <h4>{{ t('vendite.componenti.panel.section_title') }}</h4>
          </div>
          <ComponentiPanel
            :documento-id="props.documentoId"
            :riga-id="rigaEditId"
            :readonly="isReadonly || formMode !== 'edit'"
            :api-list="props.apiComponenti.elenco"
            :api-update="props.apiComponenti.aggiorna"
            :api-delete="props.apiComponenti.elimina"
            :tab-entity="props.tabEntity"
            @changed="onComponentiPanelChanged" />
        </template>
      </template>

      <!-- Composizione del bundle del listino (read-only), quando l'OVERRIDE
           parte da una riga composita del listino: i figli vivono nel listino,
           non nei componenti del documento. Indipendente dal blocco sopra
           (`articoloObj` qui resta null per non auto-aprire la Dialog). -->
      <template v-if="selectedRowComponenti.length">
        <div class="app-drawer-section">
          <h4>{{ t('vendite.componenti.panel.section_title') }}</h4>
        </div>
        <ComponentiPanel
          :initial-data="selectedRowComponenti"
          readonly
          i18n-prefix="vendite.componenti.panel" />
      </template>

      <!-- Banner inline L2 (BB condiviso): violazione di soglia sul prezzo →
           «Richiedi approvazione» ripete il salvataggio con
           `richiesta_approvazione=true` (workflow L3). -->
      <L2ErrorBanner
        :error="l2Error"
        :loading="loading"
        :label="tv('richiedi_approvazione')"
        :label-loading="tv('richiedi_approvazione_in_corso')"
        :tooltip="tv('richiedi_approvazione_tooltip')"
        @richiedi="onRichiediApprovazione"
      />

      <FormFooter
        :loading="loading"
        :disabled="!canSave"
        @save="onSave"
        @cancel="annullaForm"
      />
    </template>

    <!-- ComponentiDialog modale: pre-popola i prezzi dei componenti BoM
         prima del salvataggio di una riga composita. -->
    <ComponentiDialog
      v-model:visible="componentiDialogVisible"
      :articolo="articoloObj"
      :documento-id="props.documentoId"
      :uom-operativa-id="form.uom_operativa_id"
      :quantita="form.qta_operativa"
      :api-preview="props.apiComponenti.anteprima"
      :initial-payload="componentiPayload"
      @confirm="onComponentiConfirm" />
  </AppDrawer>
</template>

<style scoped>
.righe-eccezioni-padre-tag {
  font-size: 0.65rem;
  margin-left: 0.4rem;
  padding: 0.05rem 0.3rem;
}
.righe-eccezioni-componenti-espansi {
  padding: 0.25rem 0 0.5rem 2rem;
  background: var(--app-table-stripe-bg);
}
</style>
