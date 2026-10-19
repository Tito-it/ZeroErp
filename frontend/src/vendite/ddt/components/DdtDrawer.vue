<script setup>
// Scopo: Drawer crea/modifica DDT di vendita.
// CREATE: form testata (cliente) con auto-save BOZZA al primo set di campi
//   minimi (cliente) → "edit-evolved" interno (createdId + hasDetail), poi righe
//   inline + campi trasporto.
// EDIT: testata trasporto + righe + componenti BoM + azioni stato (emetti,
//   spedisci, consegna, reso, annulla, push commessa).
// Macchina a stati DRAFT → EMESSO → SPEDITO → CONSEGNATO (→ RESO) + ANNULLATO,
// data-driven (available_actions dal BE). Numero assegnato a EMESSO dal trigger.
// Clone adattato di OrdiniDrawer (§D-4) + riepilogo IVA, PDF (EntityPdfButton)
// e sezione indirizzi (BB condiviso _shared/indirizzi, UX v2).
import { ref, watch, computed, nextTick, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDdtStore } from '../stores/ddt'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useNotify } from '../../../core/composables/useNotify'
import { useInjectReadonly, READONLY_KEY } from '../../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useForzaturaConfermata } from '../../../core/composables/useForzaturaConfermata'
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../../core/composables/useDrawerDetailLoad'
import { useDrawerContentReady } from '../../../core/composables/useDrawerContentReady'
import { useDrawerFormPreserve } from '../../../core/composables/useDrawerFormPreserve'
import { useEmittenteFiscaleField } from '../../../core/composables/useEmittenteFiscaleField'
import { useUtilityDefaultId } from '../../../core/composables/useUtilityDefaultId'
import { useBaFormDefaults } from '../../_shared/baDefaults/useBaFormDefaults'
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { useTestataDocumento } from '../../../core/composables/useTestataDocumento'
import { mapAvailableActionsToDrawerActions } from '../../../core/composables/useDrawerActions'
import { statoDdtSeverity } from '../../../core/utils/severity'
import { CAMPI_FORM_TESTATA_DDT, STATO_DDT } from '../constants'
import { AZIONE_PUSH_COMMESSA } from '../../constants'
import EntityPdfButton from '../../../documenti/components/EntityPdfButton.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { displayDate, toDateString, oggiAziendale, parseIsoDate } from '../../../core/utils/date'
import { createDdt } from '../api/ddtApi'
import { getDdtFormDefaults } from '../../api/formDefaults'
import { useDrawerAutosaveBozza } from '../../../core/composables/useDrawerAutosaveBozza'
import { useRigheDocumento } from '../../../core/composables/useRigheDocumento'
import { ripristinaBillingAccount } from '../../../core/utils/ripristinaLookup'
import { CLIENTE_BA, clienteCambiato } from '../../_shared/cliente/clienteCambiato'
import { DRAWER_WIDTH, MANAGE_ICONS, TAB_ENTITIES } from '../../../core/constants'
import { NAV_ICONS } from '../../../core/navigation'
import AppDrawer from '../../../core/components/AppDrawer.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../../core/components/DrawerActionsBar.vue'
import RiepilogoIvaTable from '../../../core/components/RiepilogoIvaTable.vue'
import DocumentoIndirizziSection from '../../_shared/indirizzi/DocumentoIndirizziSection.vue'
import DocumentoCollegamentiBar from '../../_shared/lineage/DocumentoCollegamentiBar.vue'
import SituazioneMerceBar from '../../_shared/situazioneMerce/SituazioneMerceBar.vue'
import DdtForm from './DdtForm.vue'
import DdtRigheTable from './DdtRigheTable.vue'
import DdtPrelieviSection from './DdtPrelieviSection.vue'
import DdtNoteDrawer from './DdtNoteDrawer.vue'
import DdtResoDialog from './DdtResoDialog.vue'
import DdtEmissioneDialog from './dialogs/DdtEmissioneDialog.vue'
import DocumentoAnnulloLegamiDialog from '../../_shared/annullo/DocumentoAnnulloLegamiDialog.vue'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'

const { t, te } = useI18n()
const store = useDdtStore()
const { execute, loading, campiErrati } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  ddtId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'saved', 'changed', 'cancelled'])
const onClose = useDrawerClose(emit, 'cancelled')
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
// Preserva le modifiche non salvate quando `loadDetail` sostituisce il form
// (BB condiviso con ordini e preventivi). ⚠️ Dichiarato qui, sopra `resetForm`
// e i watch che lo toccano: in questo progetto una var usata da un watch
// immediate e dichiarata dopo ha già prodotto una TDZ silenziosa.
const {
  preserva: preservaForm,
  reset: resetFormPreserve,
  fissa: fissaForm,
  modificato,
  chiudiConConferma,
} = useDrawerFormPreserve(form, { visibile: () => props.visible })

