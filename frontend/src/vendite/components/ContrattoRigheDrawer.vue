<script setup>
// Scopo: Sub-drawer gestione righe contratto (modello unificato 2026-05-15)
//        — pattern master-detail inline. Lista paginata sopra (righe per
//        pagina dal preset della lista), form dettaglio sotto. Click riga =
//        edit, pulsante Nuovo = create, Salva/Annulla sempre in basso.
//
// Refactor modalita 2026-05-15: le righe sono ECCEZIONI tipizzate del listino
// (tipo_eccezione = OVERRIDE / ESCLUSIONE / AGGIUNTA), non piu' "righe di
// modalita C". La forma del contratto e' "con_listino" o "senza_listino",
// derivata dalla testata. Le azioni "Modifica prezzo" (OVERRIDE), "Escludi"
// (ESCLUSIONE), "Aggiungi articolo" (AGGIUNTA) corrispondono ai 3 tipi.
//
// ⭐ DAL 2026-10-04 LE RIGHE SONO LA LISTA CONFIGURABILE `vendite.contratto_righe`
//    (brief-db-liste-righe-documento, lotto D, §8.13.5 e §9.11). Fino a quel
//    giorno qui c'era una `DataTable` grezza con DUE sorgenti — le righe del
//    dettaglio del padre (`righeIniziali`) senza listino, l'anteprima prezzi
//    con — una chiave inventata dal frontend (`_row_key`), il filtro articolo
//    lato client e le azioni di riga decise qui per origine. Ora:
//    · una sorgente per le due forme, `vendite.fn_contratto_righe_preview`
//      (senza listino risponde le sole aggiunte), paginata e cercata dal
//      backend, con colonne dal catalogo, ritiro nella riga espandibile,
//      personalizzazione ed export;
//    · la chiave e' `riga_key`, emessa dal DB;
//    · i verbi della riga sono la colonna `azioni` (capability di riga): il
//      drawer li RENDE, non li decide. «Escludi» spento porta il motivo da
//      `escludi_blocco_codice`, lo stesso predicato del guard;
//    · la riga salvata porta `ordine` e `uom_operativa_id` (§9.11, R-D2): il
//      form li rimanda com'erano, senza ripieghi.
import { ref, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContrattiStore } from '../stores/contratti'
import { useContrattoRigheStore } from '../stores/contrattoRighe'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useFormInline } from '../../core/composables/useFormInline'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import { useLimitiPricing } from '../composables/useLimitiPricing'
import {
  AZIONE_RIGA_CONTRATTO, FONTE_QUANTITA_ATTESA, FORMA_CONTRATTO, PRICING_ACTIONS, TIPO_ECCEZIONE,
  TIPO_EROGAZIONE,
} from '../constants'
import { DRAWER_WIDTH, MANAGE_ICONS, TAB_ENTITIES, STATUS_ICONS } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { statoContrattoSeverity } from '../../core/utils/severity'
import { useArticoloUomOptions } from '../../catalogo/composables/useArticoloUomOptions'
import {
  previewRigaComponenti,
  listRigaComponenti as listContrattoRigaComponenti,
  updateRigaComponente as updateContrattoRigaComponente,
  deleteRigaComponente as deleteContrattoRigaComponente,
  getContrattoContestoPricing,
  exportRigheLista,
} from '../api/contratti'
import AppDrawer from '../../core/components/AppDrawer.vue'
import DrawerContextHeader from '../../core/components/DrawerContextHeader.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import ArticoloLookup from '../../catalogo/components/ArticoloLookup.vue'
import { rowComponenti, hasBundleComponenti } from '../_shared/componenti/rowComponenti'
import ComponentiCreateActionsPanel from '../_shared/componenti/ComponentiCreateActionsPanel.vue'
import ComponentiDialog from '../_shared/componenti/ComponentiDialog.vue'
import { useComponentiDialog } from '../_shared/componenti/useComponentiDialog'
import ComponentiPanel from '../_shared/componenti/ComponentiPanel.vue'
import L2ErrorBanner from '../_shared/pricing/L2ErrorBanner.vue'
import { useL2SaveFlow } from '../_shared/pricing/useL2SaveFlow'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'

