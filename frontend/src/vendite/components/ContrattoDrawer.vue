<script setup>
// Scopo: Drawer contratto v5 (modello unificato 2026-05-15) — testata +
//        sezione Pricing semplificata + sub-drawer righe (eccezioni
//        OVERRIDE/ESCLUSIONE/AGGIUNTA) + sub-drawer utility 1:1.
//
// Refactor modalita 2026-05-15: la "modalita A/B/C" sparisce come scelta
// utente. La forma del contratto e' derivata dai dati di testata:
//   - listino_id valorizzato (con/senza variazione globale) = "con_listino"
//   - listino_id NULL (interamente negoziato) = "senza_listino"
// Il badge `forma derivata` mostra all'operatore cosa ha creato post-save,
// ma non e' piu' una scelta esplicita. Il SelectButton A/B/C e il lookup
// `vendite.modalita_pricing_contratto` (entrambi rimossi) sono stati
// sostituiti da campi opzionali (Listino + Variazione globale).
import { ref, watch, computed, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContrattiStore } from '../stores/contratti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useInjectReadonly, READONLY_KEY } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useEntityCapabilities } from '../../core/composables/useEntityCapabilities'
import { DRAWER_WIDTH, MANAGE_ICONS, TIPO_RUOLO } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { addDaysToToday, toDateString, parseIsoDate, displayDate } from '../../core/utils/date'
import { paramInt, paramString } from '../../core/utils/parameterCast'
import { statoContrattoSeverity } from '../../core/utils/severity'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import DocumentoIndirizziSection from '../_shared/indirizzi/DocumentoIndirizziSection.vue'
import DocumentoCollegamentiBar from '../_shared/lineage/DocumentoCollegamentiBar.vue'
import { mapAvailableActionsToDrawerActions } from '../../core/composables/useDrawerActions'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { lookupListiniSelezionabiliContratto } from '../api/lookup'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import EmittenteFiscaleField from '../../core/components/EmittenteFiscaleField.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import ContrattoNoteDrawer from './ContrattoNoteDrawer.vue'
import ContrattoEmissioneDialog from './dialogs/ContrattoEmissioneDialog.vue'
import ContrattoRigheDrawer from './ContrattoRigheDrawer.vue'
import EntityPdfButton from '../../documenti/components/EntityPdfButton.vue'
import { SORGENTE_CODES } from '../../documenti/constants'
import TipoVariazioneSelect from './TipoVariazioneSelect.vue'
import AmbitoContrattoSelect from './AmbitoContrattoSelect.vue'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { useUtilityDefaultId } from '../../core/composables/useUtilityDefaultId'
import { useEmittenteFiscaleField } from '../../core/composables/useEmittenteFiscaleField'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { getContrattoFormDefaults } from '../api/formDefaults'
import { useBaFormDefaults } from '../_shared/baDefaults/useBaFormDefaults'
import Drawer from 'primevue/drawer'
import AppDialog from '../../core/components/AppDialog.vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import ToggleSwitch from 'primevue/toggleswitch'

const { t, te } = useI18n()
const store = useContrattiStore()
const { execute, loading } = useApiHandler()
// Readonly da permessi area (LETTURA/BLOCCATO). Si combina con isContractLocked
// (stato post-DRAFT) per ottenere l'isReadonly effettivo del drawer.
const parentReadonly = useInjectReadonly()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  contrattoId: { type: Number, default: null },
  // Prefill opzionale per creazione da contesto cliente (ContrattiBillingAccountDrawer).
  initialBillingAccount: { type: Object, default: null },
  // Forza la sola lettura a prescindere da permessi/stato (allinea allo standard
  // [[feedback_drawer_readonly]]). Usato per riusare il drawer come visualizzatore
  // read-only di un contratto "altro" (es. ispezione contratto sovrapposto dal
  // dialog di successione offerta): si propaga via READONLY_KEY a tutti i sub-drawer.
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

const detail = ref(null)
const form = ref({})

// Capability dal detail backend (Fase 1.B2: script.fn_available_actions_contratto).
// Il drawer NON ricalcola lo stato: tutto deriva dai metadata API.
// Composable centralizzato (Fase 4.F2): isLocked(field) = !canEdit OR Set lookup.
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })
const availableActions = caps.availableActions
const isLocked = caps.isLocked
const righeCount = computed(() => detail.value?.righe_count ?? detail.value?.righe?.length ?? 0)

// isContractLocked = stato post-DRAFT. La regola di dominio e' "modifiche
// libere via form solo in DRAFT". In ATTIVO la modifica di `valido_al/meta`
// (whitelist BE) avviene comunque via dialog dedicato "Cessa contratto",
// non via form drawer. CESSATO/ANNULLATO interamente immutabili.
// Prima usava `!canEditTestata` (true in ATTIVO/ANNULLATO perche' la fn DB
// considera ATTIVO parzialmente editabile) -> sub-drawer righe restava
// erroneamente editabile in stati terminali. Allineato al footer
// Salva/Chiudi che gia' usa stato_codice_interno === 'DRAFT'.
const isContractLocked = computed(
  () => isEdit.value && detail.value?.stato_codice_interno !== 'DRAFT',
)

// isReadonly effettivo del drawer: OR tra permessi area e stato post-DRAFT.
// Tutti i campi/azioni del drawer principale e dei sub-drawer (righe, utility)
// si basano su questo computed. Propagato via provide ai figli, che usano
// solo `useInjectReadonly()` senza logica locale (standard del progetto).
const isReadonly = computed(
  () => props.readonly || parentReadonly.value || isContractLocked.value,
)
provide(READONLY_KEY, isReadonly)

// Deferimento contenuto: i LookupSelect montano solo dopo l'animazione del drawer
// (pattern feedback_content_ready_after_show centralizzato in useDrawerContentReady).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

// Lookup dinamico listini "selezionabili come riferimento contrattuale"
// (refactor 2026-05-18 §4.4): filtra `vendite.listini` per esistenza di una
// versione ATTIVA. Cache modulo-level via useGlobalLookup (chiave stabile
// `vendite.listini_selezionabili_contratto`): primo consumer fa la fetch,
// successivi riusano. Single source of truth lato BE: endpoint dedicato
// `/vendite/lookup/listini-selezionabili-contratto/`. Sostituisce il
// generico `LookupSelect rel="vendite.listini"` che mostrava anche listini
// senza versione operativa, il cui salvataggio sarebbe rifiutato dal guard
// service `E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA` (UX a doppio passo).
const listiniLookup = useGlobalLookup(
  'vendite.listini_selezionabili_contratto',
  lookupListiniSelezionabiliContratto,
  { immediate: true, transform: (r) => r.data.data },
)
// Label dropdown: "descrizione (codice)" come `LookupSelect show-code`.
function formatListinoOption(item) {
  if (!item) return ''
  return item.codice ? `${item.descrizione} (${item.codice})` : item.descrizione
}