// ⭐ D-13 (2026-10-03, analisi-fe-chrome-drawer): testata E riga aperta,
//    una domanda sola. Fino a quel giorno la fotografia copriva la sola
//    testata, e una riga in compilazione si perdeva uscendo dal drawer. La
//    fotografia della riga la tiene il suo form e arriva dalla tabella-righe.
// Tabella-righe, fotografia unita (testata + riga aperta) e footer secondo lo
// stato: il legame e' del BB `useRigheDocumento` (regola del 2).
const { righeTableRef, onFormAperto, documento, footerDrawer } = useRigheDocumento({
  testata: { modificato, chiudiConConferma },
  modificabile: () => testata.modificabile.value,
  presente: () => hasDetail.value,
})
const modificatoDocumento = documento.modificato
const detail = ref(null)
// Il cliente del DDT: il billing account, o il destinatario senza BA (D-1 di
// brief-db-indirizzi-documento-seguono-il-cliente). Per l'avviso del pannello
// indirizzi prima di Salva (BB `clienteCambiato`).
const CAMPI_CLIENTE_DDT = Object.freeze([...CLIENTE_BA, 'destinatario_soggetto_ruolo_id'])

// Riepilogo IVA aggregato per aliquota (lettura da `vw_ddt_riepilogo_iva_dettaglio`).
// Auto-popolato a ogni loadDetail e ogni `@changed` delle righe: la vista DB
// e' la single source (regola fiscale DPR 633/72 art. 21). Le righe con prezzo
// NULL (DDT solo di trasporto) sono escluse in vista: riepilogo vuoto -> nascosto.
const riepilogoIva = ref([])
// Pannello visibile quando c'e' almeno una riga aggregata. Il footer della
// RiepilogoIvaTable mostra gia' totale imponibile + imposta + totale documento.
const showRiepilogoIva = computed(
  () => Array.isArray(riepilogoIva.value) && riepilogoIva.value.length > 0,
)
const noteDrawerVisible = ref(false)
const resoDialogVisible = ref(false)
// Scopo: si e' chiuso un documento aperto dalla barra collegamenti (passaggi
//        lineage): li' l'operatore puo' aver agito — annullare il DDT di un
//        ordine riapre il residuo e riaccende «Genera DDT» — quindi si
//        rileggono testata (stato, capability) e righe. Chip e situazione
//        merce li rileggono le barre su quel dettaglio nuovo (`:versione`).
//        Le liste in ascolto le ha gia' avvisate lo store del
//        verbo, nel drawer impilato.
async function onDocumentoCollegatoChiuso() {
  await loadDetail()
  righeTableRef.value?.loadRighe()
}

// ⭐ Il cambio di stato e' un gesto CONFERMABILE (D-8 di
//    brief-db-ddt-righe-evase-dall-ordine): l'annullo di una bolla con righe
//    legate a ordini o resi il DB lo rifiuta (`confirm_and_retry`) finche' chi
//    conferma non dichiara quante righe legate ha visto. La domanda la porta a
//    video `DocumentoAnnulloLegamiDialog`; una bolla senza legami passa al primo colpo.
const cambioStato = useForzaturaConfermata()
const { richiestaConferma: domandaAnnullo } = cambioStato

// Scopo: dopo la creazione di un reso, ricarica il detail (residui rendibili,
//        stato), i chip dei collegamenti e il conto della merce.
function onResoCreato() {
  loadDetail()
  // ⭐ La lista DDT dietro: il reso cambia il conto della merce e i transiti.
  // `changed`, non `saved`: dal DDT si continua a lavorare.
  emit('changed')
}
// Scopo: dopo una modifica alle righe (cancellazione, correzione della
//        quantita' evasa), ricarica il detail e le due barre in testata.
// ⚠️ Su un DDT nato da ordine o da reso la riga porta un LEGAME: cancellarla
//    lo ritira (D-3) e correggerla lo sposta (D-2), cioe' cambia cosa resta da
//    spedire e chi e' collegato. Ricaricare solo il detail lasciava la barra
//    merce a mostrare il residuo di prima (rilievo in-app di Tid, 2026-10-11).
//    Stesse due letture di `onResoCreato` e `dopoCambioStato`.
// Prelievi: la sezione e' montata col dettaglio, e alla prima apertura legge da
// se'; dopo, la rilegge `loadDetail` se era gia' montata (righe, causale e
// magazzino cambiano le voci).
const prelieviRef = ref(null)
// Un prelievo cambiato: la testata si rilegge (la capability «Emetti» e il suo
// motivo dipendono dai prelievi), e con lei la sezione.
function onPrelieviChanged() {
  loadDetail()
  emit('changed')
}

function onRigheChanged() {
  loadDetail()
  emit('changed')
}
// Avviso emissione: true quando manca l'indirizzo obbligatorio (CON) —
// alimentato dalla sezione indirizzi, mostrato nel dialog di emissione.
const indirizzoObbligatorioMancante = ref(false)

// Auto-save bozza: in CREATE, appena il cliente (BA) e' valorizzato, il drawer
// crea il DDT in BOZZA e si comporta da "edit-evolved" (righe + azioni stato).
const createdId = ref(null)
const effectiveDdtId = computed(() => createdId.value ?? props.ddtId)
// FE-A: «questo documento vende?». La risposta sta nella causale di trasporto
// (DEC-5 del brief-ddt-righe-senza-prezzo) e ha TRE stati, non due:
//   true  -> vende: una riga senza prezzo blocchera' l'emissione
//   false -> non vende (conto visione, ri-consegna): il prezzo assente e' normale
//   null  -> causale non ancora scelta
// Il confronto e' `=== true` di proposito: `null` deve comportarsi come «non
// pretendere il prezzo», non come «vende». Il BE non fa COALESCE apposta per
// lasciare qui la distinzione.
const causaleFatturabile = computed(
  () => detail.value?.causale_trasporto_fatturabile === true,
)