const { t } = useI18n()
const store = useContrattiStore()
const { execute, loading, campiErrati } = useApiHandler()
const { confirmDelete, confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()

// L2 autorizzazioni prezzi: codici BE che il drawer intercetta per mostrare
// un banner inline invece del toast standard, con CTA "Richiedi approvazione"
// (workflow L3 cablato 2026-05-19 BE porting gate riga contratti). Riusato
// elenco da `useLimitiPricing` per coerenza col pattern preventivi.
const { L2_ERROR_CODES } = useLimitiPricing()
const l2Error = ref(null)

// Gate L1 azioni di riga "variare prezzi" (label UX): decisione 2026-05-18.
// Codename DB stabile `prezzo_override_manuale`. La gate vale per le azioni
// che mutano il prezzo (Modifica prezzo, Aggiungi articolo). Anche "Escludi"
// e' negoziazione contrattuale e richiede lo stesso permesso: l'esclusione
// modifica il rapporto commerciale col cliente, non e' meno sensibile.
// Senza permesso le azioni sono `visible:false` (UX pulita) e il BE
// re-blocca con 403 retryable (defense-in-depth).
const auth = useAuthStore()
const canVariarePrezzi = computed(() => auth.isActionAllowed(PRICING_ACTIONS.OVERRIDE))

const props = defineProps({
  visible: Boolean,
  contrattoId: { type: Number, required: true },
  // L'emittente del contratto (PK di `anagrafiche.emittenti_fiscali`): il
  // lasciapassare del cancello di perimetro della lista. Finche' manca la
  // lista e' in attesa, non vuota (padre composto di `useListaStoreCore`).
  emittenteFiscaleId: { type: Number, default: null },
  // Refactor modalita 2026-05-15: niente piu' modalita A/B/C. La "forma"
  // arriva dal parent (derivata dai campi testata) ed e' "con_listino" o
  // "senza_listino". Default null: il drawer la legge dal contesto pricing.
  // ⚠️ Serve SOLO al banner: la lista non decide niente per forma.
  contrattoForma: { type: String, default: null },
  // Contesto contratto (per intestazione riepilogativa)
  contrattoNumero: { type: String, default: '' },
  contrattoCliente: { type: String, default: '' },
  contrattoValidoDal: { type: String, default: '' },
  contrattoValidoAl: { type: String, default: null },
  contrattoStatoCodice: { type: String, default: '' },
  contrattoStatoDescrizione: { type: String, default: '' },
})

const emit = defineEmits(['update:visible', 'changed'])

// === Contesto pricing contratto (FE 2.2) ===
// Mutuato dal pattern preventivi `getContestoPricing`. Espone forma, listino
// + versione fissata (post-attivazione) o corrente (DRAFT), variazione,
// categoria cliente. Renderizzato come banner informativo nell'header drawer.
const contestoPricing = ref(null)

// Forma effettiva: priorita' al backend (contesto pricing), fallback alla prop.
const formaEffettiva = computed(() => contestoPricing.value?.forma || props.contrattoForma)
const isSenzaListino = computed(() => formaEffettiva.value === FORMA_CONTRATTO.SENZA_LISTINO)

// Listino associato ma senza versione operativa oggi: la lista ha le sole
// eccezioni, e l'operatore deve attivare una versione del listino.
// ⭐ Dal contesto pricing, che sceglie la versione con la regola del contratto:
//    fino al 2026-10-04 lo diceva l'anteprima («nessuna riga DA_LISTINO»), che
//    non e' piu' una lettura del drawer — e che scambiava per «senza versione»
//    anche un listino con tutti gli articoli esclusi.
const listinoSenzaVersione = computed(() => (
  contestoPricing.value?.forma === FORMA_CONTRATTO.CON_LISTINO
    && contestoPricing.value?.listino_versione_id == null
))

async function loadContestoPricing() {
  if (!props.contrattoId) {
    contestoPricing.value = null
    return
  }
  try {
    const res = await getContrattoContestoPricing(props.contrattoId)
    contestoPricing.value = res?.data?.data || null
  } catch (err) {
    contestoPricing.value = null
    console.warn('contratto contesto pricing fetch failed',
      err?.response?.data || err)
  }
}

// === Form inline ===
// ⭐ La macchina del form inline e' il BB `useFormInline` (2026-10-03, regola
//    del 2, ok Tid): `formMode` null/'create'/'edit', la riga in modifica, la
//    conferma al cambio di riga (D-8) e la chiusura al cambio di contratto.
//    Prima della lista: le sue azioni leggono «Nuova riga» da qui.
const {
  formMode, rigaInModifica, nuovaRiga, apriRiga, chiudiForm, azioneNuovaRiga,
} = useFormInline({
  padre: () => (props.visible ? props.contrattoId : null),
  puoModificare: () => !isReadonly.value,
  // D-8: letto al clic — la fotografia nasce piu' sotto.
  confermaCambio: (procedi) => chiudiConConferma(procedi),
})
// L'id della riga di `contratti_righe` in modifica: nella sorgente della
// lista e' `override_riga_id` (vuoto sulle righe che vengono solo dal listino).
const rigaEditId = computed(() => rigaInModifica.value?.override_riga_id ?? null)
// La riga del listino da cui e' partito un prezzo forzato: il form e' una
// CREAZIONE (nessuna riga in modifica), ma a video va evidenziata quella.
const rigaListinoAperta = ref(null)
// La riga evidenziata nella lista (`riga_key`): quella in modifica, o quella
// del listino da cui nasce il prezzo forzato.
const rigaAttiva = computed(() => rigaInModifica.value?.riga_key ?? rigaListinoAperta.value)

// === Lista righe (`vendite.contratto_righe`) ===
// ⭐ Il padre e' COMPOSTO: il contratto e il suo emittente. Solo a drawer
//    aperto: il `null` alla chiusura azzera la lista, o le righe del contratto
//    precedente lampeggerebbero sotto il prossimo.
// ⭐ Il contesto pricing e' l'extra della lista: si legge col padre, e
//    «Ricarica» riallinea entrambi (banner e righe dipendono dalla stessa
//    versione del listino).
const righeStore = useContrattoRigheStore()
const {
  searchText, onPage, onSort, paginatorProps, tablePage, listaRef,
  dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm,
} = useDrawerTabLista(righeStore, {
  parentId: {
    documentoId: () => (props.visible ? props.contrattoId : null),
    emittenteId: () => (props.visible ? props.emittenteFiscaleId : null),
  },
  fetchExtra: () => loadContestoPricing(),
  exportFn: (params) => exportRigheLista(props.contrattoId, params),
  getExportParams: (formato) => ({ formato, ...righeStore.paramsExport() }),
  // Refactor 2026-05-18 (FE 2.2 Opzione C): l'unica azione globale di create
  // diretta dalla toolbar e' "Aggiungi articolo" (tipo_eccezione=AGGIUNTA:
  // articolo fuori-listino). Le azioni OVERRIDE/ESCLUSIONE si fanno
  // contestualmente sulle righe del listino. Gate L1 visibile per simmetria con
  // le azioni di riga: senza permesso `prezzo_override_manuale` non puoi
  // nemmeno aggiungere articoli.
  // «Nuovo» del BB: nascosto a form aperto (un secondo ingresso butterebbe la
  // riga in scrittura) e in sola lettura.
  // ⚠️ Arrow lazy: la legge il computed delle azioni, non il setup.
  extraActions: () => [
    azioneNuovaRiga({
      key: 'aggiungi-articolo',
      label: t('common.new'),
      tooltip: t('vendite.contratti.aggiungi_articolo_tooltip'),
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

// Scopo: handler @changed di ComponentiPanel API-driven in EDIT su
//        articolo composito. Dopo PATCH componente, il trigger DB
//        `_z90_ricalcola_padre` ha aggiornato `prezzo_unitario` sulla
//        riga padre. Risincronizza solo quel campo del form (UI mostra
//        SUM aggiornato) senza chiudere/riaprire l'EDIT e senza perdere
//        modifiche pending dell'utente (qty/ordine/ecc.).
// ⚠️ Se la riga non sta nella pagina riletta il prezzo resta com'e': il
//    componente e' salvato, il form lo mostra alla prossima apertura.

// Scopo: il prezzo della riga composita riletto dopo che il ComponentiPanel ha
//        GIA' salvato i componenti. E' un dato del server, non una modifica
//        dell'operatore: se il form era pulito resta pulito (si rifissa la
//        fotografia), o uscire chiederebbe «modifiche non salvate» per niente.
function allineaPrezzoDalServer(prezzo) {
  const eraPulito = !modificato.value
  form.value.prezzo_unitario = Number(prezzo)
  if (eraPulito) fissa()
}

async function onComponentiPanelChanged() {
  await rileggiRighe()
  if (formMode.value !== 'edit' || rigaEditId.value == null) return
  const fresca = righeStore.items.find((r) => r.override_riga_id === rigaEditId.value)
  if (fresca?.override_prezzo != null) allineaPrezzoDalServer(fresca.override_prezzo)
}

// === Form state ===
const form = ref({})

// Articolo selezionato corrente con flag `is_composito` (dal lookup
// `ArticoloLookup` o ricostruito in `_onEditRigaPersistita` per EDIT). Driver della
// detection auto-apertura ComponentiDialog + visibilita' ComponentiPanel
// (modello unificato BoM 2026-05-13).
const articoloObj = ref(null)

// === ComponentiDialog state (modello unificato BoM 2026-05-13) ===
// Pattern speculare a `PreventiviRigaForm.vue`: in CREATE su articolo
// composito, la Dialog si auto-apre al primo set di (articolo, uom, qta)
// validi; in EDIT lo stato componenti viaggia via `ComponentiPanel` sotto
// il form (lista persistita).
// Orchestrazione ComponentiDialog centralizzata nel BB `useComponentiDialog`
// (estrazione regola-del-2 2026-05-31). In CREATE l'auto-open scatta su
// articolo composito + UoM + qta valida (default `qta_operativa <> 0`); in
// EDIT il flusso e' diverso (panel sotto, no Dialog). isComposito e
// isPadreComposito leggono `articoloObj.is_composito`.
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
  // ESCLUSIONE escluso: un articolo escluso non ha prezzo (il DB impone
  // prezzo_unitario NULL) ne' senso di negoziarne i componenti BoM. Niente
  // ComponentiDialog ne' invio `componenti_overrides` per le ESCLUSIONI.
  isComposito: () => articoloObj.value?.is_composito === true
    && form.value?.tipo_eccezione !== TIPO_ECCEZIONE.ESCLUSIONE,
  isPadreComposito: () => articoloObj.value?.is_composito === true
    && form.value?.tipo_eccezione !== TIPO_ECCEZIONE.ESCLUSIONE,
})

// Modifiche non salvate del form inline (2026-10-03, D-1 di
// work-done/analisi-fe-chrome-drawer.md). Fino a quel giorno X, ESC e
// clic fuori chiudevano con un `emit` diretto: una riga compilata e non
// salvata si perdeva senza domanda. La fotografia vive finche' il form e'
// aperto e comprende i componenti BoM confermati nel dialog, che stanno fuori
// dal form ma partono col Salva (`componenti_overrides`). `articolo_obj` lo
// ignora il BB (suffisso `_obj`) — ⚠️ solo perche' il form e' fotografato
// APPIATTITO: annidato sotto una chiave, il BB confronterebbe l'oggetto intero
// e `articolo_obj` ci entrerebbe.
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(
  computed(() => ({ ...form.value, componenti_confermati: componentiPayload.value })),
  { visibile: () => props.visible && formMode.value != null },
)

// Componenti della riga sorgente cliccata, in shape preview (jsonb dalla fn
// DB). Popolato quando si apre il form OVERRIDE da una riga DA_LISTINO
// composita: i suoi componenti vivono nel listino (non in
// contratti_righe_componenti), quindi l'`api-list` del ComponentiPanel
// sarebbe vuota. Li mostriamo read-only inline (data-driven) cosi' l'operatore
// vede subito la composizione, come nell'OffertaEccezioniDrawer. Vuoto per
// "Aggiungi articolo" (nessuna riga sorgente).
const selectedRowComponenti = ref([])

// Reset banner L2 se l'utente modifica prezzo o articolo: segnale di retry
// con contesto potenzialmente diverso. Pattern identico a PreventiviRigaForm.
watch(
  () => [form.value.prezzo_unitario, form.value.articolo_id],
  () => { if (l2Error.value) l2Error.value = null },
)

// === UoM operative dell'articolo selezionato ===
// Composable centralizzato (Fase 4.F1). Autopick base se il form e' attivo
// (create OR edit con UoM mancante) — replica l'esatto criterio originale.
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

// === Options ===
const tipoErogazioneOptions = computed(() => [
  { value: TIPO_EROGAZIONE.CANONE, label: t('vendite.contratti.tipo_erogazione_canone') },
  { value: TIPO_EROGAZIONE.CONSUMO, label: t('vendite.contratti.tipo_erogazione_consumo') },
  { value: TIPO_EROGAZIONE.UNA_TANTUM, label: t('vendite.contratti.tipo_erogazione_una_tantum') },
])

// Refactor 2026-05-19: matrice (tipo_erogazione × fonte_quantita_attesa).
// Le fonti vietate (CHECK chk_contrighe_coerenza_fonte_erogazione, migration
// 20260519-05) NON appaiono nelle liste — il Select e' filtrato per tipo.
// severity: 'warn' = uso atipico (🟡 nella matrice), undefined = valida.
// default: true = scelta predefinita pre-compilata in CREATE.
// TIMESHEET commentato finche' il modulo rendicontazione ore non esistera'.
// Riferimento: docs/it/dev/work-done/refactor-contratti-fonte-quantita.md §3.
const FONTI_PER_TIPO_EROGAZIONE = {
  [TIPO_EROGAZIONE.CANONE]: [
    { value: FONTE_QUANTITA_ATTESA.FISSA, default: true },
    { value: FONTE_QUANTITA_ATTESA.MANUALE, severity: 'warn' },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
  [TIPO_EROGAZIONE.UNA_TANTUM]: [
    { value: FONTE_QUANTITA_ATTESA.FISSA, default: true },
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
  [TIPO_EROGAZIONE.ORARIO]: [
    { value: FONTE_QUANTITA_ATTESA.FISSA, severity: 'warn' },
    { value: FONTE_QUANTITA_ATTESA.MANUALE, default: true },
    // { value: FONTE_QUANTITA_ATTESA.TIMESHEET },  // attivare quando il modulo timesheet esistera'
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI, severity: 'warn' },
  ],
  [TIPO_EROGAZIONE.CONSUMO]: [
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.LETTURE, default: true },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
}

function _fontiPerTipo(tipo) {
  return FONTI_PER_TIPO_EROGAZIONE[tipo] || []
}

function _defaultFontePerTipo(tipo) {
  return _fontiPerTipo(tipo).find(f => f.default)?.value ?? null
}

const fonteQuantitaOptions = computed(() => _fontiPerTipo(form.value?.tipo_erogazione).map(f => ({
  value: f.value,
  label: t(`vendite.contratti.fonte_quantita_value_${f.value.toLowerCase()}`),
  severity: f.severity,
})))

const fonteCorrente = computed(() => fonteQuantitaOptions.value.find(f => f.value === form.value?.fonte_quantita_attesa) || null)

// Q.ta operativa visibile/obbligatoria solo per fonte FISSA. Per le altre
// 4 fonti il valore vero nasce downstream (manuale sul documento / timesheet
// / letture / derivato dai componenti via trigger DB z90_propaga_qta_componenti).
const showQtaOperativa = computed(() => form.value?.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA)

// Refactor 2026-05-18 (FE 2.2 Opzione C): il tipo_eccezione non e' piu' una
// scelta dell'operatore via Select, ma e' DERIVATO dall'azione che ha aperto
// il form:
//   - toolbar "Aggiungi articolo"     -> AGGIUNTA (articolo libero)
//   - kebab riga DA_LISTINO "Mod.prezzo" -> OVERRIDE (articolo precompilato)
//   - kebab riga DA_LISTINO "Escludi"  -> ESCLUSIONE (one-click, salvataggio diretto)
// Il form mostra il tipo come Tag readonly (sia CREATE che EDIT), niente
// piu' ambiguita' "che tipo voglio creare?". Default AGGIUNTA: l'azione
// toolbar e' il punto di ingresso piu' generico.
function defaultForm(overrides = {}) {
  const tipo = overrides.tipo_erogazione || TIPO_EROGAZIONE.CANONE
  return {
    articolo_id: null,
    articolo_obj: null,
    tipo_eccezione: TIPO_ECCEZIONE.AGGIUNTA,
    tipo_erogazione: tipo,
    // Refactor 2026-05-19: fonte derivata dalla matrice in base al tipo
    // (default = FISSA per CANONE/UNA_TANTUM). Il BE applica lo stesso
    // default se assente (defense-in-depth), ma pre-compilare in UI
    // rende esplicita la scelta predefinita all'utente.
    fonte_quantita_attesa: _defaultFontePerTipo(tipo),
    prezzo_unitario: null,
    qta_operativa: 1,
    uom_operativa_id: null,
    ordine: 10,
    ...overrides,
  }
}

// Reset stato componenti BoM: chiamato da `closeForm` e dagli ingressi
// CREATE (`onAggiungiArticolo`, `onModificaPrezzo`).
// Tiene insieme `articoloObj` + Dialog state per evitare drift.
function resetComponentiState() {
  articoloObj.value = null
  resetComponentiDialog()
  selectedRowComponenti.value = []
}

// === Lifecycle ===
// Righe e contesto pricing li legge la lista quando il padre e' completo
// (`useDrawerTabLista`): qui solo il form, che all'apertura riparte chiuso.
watch(() => props.visible, (v) => {
  if (v) {
    closeForm()
  } else {
    contestoPricing.value = null
  }
})

// Refactor 2026-05-19: reset di `fonte_quantita_attesa` al cambio
// `tipo_erogazione` SOLO se la combo nuova diventa vietata
// (decisione 3 della sessione 2026-05-19, speculare al trigger DB
// trg_contratti_righe_a10_default_fonte_qta_ins_upd).
// Preserva la scelta utente quando possibile, applica il default
// del nuovo tipo solo quando necessario.
watch(() => form.value?.tipo_erogazione, (nuovoTipo, vecchioTipo) => {
  if (!nuovoTipo || nuovoTipo === vecchioTipo) return
  const fontiValide = _fontiPerTipo(nuovoTipo).map(f => f.value)
  if (!fontiValide.includes(form.value.fonte_quantita_attesa)) {
    form.value.fonte_quantita_attesa = _defaultFontePerTipo(nuovoTipo)
  }
})

// === Azioni ===

// Scopo: ingresso CREATE "Aggiungi articolo" (azione toolbar). Articolo
//        libero (autocomplete), tipo_eccezione=AGGIUNTA (articolo fuori-listino).
function onAggiungiArticolo() {
  form.value = defaultForm({ tipo_eccezione: TIPO_ECCEZIONE.AGGIUNTA })
  nuovaRiga()
  rigaListinoAperta.value = null
  resetUomOptions()
  // resetComponentiState azzera anche selectedRowComponenti: articolo nuovo
  // fuori-listino, nessuna composizione sorgente da mostrare. Se composito,
  // i componenti si definiscono via ComponentiDialog (bottone).
  resetComponentiState()
  // Dopo il giro di watch: anche la creazione conta, un campo scritto e' gia'
  // una modifica da non perdere.
  nextTick(fissa)
}

// Scopo: ingresso CREATE "Modifica prezzo" dal click su una riga del listino
//        (verbo SOVRASCRIVI_PREZZO). Pre-compila articolo (immutabile), UoM e prezzo dal
//        listino: l'operatore deve solo cambiare il prezzo. tipo_eccezione
//        derivato = OVERRIDE.
function onModificaPrezzo(row) {
  form.value = defaultForm({
    tipo_eccezione: TIPO_ECCEZIONE.OVERRIDE,
    articolo_id: row.articolo_id,
    articolo_obj: {
      id: row.articolo_id,
      codice: row.articolo_codice,
      descrizione: row.articolo_descrizione,
      is_composito: row.is_composito === true,
      _display: `${row.articolo_codice} — ${row.articolo_descrizione}`,
    },
    // Prezzo iniziale = prezzo listino corrente. L'operatore lo modifica.
    // Number() per InputNumber (Decimal raw potrebbe arrivare come stringa).
    prezzo_unitario: row.prezzo_listino != null ? Number(row.prezzo_listino) : null,
    uom_operativa_id: row.uom_id ?? null,
    qta_operativa: row.qta_operativa != null ? Number(row.qta_operativa) : 1,
  })
  // articoloObj fuori dal form per i computed `isCompositoCorrente` & co.
  articoloObj.value = form.value.articolo_obj
  nuovaRiga()
  rigaListinoAperta.value = row.riga_key
  // Carica le UoM operative dell'articolo per popolare uomOptions: senza
  // fetch il Select UoM mostrerebbe vuoto anche con uom_operativa_id
  // pre-selezionato (PrimeVue richiede che il valore sia nelle options).
  // Pattern identico a `_onEditRigaPersistita` per righe OVERRIDE gia' esistenti.
  resetComponentiState()
  // Composizione del bundle DA_LISTINO da mostrare read-only inline (i figli
  // del listino non sono persistiti in contratti_righe_componenti, quindi
  // l'api-list del ComponentiPanel sarebbe vuota). DOPO resetComponentiState
  // che azzera selectedRowComponenti. `resetComponentiState` azzera anche
  // articoloObj: per onModificaPrezzo questo e' voluto (impedisce l'auto-open
  // della ComponentiDialog), e il blocco read-only si basa su
  // selectedRowComponenti, non su articoloObj.
  selectedRowComponenti.value = rowComponenti(row)
  loadUomPerArticolo(row.articolo_id)
  nextTick(fissa)
}

// Scopo: azione one-click "Escludi" dal menu di una riga del listino. Dialog
//        di conferma + salvataggio diretto come ESCLUSIONE (prezzo NULL,
//        UoM dal listino). Niente form: la sola scelta dell'operatore e' SI/NO.
function onEscludi(row) {
  confirmAction({
    header: t('vendite.contratti.escludi_dialog_titolo'),
    message: t('vendite.contratti.escludi_dialog_messaggio', { articolo: etichettaRiga(row) }),
    acceptLabel: t('vendite.contratti.escludi_dialog_conferma'),
    danger: true,
    onAccept: async () => {
      const payload = {
        articolo_id: row.articolo_id,
        tipo_eccezione: TIPO_ECCEZIONE.ESCLUSIONE,
        prezzo_unitario: null,  // vincolo BE
        uom_operativa_id: row.uom_id ?? null,
        qta_operativa: '1',
        tipo_erogazione: null,
      }
      const result = await execute(
        () => store.addRiga(props.contrattoId, payload),
        { successMessage: t('vendite.contratti.articolo_escluso') },
      )
      if (result !== null) await rileggiRighe()
    },
  })
}

// Scopo: handler unificato click di riga (allineamento UX standard del progetto
//        — frontend-standards §"Pattern lista": modifica = click riga, kebab
//        riservato ad azioni secondarie). Il click e' il verbo che la riga
//        ammette (colonna `azioni` del DB), non una scelta per origine:
//        - readonly: no-op
//        - SOVRASCRIVI_PREZZO (riga del listino): apre il form pre-compilato
//          come OVERRIDE (delega a onModificaPrezzo). Muta un prezzo, quindi
//          vuole lo stesso permesso di «Nuovo» ed «Escludi»: senza, il click
//          non apre un form che il backend rifiuterebbe (403)
//        - MODIFICA (riga salvata: OVERRIDE/AGGIUNTA/ESCLUSIONE): apre l'edit
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

// Scopo: apertura form EDIT per righe persistite (override/aggiunta/esclusione).
//        Estratto da onRowClick per non duplicare la logica di restore form.
function _onEditRigaPersistita(r) {
  // `apriRiga` apre la modifica (l'id lo deriva `rigaEditId`) e, se un'altra
  // riga e' aperta e modificata, prima chiede: il riempimento sta in `poi`.
  apriRiga(r, () => {
    rigaListinoAperta.value = null
    form.value = {
      articolo_id: r.articolo_id,
      articolo_obj: { id: r.articolo_id, codice: r.articolo_codice, descrizione: r.articolo_descrizione, _display: `${r.articolo_codice} — ${r.articolo_descrizione}` },
      // tipo_eccezione: immutabile in EDIT (refactor 2026-05-15). Mostrato
      // come Tag readonly nel template form. Fallback OVERRIDE per righe
      // legacy che non avevano ancora il campo (transitorio).
      tipo_eccezione: r.tipo_eccezione || TIPO_ECCEZIONE.OVERRIDE,
      tipo_erogazione: r.tipo_erogazione || TIPO_EROGAZIONE.CANONE,
      // Refactor 2026-05-19: fonte_quantita_attesa NOT NULL post-migration
      // 20260519-05. Fallback dal default della matrice solo per righe legacy
      // che non avessero ancora il campo (transitorio, non dovrebbe accadere).
      fonte_quantita_attesa: r.fonte_quantita_attesa
        || _defaultFontePerTipo(r.tipo_erogazione || TIPO_EROGAZIONE.CANONE),
      // Il prezzo scritto sulla riga di `contratti_righe` (NULL su una
      // ESCLUSIONE).
      prezzo_unitario: r.override_prezzo != null ? Number(r.override_prezzo) : null,
      qta_operativa: r.qta_operativa != null ? Number(r.qta_operativa) : 1,
      // ⭐ UdM e ordine COSI' COME SONO SCRITTI sulla riga (§9.11, R-D2):
      //    il form li rimanda al PATCH. Fino al 2026-10-04 la sorgente non li
      //    portava e il form ripiegava sull'UdM della riga di listino e su un
      //    ordine 10 — il primo «Salva» cambiava UdM e azzerava l'ordine, in
      //    silenzio. NULL resta NULL: l'UdM manca solo su una riga senza
      //    quantita' (e vale la base dell'articolo, regola del DB), e un ordine
      //    NULL il backend non lo tocca.
      uom_operativa_id: r.uom_operativa_id ?? null,
      ordine: r.ordine ?? null,
    }
    // Modello unificato BoM 2026-05-13: in EDIT articoloObj porta is_composito
    // se disponibile dalla riga (proiezione BE denormalizzata; fallback false
    // se non esposto). Driver visibilita' ComponentiPanel sotto il form.
    articoloObj.value = {
      id: r.articolo_id,
      codice: r.articolo_codice,
      descrizione: r.articolo_descrizione,
      is_composito: r.is_composito === true,
    }
    // EDIT: chiudi ogni Dialog stantia, il pannello sotto e' l'entrypoint
    // per modificare i componenti persistiti (no Dialog).
    resetComponentiDialog()
    // EDIT riga persistita: i componenti arrivano dal ComponentiPanel via
    // api-list (persistiti). Niente blocco read-only da preview.
    selectedRowComponenti.value = []
    // Edit con UoM pre-popolata dalla riga: niente autopick, solo fetch.
    loadUomPerArticolo(r.articolo_id)
    nextTick(fissa)
  })
}

function onArticoloSelected(item) {
  form.value.articolo_id = item?.id || null
  form.value.uom_operativa_id = null
  // Modello unificato BoM 2026-05-13: snapshot articolo (incluso flag
  // `is_composito` esposto dal lookup) per detection ComponentiDialog
  // post pickBase UoM nel watch sopra.
  articoloObj.value = item || null
  // Cambio articolo: reset stato Dialog (payload + key auto-open) per
  // consentire la riapertura sul nuovo articolo.
  resetComponentiDialog()
  // Cambio articolo in form aperto: autopick base.
  caricaUomConPickBase(item?.id)
}

function closeForm() {
  chiudiForm()
  rigaListinoAperta.value = null
  form.value = {}
  resetUomOptions()
  resetComponentiState()
}

// === Validazione ===
const canSave = computed(() => {
  if (isReadonly.value) return false
  if (!formMode.value) return false
  if (!form.value.articolo_id) return false
  // L'UdM e' la misura della QUANTITA': obbligatoria dove la riga ha una
  // quantita' (fonte FISSA). Una riga senza quantita' puo' non averla
  // (`contratti_righe.uom_operativa_id` nullable: vale la base dell'articolo),
  // e il form non deve inventarla per farla salvare (§9.11).
  if (form.value.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA
      && !form.value.uom_operativa_id) return false
  // Refactor 2026-05-19: fonte_quantita_attesa NOT NULL (CHECK DB).
  // Per FISSA serve qta_operativa valorizzata e diversa da zero (CHECK DB
  // `qta_operativa <> 0`: negativi ammessi, es. resi/note credito); per le
  // altre 4 fonti la quantita arriva downstream (manuale/timesheet/letture)
  // o dal trigger DB (derivata_componenti).
  if (!form.value.fonte_quantita_attesa) return false
  if (form.value.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA
      && (form.value.qta_operativa == null || Number(form.value.qta_operativa) === 0)) {
    return false
  }
  // Refactor modalita 2026-05-15: coerenza prezzo_unitario / tipo_eccezione
  // (specchio del check BE _build_data_riga):
  //   - ESCLUSIONE: prezzo NULL ammesso (l'articolo non e' disponibile)
  //   - OVERRIDE / AGGIUNTA: prezzo obbligatorio (e' il prezzo finale),
  //     EXCEPT articoli compositi dove il prezzo padre = SUM(componenti)
  //     viene popolato dal trigger DB post-init.
  const tipo = form.value.tipo_eccezione
  const prezzoMancante = form.value.prezzo_unitario == null
    || form.value.prezzo_unitario === ''
  if (tipo !== TIPO_ECCEZIONE.ESCLUSIONE
      && !articoloObj.value?.is_composito
      && prezzoMancante) return false
  // Modello unificato BoM 2026-05-13: in CREATE su articolo composito,
  // blocca il save finche' la ComponentiDialog non e' stata confermata
  // almeno una volta (componentiPayload != null). Se l'operatore annulla
  // resta bloccato — deve riaprire e confermare.
  if (showComponentiDialog.value && componentiPayload.value == null) return false
  return true
})

const formTitle = computed(() => {
  if (formMode.value === 'create') return t('vendite.contratti.nuova_riga')
  if (formMode.value === 'edit') return t('vendite.contratti.modifica_riga')
  return ''
})

// === Salvataggio ===

// Scopo: centralizza la costruzione del payload usato da onSave e da
//        onRichiediApprovazione. `extra` permette di iniettare il flag
//        opt-in `richiesta_approvazione: true` per il retry workflow L3
//        senza duplicare la build.
function buildRigaPayload(extra = {}) {
  const f = form.value
  // Refactor 2026-05-19: `qta_operativa` inviata solo per fonte FISSA.
  // Per le altre fonti (downstream o derivata) il BE forza NULL via
  // `_apply_fonte_quantita_logic`; inviare un valore qui sarebbe
  // semanticamente fuorviante (la fonte e' il driver).
  const isFissa = f.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA
  const payload = {
    tipo_erogazione: f.tipo_erogazione || null,
    fonte_quantita_attesa: f.fonte_quantita_attesa || null,
    prezzo_unitario: f.prezzo_unitario != null ? String(f.prezzo_unitario) : null,
    qta_operativa: (isFissa && f.qta_operativa != null) ? String(f.qta_operativa) : null,
    uom_operativa_id: f.uom_operativa_id || null,
    ordine: f.ordine != null ? Number(f.ordine) : null,
    ...extra,
  }
  if (formMode.value === 'create') {
    payload.articolo_id = f.articolo_id
    payload.tipo_eccezione = f.tipo_eccezione || TIPO_ECCEZIONE.OVERRIDE
    // ESCLUSIONE: BE rifiuta prezzo non-null. Forziamo null per safety.
    if (payload.tipo_eccezione === TIPO_ECCEZIONE.ESCLUSIONE) {
      payload.prezzo_unitario = null
    }
    // Modello unificato BoM 2026-05-13: includi `componenti_overrides`
    // se l'articolo e' composito e la Dialog ha prodotto overrides delta.
    if (articoloObj.value?.is_composito === true
        && componentiPayload.value?.overrides) {
      payload.componenti_overrides = componentiPayload.value.overrides
    }
  }
  return payload
}

function submitRiga(payload) {
  return formMode.value === 'create'
    ? store.addRiga(props.contrattoId, payload)
    : store.updateRiga(props.contrattoId, rigaEditId.value, payload)
}

// Save + richiedi-approvazione con gate L2 via BB condiviso (B12, regola del 2).
// Side-effect di successo: rilettura delle righe + changed + close.
const { save: onSave, richiediApprovazione: onRichiediApprovazione } = useL2SaveFlow({
  persist: submitRiga,
  buildPayload: buildRigaPayload,
  onSuccess: async () => {
    await rileggiRighe()
    closeForm()
  },
  messages: {
    success: () => (formMode.value === 'create' ? t('vendite.contratti.riga_creata') : t('vendite.contratti.riga_salvata')),
    approvalRequested: t('vendite.contratti.richiesta_approvazione_inviata'),
    error: t('vendite.contratti.errore_generico'),
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

// Scopo: cancella la riga di `contratti_righe` dietro la riga di lista (il
//        suo `override_riga_id`) e rilegge. E' lo stesso gesto per «rimuovi»
//        e per i due «ripristina»: cambia solo cio' che si dice all'operatore.
async function cancellaRiga(r, successMessage) {
  const rigaId = r.override_riga_id
  const result = await execute(
    () => store.deleteRiga(props.contrattoId, rigaId),
    { successMessage },
  )
  if (result === null) return
  // Se stavo modificando questa riga, chiudi il form.
  if (rigaEditId.value === rigaId) closeForm()
  await rileggiRighe()
}

// AGGIUNTA: "Elimina" semanticamente corretto — l'articolo non e' nel
// listino, sparisce davvero dal contratto.
function onDelete(r) {
  confirmDelete(
    r.articolo_codice || r.articolo_descrizione || `#${r.override_riga_id}`,
    () => cancellaRiga(r, t('vendite.contratti.riga_eliminata')),
  )
}

// Scopo: ripristino eccezione (refactor UX 2026-05-19). Stessa azione DB di
//        onDelete (cancella la riga `contratti_righe`), ma con messaggio
//        parlante che spieghi il vero effetto: l'articolo non viene rimosso
//        dal contratto, torna al comportamento del listino. Riusato sia per
//        OVERRIDE ("Ripristina prezzo di listino") sia per ESCLUSIONE
//        ("Ripristina articolo nel contratto"): il backend e' identico, la
//        differenza e' solo il testo del confirm (`prefix` delle chiavi).
function onRipristina(r, prefix) {
  confirmAction({
    header: t(`vendite.contratti.${prefix}_dialog_titolo`),
    message: t(`vendite.contratti.${prefix}_dialog_messaggio`, { articolo: etichettaRiga(r) }),
    acceptLabel: t(`vendite.contratti.${prefix}_dialog_conferma`),
    danger: false,
    onAccept: () => cancellaRiga(r, t('vendite.contratti.riga_ripristinata')),
  })
}

// L'Annulla del form inline chiude solo il form, chiedendo se ci sono
// modifiche. Le uscite dal drawer (X, ESC, clic fuori, «Chiudi») passano da
// AppDrawer con la stessa conferma (`conferma-uscita`).
const annullaForm = () => chiudiConConferma(closeForm)

// Scopo: le voci del menu di riga, una per VERBO della colonna `azioni`.
//        ⭐ Quali verbi valgono per la riga lo dice il DB (capability di riga,
//        brief-db-liste-righe-documento D-8.4): fino al 2026-10-04 il drawer
//        li decideva per origine, una seconda sede della stessa regola.
//        SOVRASCRIVI_PREZZO e MODIFICA non sono qui: sono il click sulla riga
//        (frontend-standards §"Pattern lista": modifica = click riga, kebab
//        riservato ad azioni secondarie).
//   - ESCLUDI (riga del listino): one-click ESCLUSIONE con conferma. Spento
//     col motivo quando il DB lo rifiuterebbe (`escludi_blocco_codice`: lo
//     stesso predicato del guard, es. un componente di un bundle del listino).
//   - RIPRISTINA_LISTINO (OVERRIDE): DELETE → torna al prezzo di listino.
//   - RIPRISTINA_ARTICOLO (ESCLUSIONE): DELETE → l'articolo torna disponibile.
//   - RIMUOVI (AGGIUNTA): DELETE → l'articolo sparisce dal contratto.
// ⚠️ Un verbo nuovo del DB senza voce qui non compare: e' un'azione che il
//    drawer non sa ancora fare, non una da inventare.
const VOCI_MENU_RIGA = {
  [AZIONE_RIGA_CONTRATTO.ESCLUDI]: (r) => ({
    key: 'escludi',
    label: t('vendite.contratti.azione_escludi'),
    icon: MANAGE_ICONS.ESCLUDI,
    severity: 'warn',
    // Gate L1 (`prezzo_override_manuale`): l'esclusione e' negoziazione.
    visible: canVariarePrezzi.value,
    disabled: !!r.escludi_blocco_codice,
    tooltip: r.escludi_blocco_codice
      ? t(`vendite.contratti.escludi_blocco.${r.escludi_blocco_codice.toLowerCase()}`)
      : '',
    command: () => onEscludi(r),
  }),
  [AZIONE_RIGA_CONTRATTO.RIPRISTINA_LISTINO]: (r) => ({
    key: 'ripristina-listino',
    label: t('vendite.contratti.azione_ripristina_listino'),
    icon: MANAGE_ICONS.RIPRISTINA_LISTINO,
    severity: 'secondary',
    command: () => onRipristina(r, 'ripristina_listino'),
  }),
  [AZIONE_RIGA_CONTRATTO.RIPRISTINA_ARTICOLO]: (r) => ({
    key: 'ripristina-articolo',
    label: t('vendite.contratti.azione_ripristina_articolo'),
    icon: MANAGE_ICONS.RIPRISTINA_LISTINO,
    severity: 'secondary',
    command: () => onRipristina(r, 'ripristina_articolo'),
  }),
  [AZIONE_RIGA_CONTRATTO.RIMUOVI]: (r) => ({
    key: 'rimuovi-aggiunta',
    label: t('vendite.contratti.azione_rimuovi_aggiunta'),
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

// Scopo: severity Tag per origine riga (cella `origine` della lista).
// Distinzione visiva delle 4 origini: DA_LISTINO neutra (preview), OVERRIDE info (prezzo
// personalizzato), AGGIUNTA success (articolo aggiunto al contratto),
// ESCLUSIONE warn (articolo rimosso dal listino).
function origineSeverity(origine) {
  if (origine === TIPO_ECCEZIONE.OVERRIDE) return 'info'
  if (origine === TIPO_ECCEZIONE.AGGIUNTA) return 'success'
  if (origine === TIPO_ECCEZIONE.ESCLUSIONE) return 'warn'
  if (origine === TIPO_ECCEZIONE.DA_LISTINO) return 'secondary'
  return null
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="props.visible"
    :title="t('vendite.contratti.drawer_righe_titolo')"
    :icon="MANAGE_ICONS.RIGHE"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.WIDE_PLUS"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="formMode ? 'nessuno' : 'chiudi'"
    @update:visible="(v) => emit('update:visible', v)"
  >

    <!-- === Intestazione contesto contratto (BB DrawerContextHeader) === -->
    <DrawerContextHeader
      :tag-value="contrattoNumero"
      :items="[
        { label: t('vendite.contratti.col_ba'), value: contrattoCliente },
        { label: t('vendite.contratti.col_valido_dal'), value: displayDate(contrattoValidoDal) },
        { label: t('vendite.contratti.col_valido_al'), value: contrattoValidoAl ? displayDate(contrattoValidoAl) : '—' },
      ]">
      <template #status>
        <Tag v-if="contrattoStatoCodice"
          :value="contrattoStatoDescrizione"
          :severity="statoContrattoSeverity(contrattoStatoCodice)" />
      </template>
    </DrawerContextHeader>

    <!-- Banner contesto pricing (refactor modalita 2026-05-15, FE 2.2):
         mostra forma derivata + listino + versione fissata (post-attivazione)
         o corrente (DRAFT) + categoria cliente. Mutuato dal pattern preventivi. -->
    <Message v-if="contestoPricing"
      :severity="isSenzaListino ? 'warn' : 'info'"
      :closable="false" size="small">
      <div>
        <strong>{{ t(`vendite.contratti.forma_${formaEffettiva}_descrizione`) }}</strong>
      </div>
      <div v-if="contestoPricing.listino_codice">
        {{ t('vendite.contratti.contesto_listino', {
          codice: contestoPricing.listino_codice,
          versione: contestoPricing.listino_versione_codice || '—',
        }) }}
        <Tag v-if="contestoPricing.listino_versione_fissata"
             :value="t('vendite.contratti.contesto_versione_fissata')"
             severity="success" class="ml-05" />
        <!-- Drift warning: il contratto e' fissato a una versione listino
             diversa da quella attualmente ATTIVA sul listino. Tag
             informativo, no blocco: i prezzi restano calcolati sulla
             fissata per design (snapshot post-attivazione). -->
        <Tag v-if="contestoPricing.drift_versione_listino"
             :value="t('vendite.contratti.contesto_drift_versione', {
               versione_corrente: contestoPricing.listino_versione_corrente_codice,
             })"
             severity="warn" class="ml-05"
             v-tooltip.top="t('vendite.contratti.contesto_drift_versione_tooltip', {
               versione_corrente: contestoPricing.listino_versione_corrente_codice,
               versione_fissata: contestoPricing.listino_versione_codice,
             })" />
      </div>
      <div v-if="contestoPricing.tipo_variazione_globale">
        {{ t('vendite.contratti.contesto_variazione', {
          tipo: contestoPricing.tipo_variazione_globale,
          valore: contestoPricing.valore_variazione_globale,
        }) }}
      </div>
      <div v-if="contestoPricing.categoria_cliente_codice">
        {{ t('vendite.contratti.contesto_categoria', {
          codice: contestoPricing.categoria_cliente_codice,
        }) }}
      </div>
    </Message>

    <!-- Avviso "senza_listino": tutte le righe AGGIUNTA, prezzo obbligatorio. -->
    <Message v-if="isSenzaListino && !contestoPricing"
             severity="warn" :closable="false" size="small">
      {{ t('vendite.contratti.righe_senza_listino_warn') }}
    </Message>

    <!-- Avviso: listino associato ma senza versione operativa oggi.
         La lista ha le sole eccezioni, legittimamente: l'operatore deve
         attivare una versione del listino prima che il pricing sia calcolato. -->
    <Message v-if="listinoSenzaVersione"
      severity="warn" :closable="false" size="small">
      {{ t('vendite.contratti.preview_listino_senza_versione', {
        codice: contestoPricing.listino_codice || ''
      }) }}
    </Message>

    <!-- === MASTER: la lista `vendite.contratto_righe` ===
         Colonne dal catalogo, ricerca ed export dal backend, chiave `riga_key`
         dal DB. ⛔ «Non sono riuscito a leggere le righe» non e' «non ce ne
         sono»: a lista vuota la tabella mostrerebbe lo stesso stato. -->
    <Message v-if="righeStore.erroreCaricamento" severity="warn" :closable="false" size="small">
      {{ t('common.righe_non_lette') }}
    </Message>
    <DrawerTabLista
      ref="listaRef"
      codice="vendite.contratto_righe"
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
          :placeholder="t('vendite.contratti.filtro_articolo_placeholder')" />
      </template>

      <template #cell-origine="{ data }">
        <Tag v-if="data.origine"
          :value="t(`vendite.contratti.origine_${data.origine.toLowerCase()}`)"
          :severity="origineSeverity(data.origine)" />
      </template>

      <!-- I componenti di un bundle, nella riga espandibile: arrivano gia'
           aggregati nel jsonb `componenti` della funzione, tanto per i bundle
           del listino quanto per le aggiunte. `ComponentiPanel` in modalita'
           data-driven (`initialData`): niente fetch. -->
      <template #row-expansion="{ data }">
        <div v-if="hasBundleComponenti(data)" class="contratti-componenti-espansi">
          <ComponentiPanel
            :initial-data="rowComponenti(data)"
            i18n-prefix="vendite.componenti.panel" />
        </div>
      </template>

      <!-- In sola lettura (contratto fuori bozza, o permesso LETTURA) nessuna
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
      <div class="app-drawer-section">
        <h4>{{ formTitle }}</h4>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_articolo') }} *</label>
          <!-- Refactor FE 2.2 Opzione C (2026-05-18): l'articolo e' libero
               SOLO per "Aggiungi articolo" (AGGIUNTA fuori-listino). Per
               "Modifica prezzo" (OVERRIDE) e in EDIT e' precompilato e
               immutabile — il flusso ha gia' identificato l'articolo via
               click sulla riga DA_LISTINO. -->
          <ArticoloLookup
            v-model="form.articolo_obj"
            @update:modelValue="onArticoloSelected"
            :disabled="formMode === 'edit' || form.tipo_eccezione !== TIPO_ECCEZIONE.AGGIUNTA"
            :filtri="{ soloComponenti: 'escludi' }"
            :placeholder="t('vendite.contratti.select_articolo')"
          />
        </div>
        <div class="form-field">
          <!-- Refactor FE 2.2 Opzione C (2026-05-18): tipo_eccezione non
               e' piu' una scelta utente. Deriva dall'azione che ha aperto
               il form: toolbar->AGGIUNTA, kebab "Modifica prezzo"->OVERRIDE.
               ESCLUSIONE non passa dal form (one-click via kebab+conferma).
               Mostrato come Tag readonly sia CREATE che EDIT per
               trasparenza UX. -->
          <label>{{ t('vendite.contratti.field_tipo_eccezione') }}</label>
          <div>
            <Tag :value="t(`vendite.contratti.tipo_eccezione_${form.tipo_eccezione}`)"
              severity="secondary" />
          </div>
        </div>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <!-- Obbligatoria solo dove la riga ha una quantita' (fonte FISSA):
               la stessa regola di `canSave`. -->
          <label>{{ t('vendite.contratti.field_uom') }}<span v-if="showQtaOperativa"> *</span></label>
          <Select v-model="form.uom_operativa_id"
            :options="uomOptions"
            option-value="uom_id"
            :option-label="uomLabel"
            :placeholder="form.articolo_id ? t('vendite.contratti.select_uom') : t('vendite.contratti.uom_select_articolo_first')"
            :disabled="!form.articolo_id || uomLoading"
            :loading="uomLoading"
            />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_tipo_erogazione') }}</label>
          <Select v-model="form.tipo_erogazione" :options="tipoErogazioneOptions"
            option-label="label" option-value="value" />
        </div>
      </div>

      <!-- Refactor 2026-05-19: Select fonte_quantita_attesa.
           Le 5 fonti sono filtrate per tipo_erogazione (CHECK DB
           chk_contrighe_coerenza_fonte_erogazione vieta le 7 combinazioni
           incoerenti — non appaiono nelle opzioni). Tooltip "uso atipico"
           sulle combinazioni rare (🟡 nella matrice). -->
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_fonte_quantita_attesa') }} *</label>
          <Select v-model="form.fonte_quantita_attesa"
            :options="fonteQuantitaOptions"
            option-label="label" option-value="value"
            :placeholder="t('vendite.contratti.select_fonte_quantita')"
            />
          <small v-if="fonteCorrente?.severity === 'warn'" class="contratti-fonte-uso-atipico">
            <i :class="STATUS_ICONS.INFO" /> {{ t('vendite.contratti.fonte_quantita_uso_atipico') }}
          </small>
        </div>
        <div class="form-field">
          <label>
            {{ t('vendite.contratti.field_prezzo_unitario') }}
            <!-- Obbligatorio per OVERRIDE/AGGIUNTA (default tipo) non
                 composito. ESCLUSIONE = prezzo NULL. -->
            <span v-if="form.tipo_eccezione !== TIPO_ECCEZIONE.ESCLUSIONE && !articoloObj?.is_composito">*</span>
            <Tag v-if="form.tipo_eccezione === TIPO_ECCEZIONE.ESCLUSIONE"
              severity="warn"
              :value="t('vendite.contratti.prezzo_esclusione_n_a')" />
            <Tag v-else-if="articoloObj?.is_composito"
              severity="info"
              :value="t('vendite.componenti.panel.padre_calcolato')"
              v-tooltip.top="t('vendite.componenti.panel.padre_calcolato_tooltip')"
              class="contratti-componenti-padre-tag" />
          </label>
          <InputNumber v-model="form.prezzo_unitario"
            :disabled="articoloObj?.is_composito === true
                       || form.tipo_eccezione === TIPO_ECCEZIONE.ESCLUSIONE"
            :min-fraction-digits="2" :max-fraction-digits="4" showButtons />
        </div>
      </div>

      <!-- Refactor 2026-05-19: Q.ta operativa visibile/obbligatoria solo
           per fonte FISSA. Per le altre 4 fonti il valore vero arriva
           downstream (manuale/timesheet/letture) o e' derivato dal
           trigger DB z90_propaga_qta_componenti (DERIVATA_COMPONENTI).
           Mostriamo un Tag readonly per chiarire all'utente da dove
           arrivera' il valore. -->
      <div class="form-grid-2col">
        <div class="form-field" v-if="showQtaOperativa">
          <label>{{ t('vendite.contratti.field_qta_operativa_fissa') }} *</label>
          <InputNumber v-model="form.qta_operativa"
            :min="0.0001" :min-fraction-digits="0" :max-fraction-digits="4" showButtons />
        </div>
        <div class="form-field" v-else-if="form.fonte_quantita_attesa">
          <label>{{ t('vendite.contratti.field_qta_operativa') }}</label>
          <Tag severity="info"
            :value="t(`vendite.contratti.fonte_quantita_tag_${form.fonte_quantita_attesa.toLowerCase()}`)"
            v-tooltip.top="t('vendite.contratti.fonte_quantita_tag_tooltip')" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_ordine') }}</label>
          <InputNumber v-model="form.ordine" :min="0"
            :invalid="campiErrati.includes('ordine')"
          />
        </div>
      </div>

      <!-- Sezione componenti BoM (modello unificato 2026-05-13).
           CREATE: il payload Dialog viaggia col save riga
           (componenti_overrides). Mostra bottone "Modifica componenti"
           + summary live. EDIT: ComponentiPanel carica i componenti
           persistiti e li espone editabili. -->
      <template v-if="articoloObj?.is_composito">
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
            :documento-id="props.contrattoId"
            :riga-id="rigaEditId"
            :readonly="isReadonly || formMode !== 'edit'"
            :api-list="listContrattoRigaComponenti"
            :api-update="updateContrattoRigaComponente"
            :api-delete="deleteContrattoRigaComponente"
            :tab-entity="TAB_ENTITIES.CONTRATTO"
            @changed="onComponentiPanelChanged" />
        </template>
      </template>

      <!-- Composizione bundle DA_LISTINO (read-only). Mostrata quando si
           apre il form OVERRIDE da una riga preview composita: i figli
           vivono nel listino, non in contratti_righe_componenti, quindi
           l'api-list del pannello sopra sarebbe vuota. Li esponiamo
           data-driven dai dati gia' caricati nella riga, come nelle offerte.
           Indipendente dal blocco `articoloObj?.is_composito` (che in
           onModificaPrezzo resta null per non auto-aprire la Dialog). -->
      <template v-if="selectedRowComponenti.length">
        <div class="app-drawer-section">
          <h4>{{ t('vendite.componenti.panel.section_title') }}</h4>
        </div>
        <ComponentiPanel
          :initial-data="selectedRowComponenti"
          readonly
          i18n-prefix="vendite.componenti.panel" />
      </template>

      <!-- Banner inline L2 (BB condiviso L2ErrorBanner): visibile quando il
           save ha sollevato E_PRICING_SCONTO_ECCESSIVO /
           E_PRICING_MAGGIORAZIONE_ECCESSIVA. CTA "Richiedi approvazione"
           retry-a il save con `richiesta_approvazione=true` (workflow L3). -->
      <L2ErrorBanner
        :error="l2Error"
        :loading="loading"
        :label="t('vendite.contratti.richiedi_approvazione')"
        :label-loading="t('vendite.contratti.richiedi_approvazione_in_corso')"
        :tooltip="t('vendite.contratti.richiedi_approvazione_tooltip')"
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
         prima del save di una riga padre composita. La conferma alimenta
         `componentiPayload`; il save include `componenti_overrides`. -->
    <ComponentiDialog
      v-model:visible="componentiDialogVisible"
      :articolo="articoloObj"
      :documento-id="props.contrattoId"
      :uom-operativa-id="form.uom_operativa_id"
      :quantita="form.qta_operativa"
      :api-preview="previewRigaComponenti"
      :initial-payload="componentiPayload"
      @confirm="onComponentiConfirm" />
  </AppDrawer>
</template>

<style scoped>
.contratti-componenti-padre-tag {
  font-size: 0.65rem;
  margin-left: 0.4rem;
  padding: 0.05rem 0.3rem;
}
.contratti-componenti-espansi {
  padding: 0.25rem 0 0.5rem 2rem;
  background: var(--app-table-stripe-bg);
}
.contratti-componenti-create {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.contratti-componenti-summary {
  color: var(--app-text-muted);
}
.contratti-fonte-uso-atipico {
  display: block;
  margin-top: 0.25rem;
  /* PrimeVue yellow-700 hex come fallback: ne' --app-text-warn ne'
     --p-yellow-700 sono definite nel tema custom; usiamo il pattern
     dei componenti core (var + fallback hex esplicito). */
  color: var(--p-yellow-700, #b45309);
  font-size: 0.8rem;
}

</style>