// Sub-drawer
const righeVisible = ref(false)
const noteDrawerVisible = ref(false)

// Guard di versione: invalida fetch stantii su apertura/chiusura rapide.
const fgFv = useFetchVersion()

// Defaults non-BA da config.parameters (Fase 2 refactor frontend vendite).
// Caricati on-open drawer prima di resetForm; cache modulo `useParameterDefaults`.
// Niente magic string COMMODITY/PERCENTUALE qui: arrivano dal seed DB
// con fallback robusto in caso di parameter mancante.
// Refactor modalita 2026-05-15: VENDITE_CONTRATTO_DEFAULT_MODALITA rimosso
// (era il default del vecchio SelectButton A/B/C, ora obsoleto).
const { defaults: paramDefaults, load: loadParamDefaults } = useParameterDefaults([
  'VENDITE_CONTRATTO_DEFAULT_AMBITO',
  'VENDITE_CONTRATTO_DEFAULT_TIPO_VARIAZIONE_GLOBALE',
  'VENDITE_CONTRATTO_DEFAULT_DATA_LEAD_GG',
  'VENDITE_CONTRATTO_DEFAULT_VALIDO_DAL_LEAD_GG',
])

// Default utility globale: il parametro DEFAULT_UTILITY stocca un codice_interno
// (framework FK-surrogata, DB 2026-05-02). Composable risolve a id locale.
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

// Emittente fiscale default dal profilo operatore (modello 1-a-1 salvo admin
// globale multi-EF). Pattern allineato a OffertaDrawer/PreventiviForm post
// brief simmetria 2026-05-26: il drawer popola `emittente_fiscale_id` in
// CREATE e il backend lo accetta come opzionale (trigger DB lo deriva
// dalla GUC `app.current_user_id` se assente).
const { defaultEmittenteId } = useEmittenteFiscaleField()