const hasDetail = computed(() => detail.value !== null)

// Readonly cumulativo: prop esplicita OR readonly area iniettato dal parent OR
// stato post-DRAFT (modifiche libere solo in bozza). Gate di stato su
// `hasDetail` (NON su mode==='edit'): in CREATE "edit-evolved" un'eventuale
// transizione fuori DRAFT deve bloccare subito il form. Le azioni di stato
// restano cliccabili in readonly grazie a `app-escape` di DrawerActionsBar.
const parentReadonly = useInjectReadonly()
const isReadonly = computed(
  () => props.readonly
    || parentReadonly.value
    || (detail.value !== null
        && detail.value.stato_codice_interno !== STATO_DDT.DRAFT),
)
provide(READONLY_KEY, isReadonly)

// Azione "Genera reso" (dialog dedicata): solo su DDT CONSEGNATO — non si
// rende cio' che non e' stato consegnato. E' il percorso per aprire un reso;
// il flip del DDT a RESO resta automatico lato DB alla conferma di un reso
// TOTALE (fn_conferma_reso), mai manuale.
const showResoAction = computed(
  () => detail.value?.stato_codice_interno === STATO_DDT.CONSEGNATO,
)

// Capability data-driven dal detail BE (script.fn_available_actions_ddt):
// availableActions + can_edit_testata + non_editable_fields. Composable
// centralizzato, uniforme a Ordini/Preventivi/Contratti.
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })

const capabilities = caps.capabilities
const availableActions = caps.availableActions
const canEditRighe = computed(() => caps.flag('can_edit_righe'))
// Push a commessa: la capability include l'azione in `available_actions` solo
// quando e' eseguibile; quando non lo e', espone il motivo nei campi
// can_push_commessa_reason/_key. Presentazione = tooltip su pulsante
// DISABILITATO, non banner (Decisione D, brief-db-ddt-reason-push-catch-all §3):
// molte cause sono PERMANENTI — fattura_da_ordine e' il caso default — e un
// banner sempre visibile sarebbe rumore perpetuo. L'entry disabled la
// sintetizza il BB (`azioneNegata`), condivisa con OrdiniDrawer.
const pushCommessaDisabledAction = computed(() => caps.azioneNegata('can_push_commessa', {
  ...AZIONE_PUSH_COMMESSA,
  label_key: 'vendite.ddt.azione_push_commessa',
}))

// La testata dopo la bozza: quali campi del form si cambiano, dalla capability
// (brief-db-testata-dopo-emissione, R-FE-3, D-0/D-1). A bolla emessa restano
// aperti trasporto e tracciamento: il form esce dal corpo protetto.
const isReadonlyPuro = computed(() => props.readonly || parentReadonly.value)
const testata = useTestataDocumento({
  caps,
  campi: CAMPI_FORM_TESTATA_DDT,
  readonlyPuro: () => isReadonlyPuro.value,
  // Il documento esiste: in EDIT anche prima che arrivi il dettaglio, cosi'
  // la capability ancora vuota tiene il form fermo (fail-closed).
  presente: () => isEdit.value || hasDetail.value,
  corpoProtetto: () => isReadonly.value,
})

// Default emittente fiscale: operatore → id profilo; admin globale → null
// (sceglie via EmittenteFiscaleField in modalita' Select). Uniformato a
// ordini/preventivi (decisione Tid 2026-07-13): l'emittente e' legato allo
// USER; il fallback dal BA in trgfn_ddt_normalize resta rete di sicurezza.
const { defaultEmittenteId } = useEmittenteFiscaleField()

// Default utility globale (parameter DEFAULT_UTILITY): proposto in CREATE.
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

// Deferimento contenuto: i LookupSelect/AutoComplete montano dopo l'animazione
// di apertura (pattern feedback_content_ready_after_show).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

function defaultForm() {
  return {
    emittente_fiscale_id: defaultEmittenteId.value ?? null,
    utility_id: utilityDefaultId.value ?? null,
    billing_account_id: null,
    // _obj per BillingAccountLookup (pattern restore lookup ricco).
    billing_account_obj: null,
    // Senza cliente: il terzista o il deposito (col cliente lo scrive il DB).
    destinatario_soggetto_ruolo_id: null,
    destinatario_obj: null,
    valuta_id: null,
    // Corsia di instradamento: default differita (DEFAULT false a DB).
    fatturazione_immediata: false,
    data: oggiAziendale(),
    // Trasporto
    causale_trasporto_id: null,
    aspetto_bene_id: null,
    modalita_addebito_trasporto_id: null,
    vettore_soggetto_ruolo_id: null,
    vettore_obj: null,
    mittente_soggetto_ruolo_id: null,
    mittente_obj: null,
    num_colli: null,
    peso_lordo: null,
    peso_netto: null,
    volume: null,
    targa: null,
    autista: null,
    tracking_code: null,
    // Magazzino (Lotto 3 D-L3-a): vuoto = lo propone il DB alla creazione (il
    // predefinito dell'emittente); l'arrivo solo per la bolla di trasferimento.
    magazzino_id: null,
    magazzino_arrivo_id: null,
  }
}

function resetForm() {
  form.value = defaultForm()
  resetFormPreserve()
  detail.value = null
  createdId.value = null
}