function defaultForm() {
  const p = paramDefaults.value
  const dataLeadGg = paramInt(p.VENDITE_CONTRATTO_DEFAULT_DATA_LEAD_GG, 0)
  const validoDalLeadGg = paramInt(p.VENDITE_CONTRATTO_DEFAULT_VALIDO_DAL_LEAD_GG, 0)
  return {
    // Emittente derivato dal profilo (1-a-1 operatore->EF, salvo admin
    // multi-EF). `defaultEmittenteId` e' un ref reattivo; alla prima
    // apertura del drawer in CREATE puo' essere null finche' il profilo
    // non e' caricato — il watch d'apertura lo legge gia' valorizzato.
    emittente_fiscale_id: defaultEmittenteId.value ?? null,
    billing_account_id: null,
    billing_account_obj: null,
    istanza_utility_id: null,
    utility_id: utilityDefaultId.value,
    ambito: paramString(p.VENDITE_CONTRATTO_DEFAULT_AMBITO, 'COMMODITY'),
    valido_dal: toDateString(addDaysToToday(validoDalLeadGg)),
    valido_al: null,
    data: toDateString(addDaysToToday(dataLeadGg)),
    parent_contratto_id: null,
    // Categoria cliente snapshot
    categoria_cliente_id_snapshot: null,
    // Corsia di instradamento: default differita (DEFAULT false a DB).
    fatturazione_immediata: false,
    // Pricing — refactor modalita 2026-05-15: niente piu' SelectButton A/B/C.
    // Listino e variazione globale sono campi opzionali liberi; la "forma"
    // (con/senza listino) e' derivata e mostrata come badge readonly post-save.
    listino_id: null,
    tipo_variazione_globale: null,
    valore_variazione_globale: null,
    // Valuta snapshot: pre-popolata da getContrattoFormDefaults (cascata
    // BA→EF-BA→EF-utente→gestore via BB resolve_valuta_default).
    // Immutabile in EDIT.
    valuta_id: null,
    // Utility 1:1 (create inline)
    utility_tipo_utenza_id: null,
    utility_classe_utenza_id: null,
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
}

function populateFromDetail(d) {
  form.value = {
    emittente_fiscale_id: d.emittente_fiscale_id,
    billing_account_id: d.billing_account_id,
    billing_account_obj: d.ba_ragione_sociale ? {
      id: d.billing_account_id,
      codice: d.ba_codice,
      ragione_sociale: d.ba_ragione_sociale,
      utility_codice: d.utility_codice,
      utility_descrizione: d.utility_descrizione,
      pdp: d.pdp || null,
    } : null,
    istanza_utility_id: d.istanza_utility_id,
    utility_id: d.utility_id,
    ambito: d.ambito || 'COMMODITY',
    valido_dal: d.valido_dal,
    valido_al: d.valido_al,
    data: d.data,
    parent_contratto_id: d.parent_contratto_id,
    categoria_cliente_id_snapshot: d.categoria_cliente_id_snapshot || null,
    fatturazione_immediata: d.fatturazione_immediata ?? false,
    listino_id: d.listino_id,
    tipo_variazione_globale: d.tipo_variazione_globale,
    valore_variazione_globale: d.valore_variazione_globale,
    valuta_id: d.valuta_id,
    utility_tipo_utenza_id: d.utility?.tipo_utenza_id || null,
    utility_classe_utenza_id: d.utility?.classe_utenza_id || null,
  }
}

// Forma derivata (refactor modalita 2026-05-15): "con_listino" se l'operatore
// ha indicato un listino di riferimento, "senza_listino" altrimenti. Usata per
// il badge informativo readonly nell'header drawer post-save. Non e' una scelta
// dell'operatore — segue automaticamente i campi compilati.
const formaDerivata = computed(() => {
  return form.value.listino_id ? 'con_listino' : 'senza_listino'
})

// Quando l'operatore rimuove il listino_id, il payload deve coerentemente
// azzerare variazione globale. Listino settato senza variazione resta valido
// (forma "con_listino" con sola applicazione listino, ex-modalita B/A-puro).
function onListinoChange(nuovoListinoId) {
  if (!nuovoListinoId) {
    form.value.tipo_variazione_globale = null
    form.value.valore_variazione_globale = null
  }
  // Selezione listino non-null: nessun pre-fill di tipo. Il pre-fill produceva
  // coppia incoerente (tipo=PERCENTUALE, valore=null) che in edit mascherava
  // E_VENDITE_CONTRATTO_OVERLAP con un generico "Payload contratto non valido"
  // perche' il BE rifiutava la coppia prima del DB check. Il pre-fill del tipo
  // avviene gia' in `onValoreVariazioneChange` quando l'operatore inizia a
  // valorizzare il delta — coerente con la regola BE "entrambi presenti o
  // entrambi NULL".
}

// Quando l'operatore inserisce un tipo variazione ma non un valore (o
// viceversa), la coppia e' incompleta — il BE rifiuterebbe. Auto-reset
// del tipo se valore tornato a null, e mantenimento del tipo se valore valido.
function onValoreVariazioneChange(nuovoValore) {
  if (nuovoValore == null && !form.value.tipo_variazione_globale) {
    form.value.tipo_variazione_globale = null
  } else if (nuovoValore != null && !form.value.tipo_variazione_globale) {
    form.value.tipo_variazione_globale = paramString(
      paramDefaults.value.VENDITE_CONTRATTO_DEFAULT_TIPO_VARIAZIONE_GLOBALE,
      'PERCENTUALE',
    )
  }
}

// Wrapper: accetta sia string che Date (DatePicker emette Date).
function toIsoDate(d) {
  return typeof d === 'string' ? d : toDateString(d)
}

// Carica dati all'apertura. Il reset di `contentReady` alla chiusura e' gestito
// dal composable useDrawerContentReady — qui resta solo l'invalidation del guard
// di versione per scartare fetch stantii in caso di apertura/chiusura rapide.
watch(() => props.visible, async (val) => {
  if (!val) { fgFv.invalidate(); return }
  const v = fgFv.tag()

  // loadParamDefaults serve sia in EDIT (onModalitaChange usa
  // VENDITE_CONTRATTO_DEFAULT_TIPO_VARIAZIONE_GLOBALE) sia in CREATE.
  // loadUtilityDefault serve solo in CREATE (in EDIT utility_id arriva
  // dal detail BE). In CREATE le carichiamo in parallelo.
  if (isEdit.value && props.contrattoId) {
    await loadParamDefaults()
    if (!fgFv.isCurrent(v)) return
    const d = await loadDetailOrClose(() => store.fetchDetail(props.contrattoId))
    if (!fgFv.isCurrent(v)) return
    if (d == null) return  // dettaglio non accessibile → drawer già chiuso
    detail.value = d
    populateFromDetail(d)
  } else {
    await Promise.all([loadParamDefaults(), loadUtilityDefault()])
    if (!fgFv.isCurrent(v)) return
    resetForm()
    // Prefill BA se aperto da contesto cliente.
    if (props.initialBillingAccount?.id) {
      onBaSelected(props.initialBillingAccount)
    } else {
      // CREATE senza BA: pre-popoliamo la valuta dal BB resolve_valuta_default
      // lato BE (catena EF utente → gestore). Mirror PreventiviDrawer /
      // OffertaDrawer. Se BA viene selezionato dopo, il watch su
      // billing_account_id sovrascrive col valore BA-resolved.
      try {
        const res = await getContrattoFormDefaults(null)
        if (!fgFv.isCurrent(v)) return
        const data = res?.data?.data
        if (data && form.value.valuta_id == null && data.valuta_id != null) {
          form.value.valuta_id = data.valuta_id
        }
      } catch {
        // Best-effort: trigger DB risolverà la valuta al save.
      }
    }
  }
})

// Badge sintetico: "GAS — PDP IT001E00012345" oppure solo "GAS" se senza PDP.
const baBadgeLabel = computed(() => {
  const ba = form.value.billing_account_obj
  if (!ba) return ''
  const utility = ba.utility_codice || ba.utility_descrizione || ''
  if (!utility) return ''
  const pdp = ba.pdp ? `PDP ${ba.pdp}` : ''
  return pdp ? `${utility} — ${pdp}` : utility
})

function onBaSelected(item) {
  if (!item) {
    form.value.billing_account_id = null
    form.value.billing_account_obj = null
    form.value.istanza_utility_id = null
    // Ripristina il default utility quando si pulisce il BA: l'operatore
    // mantiene il filtro lookup BA sull'utility tipica del proprio EF
    // invece di tornare a "vedo tutti i BA". Allinea OffertaDrawer.
    form.value.utility_id = utilityDefaultId.value
    form.value.categoria_cliente_id_snapshot = null
    return
  }
  form.value.billing_account_id = item.id
  form.value.billing_account_obj = item
  form.value.istanza_utility_id = item.istanza_utility_id || null
  form.value.utility_id = item.utility_id || null
  // Pre-compila la categoria dal BA; l'operatore puo' cambiarla.
  form.value.categoria_cliente_id_snapshot = item.categoria_cliente_id || null
}

// Auto-fill valuta dal form-defaults BE (BB resolve_valuta_default), al cambio
// BA in CREATE: la valuta del BA vince (regola di coerenza dominio). Watcher
// condiviso `useBaFormDefaults` con guard latest-wins inclusa.
useBaFormDefaults({ form, isEdit, fetchDefaults: getContrattoFormDefaults })

// Validazione FE (refactor modalita 2026-05-15: niente piu' check su modalita).
// Vincolo strutturale unico sulla coppia variazione globale: tipo e valore
// devono essere entrambi presenti o entrambi null (vincolo BE
// _validate_variazione_globale_coppia_coerente). Listino e variazione sono
// indipendenti: contratto senza listino e' valido (forma "senza_listino"),
// contratto con listino senza variazione e' valido (forma "con_listino"
// listino tal quale), contratto con listino + variazione e' valido.
const canSave = computed(() => {
  if (isReadonly.value) return false
  const f = form.value
  // Coppia variazione coerente: tipo presente <=> valore presente. Applicabile
  // sia in create che in edit — il BE rifiuta la coppia incoerente con
  // `_validate_variazione_globale_coppia_coerente` (entrambi presenti o
  // entrambi NULL). Disattivare il pulsante Salva e' l'unico modo di evitare
  // il toast generico "Payload contratto non valido" quando, ad esempio,
  // l'operatore cambia listino in edit.
  const hasTipo = !!f.tipo_variazione_globale
  const hasValore = f.valore_variazione_globale != null && f.valore_variazione_globale !== ''
  if (hasTipo !== hasValore) return false
  if (isEdit.value) return true
  // Per operatore non-admin il `defaultEmittenteId` arriva dal profilo
  // (`useAuthStore`) e il check non blocca; per admin globale multi-EF
  // serve scelta esplicita prima di abilitare Salva.
  if (!f.emittente_fiscale_id) return false
  if (!f.billing_account_id) return false
  if (!f.valido_dal || !f.data) return false
  if (!f.ambito) return false
  return true
})

function buildPayload() {
  const f = form.value
  // Profilo A whitelist FE: il payload PATCH va limitato ai campi che il
  // BE accetta nello stato corrente. Il BE applica una guard speculare
  // (E_CONTRATTO_NON_MODIFICABILE) — rispettiamo la stessa whitelist qui
  // per evitare round-trip e fornire UX coerente.
  // - DRAFT: tutti i campi
  // - ATTIVO: solo valido_al + meta (programma cessazione + note)
  // - CESSATO: nessuno (Salva non dovrebbe nemmeno essere cliccabile)
  const stato = isEdit.value ? (detail.value?.stato_codice_interno || null) : 'DRAFT'
  const isDraft = stato === 'DRAFT'

  if (!isDraft) {
    // Stati post-DRAFT: il pulsante Salva e' disabilitato (canSave=false
    // perche' isReadonly=true). Questo branch non dovrebbe mai essere
    // raggiunto in pratica; ritorniamo payload vuoto per safety. Le
    // operazioni post-DRAFT sono solo via cambio stato (dialog Cessa).
    return {}
  }

  const payload = {
    ambito: f.ambito,
    valido_dal: toIsoDate(f.valido_dal),
    valido_al: toIsoDate(f.valido_al),
    data: toIsoDate(f.data),
    parent_contratto_id: f.parent_contratto_id || null,
    categoria_cliente_id_snapshot: f.categoria_cliente_id_snapshot || null,
    // Corsia di instradamento: solo in PATCH. La fn madre di create
    // (vendite.fn_create_contratto) ha una whitelist SUA che non contiene
    // ancora la colonna e la scarterebbe in silenzio -> il create la omette
    // esplicitamente (vedi handleSave). Brief DB passato al team.
    fatturazione_immediata: !!f.fatturazione_immediata,
  }
  // Pricing — refactor modalita 2026-05-15: niente piu' if-chain modalita.
  // Il payload include sempre listino_id (puo' essere null = forma senza_listino).
  // La coppia variazione globale (tipo+valore) e' opzionale; il vincolo di
  // coppia coerente (entrambi NULL o entrambi NOT NULL) e' validato lato FE
  // in canSave e lato BE in _validate_variazione_globale_coppia_coerente.
  payload.listino_id = f.listino_id || null
  payload.tipo_variazione_globale = f.tipo_variazione_globale || null
  payload.valore_variazione_globale = (f.valore_variazione_globale != null
    && f.valore_variazione_globale !== '')
    ? String(f.valore_variazione_globale)
    : null
  return payload
}

async function handleSave() {
  if (isEdit.value) {
    const result = await execute(
      () => store.update(props.contrattoId, buildPayload()),
      { successMessage: t('vendite.contratti.contratto_salvato') }
    )
    if (result !== null) emit('saved', result)
  } else {
    const f = form.value
    // `fatturazione_immediata` viaggia solo nella PATCH: il BE rifiuta le
    // chiavi fuori dalla whitelist di create con un 400, e la fn madre DB la
    // scarterebbe comunque in silenzio. Si scorpora qui, esplicitamente.
    const { fatturazione_immediata: _soloInPatch, ...campiCreate } = buildPayload()
    const payload = {
      emittente_fiscale_id: f.emittente_fiscale_id,
      billing_account_id: f.billing_account_id,
      istanza_utility_id: f.istanza_utility_id,
      utility_id: f.utility_id,
      // Valuta inviata SOLO in CREATE: snapshot immutabile post-INSERT
      // (non in _UPDATE_KEYS_TESTATA BE). Se null, il trigger DB la
      // risolve via fn_get_valuta_id (BA→emittente→gestore).
      valuta_id: f.valuta_id || null,
      ...campiCreate,
    }
    // Utility 1:1 inline: tipo/classe utenza (opzionali)
    if (f.utility_tipo_utenza_id || f.utility_classe_utenza_id) {
      payload.utility = {
        tipo_utenza_id: f.utility_tipo_utenza_id || null,
        classe_utenza_id: f.utility_classe_utenza_id || null,
      }
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('vendite.contratti.contratto_creato') }
    )
    if (result !== null) emit('saved', result)
  }
}