// ⚠️ `loadDetail` SOSTITUISCE il form coi dati del server, ed è chiamata da
// SETTE punti (apertura, auto-save bozza, salvataggio riga via `@changed`,
// cambio stato, azioni): senza il BB `useDrawerFormPreserve` ogni chiamata
// butterebbe via i campi di testata digitati e non ancora salvati.

async function loadDetail(id = null) {
  const targetId = id ?? effectiveDdtId.value
  if (!targetId) return
  const applicaModifiche = preservaForm()
  // La sezione prelievi si rilegge solo se c'era GIA': montata adesso (prima
  // apertura) legge da se', e rileggerla qui sarebbe una seconda richiesta.
  const prelieviGiaMontati = prelieviRef.value != null
  const data = await loadDetailOrClose(() => store.fetchDetail(targetId))
  if (!data) return
  detail.value = data
  form.value = {
    // Emittente fiscale memorizzato (denormalizzato dal detail BE: ragione
    // sociale soggetto + codice via EmittenteFiscaleField :record).
    // Immutabile post-create (whitelist BE update lo esclude).
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    utility_id: data.utility_id ?? null,
    billing_account_id: data.billing_account_id ?? null,
    billing_account_obj: null,  // popolato sotto da ripristinaBillingAccount
    // Restore ricco dalla denominazione denormalizzata della vista, come
    // mittente e vettore.
    destinatario_soggetto_ruolo_id: data.destinatario_soggetto_ruolo_id ?? null,
    destinatario_obj: data.destinatario_soggetto_ruolo_id
      ? { soggetto_ruolo_id: data.destinatario_soggetto_ruolo_id, ragione_sociale_completa: data.destinatario_denominazione }
      : null,
    valuta_id: data.valuta_id ?? null,
    fatturazione_immediata: data.fatturazione_immediata ?? false,
    data: parseIsoDate(data.data),
    // Trasporto
    causale_trasporto_id: data.causale_trasporto_id ?? null,
    aspetto_bene_id: data.aspetto_bene_id ?? null,
    modalita_addebito_trasporto_id: data.modalita_addebito_trasporto_id ?? null,
    // Restore ricco mittente/vettore dalle denominazioni denormalizzate della
    // vista (SoggettoRuoloLookup mostra ragione_sociale_completa senza round-trip).
    vettore_soggetto_ruolo_id: data.vettore_soggetto_ruolo_id ?? null,
    vettore_obj: data.vettore_soggetto_ruolo_id
      ? { soggetto_ruolo_id: data.vettore_soggetto_ruolo_id, ragione_sociale_completa: data.vettore_denominazione }
      : null,
    mittente_soggetto_ruolo_id: data.mittente_soggetto_ruolo_id ?? null,
    mittente_obj: data.mittente_soggetto_ruolo_id
      ? { soggetto_ruolo_id: data.mittente_soggetto_ruolo_id, ragione_sociale_completa: data.mittente_denominazione }
      : null,
    num_colli: data.num_colli ?? null,
    peso_lordo: data.peso_lordo != null ? Number(data.peso_lordo) : null,
    peso_netto: data.peso_netto != null ? Number(data.peso_netto) : null,
    volume: data.volume != null ? Number(data.volume) : null,
    targa: data.targa ?? null,
    autista: data.autista ?? null,
    tracking_code: data.tracking_code ?? null,
    magazzino_id: data.magazzino_id ?? null,
    magazzino_arrivo_id: data.magazzino_arrivo_id ?? null,
  }
  // Fissa la baseline e ripristina il non-salvato che la sostituzione
  // avrebbe cancellato.
  applicaModifiche()
  await nextTick()
  // Il cliente per l'etichetta del lookup (BB `ripristinaBillingAccount`).
  await ripristinaBillingAccount(form.value, data.billing_account_id)
  // Riepilogo IVA: la vista DB ricalcola dalle righe attive valorizzate a ogni
  // mutazione; qui leggiamo lo stato corrente (best-effort).
  await loadRiepilogoIva(targetId)
  if (prelieviGiaMontati) prelieviRef.value?.carica()
}

// Scopo: Carica il riepilogo IVA aggregato (best-effort: in caso di errore il
//        pannello resta vuoto/nascosto, il resto del drawer non e' impattato).
async function loadRiepilogoIva(targetId = null) {
  const id = targetId ?? effectiveDdtId.value
  if (!id) return
  try {
    riepilogoIva.value = await store.loadRiepilogoIva(id)
  } catch {
    riepilogoIva.value = []
  }
}

watch(() => props.visible, async (v) => {
  if (!v) return
  if (isEdit.value) {
    loadDetail()
  } else {
    // CREATE: risolve la utility di default (parameter DEFAULT_UTILITY) PRIMA di
    // resetForm, così defaultForm() la legge. Poi pre-popola la valuta dalla
    // catena EF (resolve_valuta_default lato BE), come ordini/preventivi.
    await loadUtilityDefault()
    resetForm()
    try {
      const res = await getDdtFormDefaults(null)
      const data = res?.data?.data
      if (data && form.value.valuta_id == null && data.valuta_id != null) {
        form.value.valuta_id = data.valuta_id
      }
    } catch {
      // Best-effort: se l'API e' giu' il drawer si apre comunque (valuta vuota).
    }
  }
})