// Ricarica dettaglio (usata dopo cambio stato o mutazioni righe/utility).
async function refreshDetail() {
  if (!props.contrattoId) return
  const d = await store.fetchDetail(props.contrattoId)
  detail.value = d
  populateFromDetail(d)
}

// Stato dialog cessazione: una azione con `requires_date=true` apre il dialog
// con `default_date` e `min_date` arrivati dal BE
// (script.fn_available_actions_contratto).
//
// Comportamento data-driven (allineato col guard DB
// `trgfn_contratti_guard_transizione_stato`):
// - data <  oggi  -> VIETATO (cessazione retroattiva: il DB rifiuta). La UI
//                    blocca a monte con min-date = oggi, niente scelta retroattiva.
// - data == oggi  -> cessazione IMMEDIATA: stato passa subito a CESSATO
//                    (e' la data di fine validita' a confermare).
// - data >  oggi  -> cessazione PROGRAMMATA: stato resta ATTIVO, il job
//                    notturno DB allinea a CESSATO quando la data scade.
const cessaDialogVisible = ref(false)
const cessaDialogData = ref(null)
const cessaDialogAction = ref(null)
// Dialog attivazione contratto: aperto quando l'azione di stato porta a
// ATTIVO (transizione DRAFT → ATTIVO). Sostituisce il confirmAction generico
// perche' l'attivazione orchestra atomic state + genera documento + allegati
// lato BE (refactor 2026-05-28, mirror del flusso offerta/preventivo).
const emissioneDialogVisible = ref(false)
const emissioneLoading = ref(false)
// Min selezionabile: oggi (no retroattivo). Se il contratto inizia nel futuro
// (valido_dal > oggi, esposto dal BE come min_date) il minimo e' valido_dal.
const cessaDialogMinDate = computed(() => {
  const oggi = new Date()
  oggi.setHours(0, 0, 0, 0)
  const beMin = parseIsoDate(cessaDialogAction.value?.min_date)
  return beMin && beMin > oggi ? beMin : oggi
})