// Al cambio BA in CREATE applica la valuta BA-derived (BA-wins) via BB
// condiviso useBaFormDefaults (guard latest-wins anti-race, come preventivi/
// offerte). Il DDT non ha termini/modalita di pagamento in testata: nessun
// `apply` extra. Se la risposta arriva dopo l'auto-save bozza, il trigger DB
// ha comunque gia' risolto la valuta sul record (fn_get_valuta_id).
const { inCorso: defaultsClienteInCorso } = useBaFormDefaults({ form, isEdit, fetchDefaults: getDdtFormDefaults })

// Costruisce il payload testata (create/update). Numeri e stringhe vuote → null:
// il BE normalizza empty→NULL (empty_to_none). emittente_fiscale_id solo in
// create. ⛔ La utility non si manda: e' una copia del cliente, la scrive il DB
// (qui filtra solo la ricerca). Il destinatario si manda solo SENZA cliente:
// col cliente lo scrive il DB, e al cambio di cliente segue quello nuovo.
function buildTestataPayload({ includeEmittente = false } = {}) {
  const f = form.value
  const payload = {
    billing_account_id: f.billing_account_id || null,
    valuta_id: f.valuta_id || null,
    fatturazione_immediata: !!f.fatturazione_immediata,
    data: f.data ? toDateString(f.data) : null,
    causale_trasporto_id: f.causale_trasporto_id || null,
    aspetto_bene_id: f.aspetto_bene_id || null,
    modalita_addebito_trasporto_id: f.modalita_addebito_trasporto_id || null,
    mittente_soggetto_ruolo_id: f.mittente_soggetto_ruolo_id || null,
    vettore_soggetto_ruolo_id: f.vettore_soggetto_ruolo_id || null,
    num_colli: f.num_colli ?? null,
    peso_lordo: f.peso_lordo ?? null,
    peso_netto: f.peso_netto ?? null,
    volume: f.volume ?? null,
    targa: f.targa || null,
    autista: f.autista || null,
    tracking_code: f.tracking_code || null,
    // Vuoto in creazione = il default del DB (il magazzino predefinito
    // dell'emittente); le regole (stesso emittente, arrivo solo per il
    // trasferimento) le applica il DB.
    magazzino_id: f.magazzino_id || null,
    magazzino_arrivo_id: f.magazzino_arrivo_id || null,
  }
  if (payload.billing_account_id == null) {
    payload.destinatario_soggetto_ruolo_id = f.destinatario_soggetto_ruolo_id || null
  }
  if (includeEmittente) {
    // Opzionale per BE: se omesso (es. admin globale che non sceglie) il
    // trigger DB fa fallback dal billing_account.
    payload.emittente_fiscale_id = f.emittente_fiscale_id || null
  }
  return payload
}

// Auto-save bozza + abbandono bozza orfana via BB condiviso (B13, regola del 2).
// Trigger: cliente (BA) o, senza cliente, destinatario valorizzato in CREATE. `close` e' l'uscita del
// drawer (`conferma-uscita` di AppDrawer); createdId resta ref del drawer.
const { close } = useDrawerAutosaveBozza({
  emit,
  execute,
  loading,
  createdId,
  visible: () => props.visible,
  isEdit: () => isEdit.value,
  contentReady: () => contentReady.value,
  triggerSources: () => [form.value.billing_account_id, form.value.destinatario_soggetto_ruolo_id],
  isReady: ([baId, destinatarioId]) => baId != null || destinatarioId != null,
  createDraftApi: createDdt,
  buildDraftPayload: async () => buildTestataPayload({ includeEmittente: true }),
  tabEntity: TAB_ENTITIES.DDT,
  fetchDetail: (id) => loadDetail(id),
  // Il BB preserva i campi compilati MENTRE la POST di creazione viaggia:
  // senza il form li perderebbe, perche' `loadDetail` sostituisce il form
  // coi dati del server (fix 2026-08-17).
  form,
  deleteDraft: (id) => store.elimina(id),
  righeCountGetter: () => detail.value?.righe_count ?? 0,
  // Uscita con modifiche non salvate: prima si chiede (BB useDrawerFormPreserve).
  confermaUscita: documento.chiudiConConferma,
  messages: {
    bozzaCreata: t('vendite.ddt.bozza_creata'),
    abbandonoTitolo: t('vendite.ddt.abbandono_bozza_titolo'),
    abbandonoMessage: t('vendite.ddt.conferma_abbandono_bozza'),
    abbandonoConferma: t('vendite.ddt.abbandono_bozza_conferma'),
    bozzaEliminata: t('vendite.ddt.bozza_eliminata'),
  },
})

// Finche' arrivano i dati del cliente (BB `useBaFormDefaults`) il Salva
// aspetta: partirebbe un form senza quei dati, presi per scelte dell'operatore.
const canSave = computed(() => {
  if (!testata.modificabile.value) return false
  if (defaultsClienteInCorso.value) return false
  return form.value.billing_account_id != null || form.value.destinatario_soggetto_ruolo_id != null
})

async function handleSave() {
  if (isEdit.value || createdId.value !== null) {
    // UPDATE testata: in bozza tutto, cliente e destinatario compresi (si
    // scelgono in bozza); dopo i soli campi aperti (decide il DB, i bloccati
    // viaggiano invariati e il lock li lascia passare).
    const result = await execute(
      () => store.update(effectiveDdtId.value, buildTestataPayload()),
      { successMessage: t('vendite.ddt.ddt_salvato') },
    )
    if (result !== null) {
      // Salvato: la fotografia e' il form com'e' ora, PRIMA della ricarica —
      // o `preserva` prenderebbe i valori appena salvati per «non salvati» e
      // li rimetterebbe sopra quelli (eventualmente normalizzati) del server.
      fissaForm()
      await loadDetail()
      emit('saved', result)
    }
  } else {
    // Fallback CREATE manuale (auto-save non scattato): chiude dopo create.
    const result = await execute(
      () => store.create(buildTestataPayload({ includeEmittente: true })),
      { successMessage: t('vendite.ddt.ddt_creato') },
    )
    if (result !== null) emit('saved', result)
  }
}

// --- Azioni stato ---

// Dialog emissione DDT: aperto quando l'azione 'emetti' porta a EMESSO
// (assegna numero, gate componenti). Anteprima PDF accompagnatorio + allegati
// via BB DocumentoEmissioneDialog (mirror ordini).
const emissioneDialogVisible = ref(false)
const emissioneLoading = ref(false)

function onEmetti() {
  emissioneDialogVisible.value = true
}

// Scopo: callback @confirm di DdtEmissioneDialog. Riceve i file staged
// dall'utente e chiama store.emetti (POST multipart /emetti/). Se la
// generazione del documento fallisce il BE annulla l'emissione (stato resta
// DRAFT, numero non consumato).
async function handleEmissioneConferma({ files }) {
  emissioneLoading.value = true
  const result = await execute(
    () => store.emetti(effectiveDdtId.value, { allegati: files || [] }),
    { successMessage: t('vendite.ddt.ddt_emesso') },
  )
  emissioneLoading.value = false
  if (result !== null) {
    emissioneDialogVisible.value = false
    // L'emissione e' il momento in cui le partite di merce NASCONO (soglia
    // EMESSO, decisione D1): la barra merce le rilegge su questo dettaglio
    // nuovo (`:versione`), o resterebbe «nessuna merce» fino alla riapertura.
    await loadDetail()
    emit('saved', result)
  }
}

// Push singolo a commessa. Toast differenziato per `report.stato` (l'orchestrator
// risponde 200 anche con esito PARZIALE/ERRORE per riga — gemello ordini).
function onPush() {
  confirmAction({
    header: t('vendite.ddt.azione_push_commessa'),
    message: t('vendite.ddt.push_commessa_messaggio'),
    onAccept: async () => {
      const result = await execute(() => store.push(effectiveDdtId.value))
      if (result === null) return  // errore HTTP gia' gestito da useApiHandler

      const stato = result?.stato
      const pushLogId = result?.push_log_id
      const righe = result?.handlers?.reduce(
        (acc, h) => acc + (h?.created ?? 0) + (h?.updated ?? 0),
        0,
      ) ?? result?.righe_pushable ?? 0

      if (stato === 'COMPLETATO') {
        notify.success(t('vendite.ddt.push_commessa_ok', { righe, push_log_id: pushLogId }))
      } else if (stato === 'PARZIALE') {
        notify.warn(t('vendite.ddt.push_commessa_parziale', { righe, push_log_id: pushLogId }))
      } else if (stato === 'ERRORE') {
        const firstError = result?.handlers?.[0]?.errors?.[0] || t('common.error_generic')
        notify.error(t('vendite.ddt.push_commessa_errore', { primo_errore: firstError }))
      } else if (stato === 'SKIPPED') {
        notify.warn(t('vendite.ddt.push_commessa_skipped'))
      } else {
        notify.success(t('vendite.ddt.push_commessa_ok_generico'))
      }

      if (stato === 'COMPLETATO' || stato === 'PARZIALE') {
        await loadDetail()
        emit('saved', result)
      }
    },
  })
}

// Smista le azioni data-driven (`available_actions`) ai relativi handler.
// emetti/push_commessa hanno flussi dedicati; le altre transizioni
// (spedisci/consegna/reso/annulla) passano dal cambio stato generico.

// Scopo: il nome dello STATO di destinazione per la frase di conferma («Portare
//   il documento nello stato {stato}?»). La descrizione leggibile la sa solo il
//   database (`DRAFT` -> «Bozza», `ALLOCATO` -> «Allocato a magazzino»: non e'
//   derivabile dal codice), quindi arriva dalla capability come
//   `target_state_descrizione`. Finche' il DB non la espone si ripiega sulla
//   label dell'azione — comportamento invariato, nessun testo mancante.
function statoDestinazione(action) {
  return action.target_state_descrizione || t(action.label_key)
}

function onAction(action) {
  if (action.key === 'emetti') { onEmetti(); return }
  if (action.key === 'push_commessa') { onPush(); return }
  if (action.requires_confirm) {
    confirmAction({
      header: t('confirm.cambio_stato_title'),
      message: t('vendite.ddt.conferma_cambio_stato', { stato: statoDestinazione(action) }),
      onAccept: () => eseguiCambioStato(action),
    })
  } else {
    eseguiCambioStato(action)
  }
}

// Transizione di stato generica (target_state dell'azione). Il trigger DB valida
// l'ammissibilita'; qui orchestriamo chiamata + refresh detail. Il primo
// tentativo va SEMPRE senza dichiarazione (`useForzaturaConfermata`).
async function eseguiCambioStato(action) {
  const result = await cambioStato.esegui(
    (dichiarazione) => store.cambiaStato(effectiveDdtId.value, action.target_state, dichiarazione),
    { successMessage: t('vendite.ddt.stato_cambiato') },
  )
  await dopoCambioStato(result)
}