// Programmata SOLO se strettamente futura. Data odierna = cessazione immediata.
const cessazioneProgrammata = computed(() => {
  if (!cessaDialogData.value) return false
  const oggi = new Date()
  oggi.setHours(0, 0, 0, 0)
  const scelta = new Date(cessaDialogData.value)
  scelta.setHours(0, 0, 0, 0)
  return scelta > oggi
})

function openCessaDialog(action) {
  cessaDialogAction.value = action
  // default_date dal BE; fallback oggi solo se la fn non lo fornisce.
  cessaDialogData.value = parseIsoDate(action?.default_date) || new Date()
  cessaDialogVisible.value = true
}

async function onConfermaCessazione() {
  const validoAl = toDateString(cessaDialogData.value)
  const programmata = cessazioneProgrammata.value
  const targetState = cessaDialogAction.value?.target_state || 'CESSATO'
  const result = await execute(
    () => store.cambiaStato(props.contrattoId, targetState, { validoAl }),
    {
      successMessage: programmata
        ? t('vendite.contratti.cessa_dialog_success_programmata', { data: validoAl })
        : t('vendite.contratti.cessa_dialog_success_immediata'),
    },
  )
  if (result !== null) {
    cessaDialogVisible.value = false
    await refreshDetail()
  }
}

// Cambio stato (edit). Le azioni vengono dal backend:
// - requires_date=true  -> dialog con DatePicker (es. "cessa")
// - requires_confirm    -> confirmAction con label_key dell'azione
// - altrimenti          -> diretto
function onCambiaStato(action) {
  // Transizione → ATTIVO: dialog dedicato con anteprima documento + allegati.
  // L'endpoint /emetti/ (multipart) orchestra atomic state + genera + allegati
  // (refactor 2026-05-28). NB: il BE rifiuta la transizione via /cambia-stato/
  // con E_VENDITE_VALIDAZIONE — questa intercettazione e' la sola via supportata.
  if (action.target_state === 'ATTIVO') {
    emissioneDialogVisible.value = true
    return
  }
  if (action.requires_date) {
    openCessaDialog(action)
    return
  }
  // Annullamento: dialog dedicato con messaggio specifico (numero contratto,
  // wording "operazione irreversibile") invece del confirm generico. Post
  // brief DB 2026-05-28 l'azione arriva data-driven da
  // `fn_available_actions_contratto` con `key='annulla'`.
  if (action.key === 'annulla') {
    onAnnullaContratto(action)
    return
  }
  if (action.requires_confirm) {
    confirmAction({
      title: t('vendite.contratti.conferma_titolo'),
      message: t('vendite.contratti.conferma_cambio_stato', { stato: t(action.label_key) }),
      onAccept: () => eseguiCambioStato(action.target_state),
    })
    return
  }
  eseguiCambioStato(action.target_state)
}

async function eseguiCambioStato(targetState) {
  const result = await execute(
    () => store.cambiaStato(props.contrattoId, targetState),
    { successMessage: t('vendite.contratti.stato_cambiato') },
  )
  if (result !== null) await refreshDetail()
}

// Scopo: callback @confirm del ContrattoEmissioneDialog. Riceve i file
// staged dall'utente e chiama store.emetti (POST multipart /emetti/).
// Loading + abandon-warning sono gestiti dal building block generico.
async function handleEmissioneConferma({ files }) {
  emissioneLoading.value = true
  const result = await execute(
    () => store.emetti(props.contrattoId, { allegati: files || [] }),
    { successMessage: t('vendite.contratti.stato_cambiato') },
  )
  emissioneLoading.value = false
  if (result !== null) {
    emissioneDialogVisible.value = false
    await refreshDetail()
  }
}

// Refactor 2026-05-20: annullamento contratto (transizione DRAFT → ANNULLATO).
// Bottone temporaneo finche' `fn_available_actions_contratto` non espone
// l'azione lato BE. Solo DRAFT: ATTIVO → ANNULLATO non e' transizione
// ammessa (per contratti attivi si usa CESSATO con data di fine validita').
function onAnnullaContratto(action) {
  // target_state arriva data-driven dall'azione BE (`available_actions[]` di
  // `fn_available_actions_contratto`). Fallback 'ANNULLATO' difensivo per
  // eventuali chiamate dirette senza action (oggi non esistono).
  const targetState = action?.target_state || 'ANNULLATO'
  confirmAction({
    header: t('vendite.contratti.annulla_dialog_titolo'),
    message: t('vendite.contratti.annulla_dialog_messaggio', { numero: detail.value?.numero }),
    acceptLabel: t('vendite.contratti.annulla_dialog_conferma'),
    danger: true,
    onAccept: () => eseguiCambioStato(targetState),
  })
}

// Azioni della testata contratto consumate da DrawerActionsBar.
// Composizione: transizioni di stato data-driven (availableActions BE) +
// Gestisci righe/note (sub-drawer). Il PDF resta componente dedicato nel
// #suffix del BB (stateful). Post brief DB 2026-05-28 anche `annulla` su
// DRAFT arriva da `fn_available_actions_contratto` (niente piu' hardcoded).
const drawerActions = computed(() => {
  if (!isEdit.value || !detail.value) return []
  // Read-only PURO (permesso LETTURA / pannello split / readonly forzato per
  // ispezione di un contratto "altro"): niente azioni di cambio stato/cessa —
  // si sta solo visualizzando. NB: `props.readonly || parentReadonly`, NON
  // `isReadonly`: quest'ultimo include il lock-di-stato (un contratto ATTIVO ha
  // la form bloccata ma DEVE mostrare "Cessa"). Restano i pannelli righe/note
  // (aprono i sub-drawer in sola lettura via READONLY_KEY).
  const list = mapAvailableActionsToDrawerActions({
    availableActions,
    t,
    te,
    onAction: onCambiaStato,
    readonly: props.readonly || parentReadonly.value,
  })
  list.push({
    key: 'manage-righe',
    kind: 'manage',
    label: t('vendite.contratti.gestisci_righe'),
    icon: MANAGE_ICONS.RIGHE,
    badge: righeCount.value,
    command: () => { righeVisible.value = true },
  })
  list.push({
    key: 'manage-note',
    kind: 'manage',
    label: t('vendite.contratti.gestisci_note'),
    icon: MANAGE_ICONS.NOTE,
    command: () => { noteDrawerVisible.value = true },
  })
  return list
})

const onClose = useDrawerClose(emit, 'cancelled')
// Detail fuori scope (RLS) / inesistente → toast + chiusura, niente drawer vuoto.
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    :dismissable="true"
    @update:visible="val => emit('update:visible', val)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('vendite.contratti.contratto')"
        :icon="NAV_ICONS.CONTRATTI"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">

      <!-- === Intestazione edit: numero/stato + azioni testata omogenee ai preventivi.
           Refactor UI drawer 2026-05-21: header info e azioni passano dai BB
           condivisi DrawerEntityHeader + DrawerActionsBar (vedi
           docs/it/dev/frontend/frontend-standards.md §"Azioni Drawer"). === -->
      <template v-if="isEdit && detail">
        <DrawerEntityHeader>
          <Tag :value="detail.numero" severity="secondary" />
          <span v-if="detail.data" class="app-drawer-header-muted">
            {{ displayDate(detail.data) }}
          </span>
          <Tag
            :value="t(`vendite.contratti.forma_${formaDerivata}`)"
            :severity="formaDerivata === 'senza_listino' ? 'warn' : 'info'"
          />
          <template #status>
            <Tag
              :value="detail.stato_descrizione"
              :severity="statoContrattoSeverity(detail.stato_codice_interno)"
            />
          </template>
        </DrawerEntityHeader>

        <DrawerActionsBar :actions="drawerActions">
          <template #suffix>
            <EntityPdfButton
              :sorgente-code="SORGENTE_CODES.CONTRATTO"
              :entity-id="props.contrattoId"
              :pdf="detail.pdf"
              i18n-prefix="vendite.contratti.pdf"
              :dialog-title="detail.numero
                ? t('vendite.contratti.pdf.dialog_title', { numero: detail.numero })
                : ''"
            />
          </template>
        </DrawerActionsBar>

        <!-- Collegamenti diretti (pratica + origine + destinazioni di livello 1):
             segnalazione a colpo d'occhio sotto i pulsanti. Il grafo completo si
             apre dai chip in dialog. Solo in EDIT. -->
        <DocumentoCollegamentiBar
          v-if="isEdit && contrattoId"
          base-path="/vendite/contratti"
          :doc-id="contrattoId"
          :readonly="readonly || parentReadonly" />

        <!-- Banner contratto bloccato: in stati post-DRAFT ammessa solo
             modifica valido_al (programma cessazione) + cambio stato.
             Coerente con Profilo A whitelist BE. -->
        <Message v-if="isContractLocked && detail.stato_codice_interno !== 'CESSATO'"
          severity="info" :closable="false" size="small" class="mt-2">
          {{ t('vendite.contratti.banner_locked_attivo', { stato: detail.stato_descrizione }) }}
        </Message>
        <Message v-else-if="isContractLocked && detail.stato_codice_interno === 'CESSATO'"
          severity="warn" :closable="false" size="small" class="mt-2">
          {{ t('vendite.contratti.banner_locked_cessato') }}
        </Message>
      </template>

      <!-- === Emittente fiscale === -->
      <!-- Sezione separata sopra il cliente (pattern offerte/preventivi).
           Operatore con EF assegnato -> read-only auto-popolato dal profilo;
           admin globale (multi-EF) -> Select sugli EF disponibili.
           In edit mostra codice + ragione sociale denormalizzati dal record. -->
      <h4 class="mt-3">{{ t('vendite.contratti.section_emittente') }}</h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_emittente_fiscale') }} <span v-if="!isEdit">*</span></label>
          <EmittenteFiscaleField
            v-model="form.emittente_fiscale_id"
            :record="detail"
            :is-edit="isEdit"
            :disabled="isReadonly"
          />
        </div>
      </div>

      <!-- === Cliente (BA + utility) + badge utility/PDP === -->
      <h4 class="mt-3">
        {{ t('vendite.contratti.section_cliente') }}
        <Tag v-if="baBadgeLabel" :value="baBadgeLabel" severity="info" class="ml-2" />
      </h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_billing_account') }} <span v-if="!isEdit">*</span></label>
          <!-- `utility-id` pre-filtra il lookup BA sull'utility selezionata
               (default = utility dell'operatore via `utilityDefaultId`).
               `onBaSelected` sovrascrive `utility_id` con quella canonical
               del BA scelto, mantenendo coerenza FK. Allinea OffertaDrawer. -->
          <BillingAccountLookup
            v-if="!isEdit"
            :model-value="form.billing_account_obj"
            :utility-id="form.utility_id"
            @update:model-value="onBaSelected"
            :placeholder="t('vendite.contratti.select_billing_account')"
          />
          <InputText v-else :model-value="detail?.ba_ragione_sociale" disabled class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_utility') }} <span v-if="!isEdit">*</span></label>
          <!-- Building block standard utility-per-ruolo-EF: filtra le utility
               configurate per l'EF dell'operatore + ammesse al ruolo CLIENTE
               (intersezione `emittenti_fiscali_utilities` x
               `utilities_tipi_ruolo`). Pre-popolato da `defaultForm()` via
               `utilityDefaultId`; quando l'operatore sceglie il BA,
               `onBaSelected` sovrascrive con la utility canonical del BA. -->
          <UtilityPerRuoloSelect
            v-model="form.utility_id"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.contratti.field_utility')"
            :disabled="isEdit || isReadonly"
          />
        </div>
      </div>
      <!-- Ambito + Categoria cliente snapshot sulla stessa riga.
           Categoria editabile in create e in DRAFT, bloccata dopo
           attivazione (BE/non_editable_fields + trigger DB). -->
      <div class="form-grid-2col mt-1">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_ambito') }} <span v-if="!isEdit">*</span></label>
          <AmbitoContrattoSelect v-model="form.ambito"
            class="w-full" :disabled="isEdit && isLocked('ambito')" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_categoria_cliente_snapshot') }}</label>
          <LookupSelect
            v-model="form.categoria_cliente_id_snapshot"
            rel="anagrafiche.categorie_clienti"
            class="w-full"
            :placeholder="t('vendite.contratti.select_categoria_cliente')"
            show-clear
            :disabled="isEdit && isLocked('categoria_cliente_id_snapshot')"
          />
        </div>
      </div>

      <!-- Corsia di fatturazione: instradamento deciso PRIMA che il contratto
           entri in commessa; dopo il push il flag e' inerte e il DB respinge
           la modifica. Solo in MODIFICA e solo in bozza: la create non lo
           accetta ancora (whitelist della fn madre DB, brief al team) e in
           ATTIVO la PATCH ammette solo la data di fine validita'. -->
      <div v-if="isEdit" class="form-grid-2col mt-1">
        <div class="form-field">
          <label for="ctr-fatt-immediata">{{ t('vendite.contratti.field_fatturazione_immediata') }}</label>
          <div class="app-form-inline-toggle">
            <ToggleSwitch
              input-id="ctr-fatt-immediata"
              v-model="form.fatturazione_immediata"
              :disabled="isLocked('fatturazione_immediata') || isReadonly" />
            <small class="text-color-secondary">
              {{ t('vendite.contratti.fatturazione_immediata_hint') }}
            </small>
          </div>
        </div>
        <div class="form-field"></div>
      </div>

      <!-- === Validità === -->
      <h4 class="mt-3">{{ t('vendite.contratti.section_validita') }}</h4>
      <div class="form-grid-3col">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_data') }} *</label>
          <DatePicker :model-value="parseIsoDate(form.data)"
            @update:model-value="form.data = toIsoDate($event)"
            :disabled="isEdit && isLocked('data')"
            date-format="dd/mm/yy" show-icon class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_valido_dal') }} *</label>
          <DatePicker :model-value="parseIsoDate(form.valido_dal)"
            @update:model-value="form.valido_dal = toIsoDate($event)"
            :disabled="isEdit && isLocked('valido_dal')"
            date-format="dd/mm/yy" show-icon class="w-full" />
        </div>
        <!-- Campo valido_al condizionale per stato:
             - DRAFT: editabile come "Fine validita' (opz.)"
             - ATTIVO con valido_al impostato: readonly come "Cessazione
               programmata al {data}" (cessazione futura applicata via
               dialog Cessa, in attesa di scadere)
             - ATTIVO senza valido_al: nascosto (cessazione passa solo
               dal dialog dedicato)
             - CESSATO: readonly come "Data cessazione" -->
        <div class="form-field"
          v-if="!isEdit
            || detail?.stato_codice_interno === 'DRAFT'
            || detail?.stato_codice_interno === 'CESSATO'
            || (form.valido_al && detail?.stato_codice_interno === 'ATTIVO')">
          <label>
            {{ detail?.stato_codice_interno === 'CESSATO'
              ? t('vendite.contratti.field_data_cessazione')
              : detail?.stato_codice_interno === 'ATTIVO' && form.valido_al
                ? t('vendite.contratti.field_cessazione_programmata')
                : t('vendite.contratti.field_valido_al') }}
          </label>
          <DatePicker :model-value="parseIsoDate(form.valido_al)"
            @update:model-value="form.valido_al = toIsoDate($event)"
            :disabled="isEdit && isLocked('valido_al')"
            date-format="dd/mm/yy" show-icon show-button-bar class="w-full" />
        </div>
      </div>

      <!-- === Pricing (refactor modalita 2026-05-15) === -->
      <!-- Niente piu' SelectButton A/B/C: l'operatore compila campi opzionali
           (listino + variazione globale). La "forma" derivata e' un badge
           informativo readonly mostrato sopra in detail (composable
           `formaDerivata`). -->
      <h4 class="mt-3">{{ t('vendite.contratti.section_pricing') }}</h4>

      <!-- Badge forma derivata: visibile in EDIT come audit visivo del path. -->
      <Message
        v-if="isEdit && detail"
        :severity="formaDerivata === 'senza_listino' ? 'warn' : 'info'"
        :closable="false" size="small"
      >
        {{ t(`vendite.contratti.forma_${formaDerivata}_descrizione`) }}
      </Message>

      <div class="form-field">
        <label>{{ t('vendite.contratti.field_listino') }}</label>
        <!-- Refactor 2026-05-18 §4.4: lookup dedicato che esclude i listini
             senza versione ATTIVA. Pattern useGlobalLookup + Select, cache
             modulo-level. Niente piu' LookupSelect generico per non far
             apparire scelte che il save rifiuterebbe. -->
        <Select v-model="form.listino_id"
          :options="listiniLookup.items.value"
          :option-label="formatListinoOption"
          option-value="id"
          :loading="listiniLookup.loading.value"
          class="w-full"
          :placeholder="t('vendite.contratti.select_listino_opzionale')"
          show-clear
          filter
          @update:model-value="onListinoChange"
          :disabled="isEdit && (isLocked('listino_id') || righeCount > 0)" />
        <small v-if="isEdit && righeCount > 0 && !isLocked('listino_id')"
          style="color: var(--p-yellow-700, #b45309);">
          <i class="pi pi-exclamation-triangle" />
          {{ t('vendite.contratti.hint_listino_lock_righe', { n: righeCount }) }}
        </small>
        <small v-else class="text-color-secondary">
          {{ t('vendite.contratti.hint_listino_opzionale') }}
        </small>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_tipo_variazione') }}</label>
          <TipoVariazioneSelect v-model="form.tipo_variazione_globale"
            scope="contratto"
            show-clear
            class="w-full"
            :disabled="isEdit && isLocked('tipo_variazione_globale')" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_valore_variazione') }}</label>
          <InputNumber v-model="form.valore_variazione_globale" class="w-full"
            :min-fraction-digits="0" :max-fraction-digits="4" showButtons
            @update:model-value="onValoreVariazioneChange"
            :disabled="isEdit && isLocked('valore_variazione_globale')"
            :suffix="form.tipo_variazione_globale === 'PERCENTUALE' ? ' %' : ''" />
          <small class="text-color-secondary">{{ t('vendite.contratti.hint_valore_variazione') }}</small>
        </div>
      </div>

      <!-- Valuta: snapshot fissato al CREATE, immutabile in EDIT
           (allineato a preventivi/offerte). Pre-popolata da
           ApiContrattoFormDefaults via cascata BB resolve_valuta_default. -->
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_valuta') }}</label>
          <LookupSelect v-model="form.valuta_id" rel="config.valute" class="w-full"
            :placeholder="t('vendite.contratti.field_valuta')"
            :disabled="isEdit"
            show-clear />
        </div>
      </div>

      <!-- === Tipo/Classe utenza (editabile in BOZZA, readonly dopo) === -->
      <h4 class="mt-3">{{ t('vendite.contratti.section_utenza') }}</h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_tipo_utenza') }}</label>
          <LookupSelect v-model="form.utility_tipo_utenza_id" rel="config.tipi_utenze" class="w-full"
            :placeholder="t('vendite.contratti.select_tipo_utenza')" show-clear
            :disabled="isEdit && detail?.stato_codice_interno !== 'DRAFT'" />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_classe_utenza') }}</label>
          <LookupSelect v-model="form.utility_classe_utenza_id" rel="config.classi_utenze" class="w-full"
            :placeholder="t('vendite.contratti.select_classe_utenza')" show-clear
            :disabled="isEdit && detail?.stato_codice_interno !== 'DRAFT'" />
        </div>
      </div>

      <!-- Sezione indirizzi (UX v2, BB condiviso): solo il default,
           contatore "+N altri", pulsante "Indirizzi" che apre il drawer
           di gestione. Solo in EDIT (documento persistito). -->
      <DocumentoIndirizziSection
        v-if="isEdit && detail"
        dominio="contratti"
        :doc-id="contrattoId"
        :soggetto-ruolo-id="detail?.soggetto_ruolo_id ?? null"
        :istanza-utility-id="detail?.istanza_utility_id ?? null"
        :readonly="isReadonly" />

      <!-- L'area inline "Documenti generati" e' stata rimossa 2026-07-16
           (doppione): l'archivio PDF si consulta dal pulsante PDF in testata
           (EntityPdfButton -> PdfDocumentiSorgenteDialog, stesso BB con in
           piu' expand automatico e append allegati). Il seed pdf_mode
           ANNULLATO=ARCHIVE (regola unica 5 domini: annullare non cancella
           la storia) tiene il pulsante consultabile anche sugli annullati. -->


      <!-- Footer Salva/Annulla solo se editabile. La regola di dominio e':
           - CREATE (no detail): editabile
           - EDIT DRAFT: editabile
           - EDIT ATTIVO/CESSATO/ANNULLATO: NON editabile (solo Chiudi)
           NB: ATTIVO ammette tecnicamente modifica di `valido_al + meta`
           (cf. _CONTRATTO_PATCH_ALLOWED_BY_STATE BE + fn_available_actions_contratto
           che ritorna `can_edit_testata=true` per ATTIVO), ma l'unica modifica
           operativa in ATTIVO e' la cessazione programmata, gestita via
           dialog "Cessa contratto" dedicato (non via Salva del drawer).
           Quindi UX: mostrare solo Chiudi sgombera il footer da azioni
           ingannevoli ("Salva" semanticamente non porta a nessuna modifica
           visibile per l'operatore in ATTIVO). -->
      <FormFooter v-if="!isReadonly && (!detail || detail.stato_codice_interno === 'DRAFT')"
        :loading="loading" :disabled="!canSave"
        @save="handleSave" @cancel="onClose" />
      <!-- Fallback close-only: stati post-DRAFT o LETTURA. Footer dedicato
           con solo "Chiudi" (semantica completion, vs X in alto = dismiss).
           Pattern coerente con `feedback_drawer_footer_close_only` e
           PreventiviDrawer. -->
      <FormFooter v-else-if="detail" close-only @cancel="onClose" />
      </template>
    </div>

    <!-- Sub-drawer: gestione righe -->
    <ContrattoRigheDrawer
      v-if="isEdit && detail"
      :visible="righeVisible"
      @update:visible="v => righeVisible = v"
      :contratto-id="props.contrattoId"
      :contratto-forma="formaDerivata"
      :righe-iniziali="detail.righe || []"
      :contratto-numero="detail.numero"
      :contratto-cliente="detail.ba_ragione_sociale"
      :contratto-valido-dal="detail.valido_dal"
      :contratto-valido-al="detail.valido_al"
      :contratto-stato-codice="detail.stato_codice_interno"
      :contratto-stato-descrizione="detail.stato_descrizione"
      @changed="refreshDetail"
    />

    <!-- Sub-drawer note partizionate. Le righe sono passate per popolare il
         dropdown RIGA del form: detail.righe e' gia' caricato dal padre. -->
    <ContrattoNoteDrawer
      v-if="isEdit && detail"
      v-model:visible="noteDrawerVisible"
      :contratto-id="props.contrattoId"
      :righe="detail.righe || []"
    />

    <!-- Dialog attivazione contratto (transizione DRAFT → ATTIVO). Wrapper sul
         building block DocumentoEmissioneDialog: anteprima PDF + allegati,
         conferma orchestra atomic state + genera + allegati via /emetti/. -->
    <ContrattoEmissioneDialog
      v-if="isEdit && detail"
      v-model:visible="emissioneDialogVisible"
      :contratto="detail"
      :loading="emissioneLoading"
      @confirm="handleEmissioneConferma"
    />

    <!-- Dialog cessazione contratto: chiede la data di cessazione (default
         oggi) e fa POST cambia-stato {CESSATO, valido_al} in transazione BE.
         Comportamento data-driven:
         - data < oggi  -> cessazione immediata, stato CESSATO
         - data >= oggi -> cessazione programmata, stato resta ATTIVO -->
    <AppDialog v-model:visible="cessaDialogVisible"
      :header="cessazioneProgrammata
        ? t('vendite.contratti.cessa_dialog_titolo_programma')
        : t('vendite.contratti.cessa_dialog_titolo_immediata')"
      width="sm"
      :readonly="parentReadonly"
      :loading="loading"
      :save-disabled="!cessaDialogData || loading"
      :save-label="cessazioneProgrammata
        ? t('vendite.contratti.cessa_dialog_conferma_programma')
        : t('vendite.contratti.cessa_dialog_conferma_immediata')"
      :save-severity="cessazioneProgrammata ? 'warn' : 'danger'"
      @save="onConfermaCessazione">
      <div class="form-field">
        <label>{{ t('vendite.contratti.cessa_dialog_data') }}</label>
        <DatePicker v-model="cessaDialogData" date-format="dd/mm/yy"
          show-icon show-button-bar :min-date="cessaDialogMinDate" />
      </div>
      <Message :severity="cessazioneProgrammata ? 'info' : 'warn'"
        :closable="false" class="mt-1" size="small">
        {{ cessazioneProgrammata
          ? t('vendite.contratti.cessa_dialog_warning_programmata')
          : t('vendite.contratti.cessa_dialog_warning_immediata') }}
      </Message>
    </AppDialog>

  </Drawer>
</template>