// Scopo: l'operatore ha visto le righe legate e conferma l'annullo: si ripete
//        la chiamata DICHIARANDO quante erano. Se nel frattempo sono cambiate,
//        il DB chiede di nuovo e la finestra si rilegge (domanda nuova).
async function onConfermaAnnullo(dichiarazione) {
  await dopoCambioStato(await cambioStato.conferma(dichiarazione))
}

async function dopoCambioStato(result) {
  if (result !== null) {
    // Il cambio stato sposta i conti della merce (l'ANNULLO rende il documento
    // abortito e le sue partite ESCONO dalla vista) e ritira i legami delle
    // righe con ordini e resi (D-8). Entrambe le barre li rileggono su questo
    // dettaglio nuovo (`:versione`), senza una chiamata qui.
    await loadDetail()
    emit('saved', result)
  }
}

// Azioni del drawer DDT consumate da DrawerActionsBar. Le transizioni di stato
// arrivano data-driven da fn_available_actions_ddt (mapper condiviso); in
// readonly puro (LETTURA/split) sono nascoste.
const drawerActions = computed(() => {
  if (!hasDetail.value) return []
  const readonlyPuro = props.readonly || parentReadonly.value
  const stateActions = mapAvailableActionsToDrawerActions({
    availableActions: [...availableActions.value, ...pushCommessaDisabledAction.value],
    t,
    te,
    onAction,
    readonly: readonlyPuro,
  })
  return [
    ...stateActions,
    // Genera reso: apre la dialog dedicata (righe consegnate con residuo
    // rendibile). Resta visibile anche in readonly puro — la dialog si apre
    // in sola consultazione (footer di sola chiusura).
    ...(showResoAction.value
      ? [{
          key: 'genera-reso',
          kind: 'manage',
          label: t('vendite.ddt.genera_reso'),
          icon: NAV_ICONS.RESI,
          command: () => { resoDialogVisible.value = true },
        }]
      : []),
    {
      key: 'manage-note',
      kind: 'manage',
      label: t('vendite.ddt.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => { noteDrawerVisible.value = true },
    },
  ]
})

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <!-- L'uscita la possiede l'auto-salvataggio della bozza
       (`useDrawerAutosaveBozza`): con una bozza rimasta vuota chiede se
       eliminarla, altrimenti le modifiche non salvate; poi emette lui
       `update:visible` e `cancelled` verso il padre. Per questo
       `conferma-uscita` ignora il `chiudi` del guscio. -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.ddt.ddt')"
    :icon="NAV_ICONS.DDT"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.WIDE_PLUS"
    :modificato="modificatoDocumento"
    :conferma-uscita="() => close()"
    :footer="footerDrawer"
    :footer-readonly="testata.footerReadonly.value"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @after-show="onAfterShow"
    @save="handleSave"
  >

    <!-- Header info: visibile in EDIT classico e in CREATE post auto-save. -->
    <template v-if="hasDetail">
      <DrawerEntityHeader>
        <!-- Numero: "—" finche' il DDT e' in DRAFT (assegnato solo a EMESSO). -->
        <Tag :value="detail.numero || '—'" severity="secondary" />
        <span v-if="detail.data" class="app-drawer-header-muted font-bold">
          {{ displayDate(detail.data) }}
        </span>
        <!-- La provenienza (ordine di evasione) NON e' piu' un chip d'header
             dedicato: e' assorbita dai chip di DocumentoCollegamentiBar sotto
             la barra azioni, dove sta l'origine di TUTTI i domini (2026-07-25).
             Un solo posto, uguale ovunque, invece di un chip speciale del DDT. -->

        <template #status>
          <Tag
            :value="detail.stato_descrizione"
            :severity="statoDdtSeverity(detail.stato_codice_interno)"
          />
        </template>
      </DrawerEntityHeader>

      <DrawerActionsBar :actions="drawerActions" :info-key="capabilities.stato_info_key || ''">
        <template #suffix>
          <!-- Stampa DDT accompagnatorio: anteprima in bozza, gestione
               documenti generati post-emissione. BB EntityPdfButton 1:1. -->
          <EntityPdfButton
            :sorgente-code="SORGENTE_CODES.DDT_VENDITA"
            :entity-id="effectiveDdtId"
            :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
            :pdf="capabilities.pdf"
            i18n-prefix="vendite.ddt.pdf"
            :dialog-title="detail.numero
              ? t('vendite.ddt.pdf.dialog_title', { numero: detail.numero })
              : ''"
          />
        </template>
      </DrawerActionsBar>

      <!-- Collegamenti diretti (pratica + origine + destinazioni di livello 1):
           segnalazione a colpo d'occhio sotto i pulsanti — «Ordine», «1 Reso».
           Il dettaglio (grafo completo) si apre dai chip stessi in dialog.
           `ref` per ricaricare i chip dopo un'azione che li cambia (reso). -->
      <DocumentoCollegamentiBar
        base-path="/vendite/ddt"
        :versione="detail"
        :doc-id="effectiveDdtId"
        @documento-chiuso="onDocumentoCollegatoChiuso"
        :readonly="readonly || parentReadonly" />

      <!-- Situazione merce di QUESTA spedizione: quanto e' uscito, tornato,
           fatturato e cosa resta aperto. La barra sopra dice COSA e'
           collegato, questa COM'E' ANDATA. Sparisce se non c'e' nulla da
           raccontare (un DDT in bozza non ha ancora partite). -->
      <SituazioneMerceBar
        base-path="/vendite/ddt"
        :versione="detail"
        :doc-id="effectiveDdtId"
        :readonly="readonly || parentReadonly" />
    </template>

    <Divider v-if="hasDetail" />

    <!-- Form testata: monta dopo l'animazione drawer per evitare rimbalzo lookup. -->
    <!-- Fuori bozza il form esce dal corpo protetto se ha un campo aperto
         (`useTestataDocumento`): a bolla emessa trasporto e tracciamento. -->
    <div :class="{ 'app-escape': testata.sopraCorpoProtetto.value }">
      <DdtForm
        :campi-errati="campiErrati"
        :form="form" :is-modificabile="testata.modificabile.value"
        :non-editable-fields="testata.campiBloccati.value"
        :record="detail"
        :is-edit="isEdit || createdId !== null" />
    </div>

    <!-- Righe: visibili appena c'e' detail (EDIT classico o CREATE post auto-save). -->
    <template v-if="hasDetail">
      <!-- Sezione indirizzi (UX v2, BB condiviso): solo il default CON,
           avviso se mancante (obbligatorio all'emissione, guard DB),
           pulsante "Indirizzi" che apre il drawer di gestione. -->
      <DocumentoIndirizziSection
        dominio="ddt"
        :doc-id="effectiveDdtId"
        :soggetto-ruolo-id="detail?.destinatario_soggetto_ruolo_id ?? null"
        :istanza-utility-id="detail?.istanza_utility_id ?? null"
        :readonly="isReadonlyPuro"
        :capabilities="capabilities"
        @state="(s) => { indirizzoObbligatorioMancante = s.obbligatorioMancante }"
        :cliente-da-salvare="clienteCambiato(form, detail, CAMPI_CLIENTE_DDT)"
        :bordo="false" />

      <Divider />
      <DdtRigheTable
        ref="righeTableRef"
        :ddt-id="effectiveDdtId"
        :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
        :is-modificabile="canEditRighe && !isReadonly"
        :causale-fatturabile="causaleFatturabile"
        @changed="onRigheChanged"
        @form-aperto="onFormAperto" />

      <!-- Prelievi (Lotto 3 R-2b): da dove esce la merce. Compare solo se la
           bolla muove merce. Aggiungere e togliere solo in bozza; l'ubicazione
           di arrivo anche dopo l'emissione, fino alla consegna (decide il DB). -->
      <DdtPrelieviSection
        ref="prelieviRef"
        :ddt-id="effectiveDdtId"
        :modificabile="canEditRighe && !isReadonly"
        :arrivo-modificabile="!isReadonlyPuro"
        @changed="onPrelieviChanged" />

      <!-- Riepilogo IVA aggregato (regola fiscale DPR 633/72 art. 21).
           Visibile con almeno una riga valorizzata (righe prezzo NULL escluse
           in vista: DDT solo di trasporto -> pannello nascosto). Componente
           riusabile cross-dominio condiviso con preventivi/ordini. -->
      <template v-if="showRiepilogoIva">
        <Divider />
        <RiepilogoIvaTable :items="riepilogoIva" :show-subtitle="true" />
      </template>

    </template>
  </AppDrawer>

  <!-- Sub-drawer note: cablato sull'id effettivo del DDT. -->
  <DdtNoteDrawer
    v-if="effectiveDdtId"
    v-model:visible="noteDrawerVisible"
    :ddt-id="effectiveDdtId"
  />

  <!-- Dialog "Genera reso" (slice resi): righe consegnate con residuo rendibile,
       aperta dal pulsante in barra azioni. Il reso nasce DRAFT nel tab Resi;
       alla sua CONFERMA il BE riapre il residuo ordine e, se il reso e' TOTALE,
       flippa questo DDT a RESO. `readonly` = quello PURO del chiamante: il lock
       di stato del drawer (CONSEGNATO) non deve disabilitare un'azione di
       processo legittima proprio in quello stato. -->
  <DdtResoDialog
    v-if="effectiveDdtId && showResoAction"
    v-model:visible="resoDialogVisible"
    :ddt-id="effectiveDdtId"
    :readonly="props.readonly || parentReadonly"
    @reso-creato="onResoCreato"
  />

  <!-- La conferma dell'annullo di una bolla con legami (ordini, resi, righe di
       commessa): aperta dalla domanda del DB, chiusa dalla conferma o dalla
       rinuncia. Finestra comune ai documenti che si annullano con conferma. -->
  <DocumentoAnnulloLegamiDialog
    v-if="effectiveDdtId"
    :visible="domandaAnnullo !== null"
    base-path="/vendite/ddt"
    :doc-id="effectiveDdtId"
    :header="t('vendite.ddt.azione_annulla')"
    :domanda="domandaAnnullo"
    :loading="cambioStato.loading.value"
    :readonly="isReadonlyPuro"
    @conferma="onConfermaAnnullo"
    @cancel="cambioStato.annulla()"
  />

  <!-- Dialog emissione DDT (transizione DRAFT → EMESSO, assegna numero). -->
  <DdtEmissioneDialog
    v-model:visible="emissioneDialogVisible"
    :ddt="detail"
    :loading="emissioneLoading"
    @confirm="handleEmissioneConferma"
    :indirizzo-mancante="indirizzoObbligatorioMancante"
  />
</template>
