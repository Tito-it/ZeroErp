<script setup>
// Scopo: Drawer offerta commerciale — testata + sezione utility inline +
//        sub-drawer eccezioni + tab revisioni. State machine codificata FE
//        (BOZZA/EMESSA/ACCETTATA/RIFIUTATA/ANNULLATA/SUPERATA) finche' il
//        BE non espone `available_actions` come per contratti/preventivi.
//
// Pattern speculare a ContrattoDrawer (utility 1:1 inline in testata,
// listino + variazione globale PERCENTUALE, validita range). Drawer 3 tab
// (testata, eccezioni, revisioni) come da piano BE+FE rev. f §FE-3.
import { computed, nextTick, provide, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import AppDialog from '../../../core/components/AppDialog.vue'
import Drawer from 'primevue/drawer'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tab from 'primevue/tab'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import BillingAccountLookup from '../../../core/components/BillingAccountLookup.vue'
import DrawerActionsBar from '../../../core/components/DrawerActionsBar.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import FormFooter from '../../../core/components/FormFooter.vue'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import EmittenteFiscaleField from '../../../core/components/EmittenteFiscaleField.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { mapAvailableActionsToDrawerActions } from '../../../core/composables/useDrawerActions'
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../../core/composables/useDrawerDetailLoad'
import { useDrawerContentReady } from '../../../core/composables/useDrawerContentReady'
import { useEmittenteFiscaleField } from '../../../core/composables/useEmittenteFiscaleField'
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { useFetchVersion } from '../../../core/composables/useFetchVersion'
import { useGlobalLookup } from '../../../core/composables/useGlobalLookup'
import { useNotify } from '../../../core/composables/useNotify'
import { useRevisioniTab } from '../../../core/composables/useRevisioniTab'
import { useUtilityDefaultId } from '../../../core/composables/useUtilityDefaultId'
import {
  READONLY_KEY,
  useInjectReadonly,
} from '../../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS, TIPO_RUOLO } from '../../../core/constants'
import { NAV_ICONS } from '../../../core/navigation'
import { extractApiError, extractApiErrorCode } from '../../../core/utils/apiError'
import { displayDate, parseIsoDate, toDateString } from '../../../core/utils/date'
import { statoOffertaSeverity } from '../../../core/utils/severity'
import { getOffertaFormDefaults } from '../../api/formDefaults'
import { useBaFormDefaults } from '../../_shared/baDefaults/useBaFormDefaults'
import { lookupListiniSelezionabiliContratto } from '../../api/lookup'
import TipoVariazioneSelect from '../../components/TipoVariazioneSelect.vue'
import {
  STATI_OFFERTA_ANTEPRIMA_PDF,
  STATI_OFFERTA_APPEND_ALLEGATI,
  STATI_OFFERTA_CON_DOCUMENTO,
  STATI_OFFERTA_SEGNALA_SCADENZA,
  STATI_OFFERTA_TERMINALI,
} from '../constants'
import { useOfferteStore } from '../stores/offerte'
import OffertaEccezioniDrawer from './OffertaEccezioniDrawer.vue'
import OffertaNoteDrawer from './OffertaNoteDrawer.vue'
import OffertaEmissioneDialog from './dialogs/OffertaEmissioneDialog.vue'
import OffertaEsitoDialog from './dialogs/OffertaEsitoDialog.vue'
import OffertaPushDialog from './dialogs/OffertaPushDialog.vue'
import OffertaSuccessioneDialog from './dialogs/OffertaSuccessioneDialog.vue'
// Riuso read-only del drawer contratti per ispezionare il contratto sovrapposto
// dal dialog di successione (righe comprese). Read-only forzato via prop.
import ContrattoDrawer from '../../components/ContrattoDrawer.vue'
import EntityPdfButton from '../../../documenti/components/EntityPdfButton.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'

const { t } = useI18n()
const store = useOfferteStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()
const parentReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  offertaId: { type: Number, default: null },
  initialBillingAccount: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled', 'navigate-contratto'])

const isEdit = computed(() => props.mode === 'edit')

const detail = ref(null)
const form = ref({})
// Tab "Testata | Revisioni" — state + load con guard di race incapsulati nel
// building block `useRevisioniTab` (regola del 2, estratto a 2026-05-28
// insieme a PreventiviDrawer). Le revisioni hanno il loro guard di versione
// indipendente da `fv` (fgVersion del detail): sono fetch best-effort separate.
const revisioniTab = useRevisioniTab({
  load: (id) => store.loadRevisioni(id),
})
const { activeTab, revisioni } = revisioniTab

// State machine data-driven dal BE (Step 9b 2026-05-26:
// script.fn_available_actions_offerta + arricchimento `get_offerta`).
// Le capability `canEdit`, `availableActions`, `isLocked(field)` arrivano
// dal blob jsonb merged nel detail. Il drawer NON ricalcola stato lato
// client: legge la verita' BE. Pattern allineato a Contratto/Preventivo.
const stato = computed(() => detail.value?.stato_codice_interno || null)
// `useEntityCapabilities` espone anche `isLocked(field)` per granularita'
// campo-per-campo da `non_editable_fields`. Oggi non lo usiamo (il BE
// blocca tutta la testata fuori BOZZA, equivalente a `!canEdit`), ma resta
// pronto per future estensioni (es. "modificabile solo meta in EMESSA").
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })
const availableActions = caps.availableActions
const canEditTestata = caps.canEdit

// isReadonly cumulativo: OR tra permessi area e workflow lock (= !canEditTestata
// in edit mode). In create canEditTestata e' true per costruzione (l'offerta
// nasce in BOZZA, l'utente puo' compilare).
const isReadonly = computed(
  () => parentReadonly.value || (isEdit.value && !canEditTestata.value),
)
provide(READONLY_KEY, isReadonly)

// Discriminante terminale vs intermedio per la severity del banner: il BE
// espone `can_edit_testata=false` sia per EMESSA/ACCETTATA (intermedi, "passa
// al cambio stato") sia per RIFIUTATA/ANNULLATA/SUPERATA (terminali, "non
// puoi piu' fare nulla"). La lista locale distingue i due casi senza dover
// chiedere un flag in piu' al BE.
const isStatoTerminale = computed(
  () => STATI_OFFERTA_TERMINALI.includes(stato.value),
)

// Deferimento contenuto: i LookupSelect montano solo dopo l'animazione.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

// Lookup listini "selezionabili come riferimento contrattuale" — stesso
// pattern del contratto (refactor 2026-05-18 §4.4). L'offerta congela la
// versione del listino all'emissione: serve solo un listino che abbia
// almeno una versione ATTIVA al momento.
const listiniLookup = useGlobalLookup(
  'vendite.listini_selezionabili_contratto',
  lookupListiniSelezionabiliContratto,
  { immediate: true, transform: (r) => r.data.data },
)
function formatListinoOption(item) {
  if (!item) return ''
  return item.codice ? `${item.descrizione} (${item.codice})` : item.descrizione
}

// Defaults da profilo operatore (pattern identico a preventivi/contratti):
// - Emittente fiscale: derivato dal profilo (1-a-1 operatore->emittente
//   salvo admin globali multi-EF che vedono il Select). Pre-popolato in
//   CREATE per evitare il "buco" dell'INSERT senza emittente.
// - Utility: codice_interno DEFAULT_UTILITY in `config.parameters`,
//   risolto a id locale dal composable. Pre-popolato in CREATE per
//   filtrare automaticamente il BillingAccountLookup sull'utility
//   dell'operatore (UX: l'operatore vede subito solo i BA della sua
//   utility tipica).
const { defaultEmittenteId } = useEmittenteFiscaleField()
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

// Sub-drawer + dialogs.
const eccezioniDrawerVisible = ref(false)
const noteDrawerVisible = ref(false)
const emissioneDialogVisible = ref(false)
const esitoDialogVisible = ref(false)
const esitoDialogModalita = ref('ACCETTATA') // ACCETTATA | RIFIUTATA | ANNULLATA
const pushDialogVisible = ref(false)
// Dialog "contratto gia' generato" — aperto se l'offerta ha gia' un contratto
// collegato (detail.contratto_id valorizzato dal BE, idempotenza Pattern A).
// Si apre proattivamente al click "Push verso contratto" se gia' presente,
// oppure reattivamente se il BE solleva E_OFFERTA_CONTRATTO_GIA_GENERATO
// (race condition: contratto creato in altro tab tra fetch detail e push).
const giaGeneratoDialogVisible = ref(false)
// Dialog di successione — aperto se il push fallisce con
// E_CONTRATTO_OVERLAP_ESISTENTE (esiste un contratto attivo sovrapposto).
// `contrattoSovrapposto` e' il contratto in conflitto (read da BE);
// `pushPraticaId` conserva la pratica scelta nel push dialog per il
// re-push con chiudi_esistente=true.
const successioneDialogVisible = ref(false)
const contrattoSovrapposto = ref(null)
const pushPraticaId = ref(null)
// Ispezione read-only del contratto sovrapposto (riuso ContrattoDrawer). Il
// dialog di successione viene nascosto durante l'ispezione e ri-aperto alla
// chiusura: `contrattoSovrapposto`/`pushPraticaId` restano valorizzati, quindi
// al ritorno la conferma successione funziona ancora.
const contrattoIspezioneVisible = ref(false)
const contrattoIspezioneId = ref(null)

// Guard di versione per i fetch del detail (apertura/chiusura/cambio-id
// rapide). Incrementato anche quando offertaId cambia con drawer ancora
// aperto (caso rev N+1 dopo crea_revisione: il parent fa editRow senza
// chiudere il drawer). Il guard delle revisioni e' indipendente e vive
// dentro `revisioniTab` (useFetchVersion interno).
const fv = useFetchVersion()

function defaultForm() {
  return {
    // Emittente derivato dal profilo (1-a-1 operatore->EF, salvo admin
    // multi-EF). `defaultEmittenteId` e' un ref reattivo; alla prima
    // apertura del drawer in CREATE puo' essere null finche' il profilo
    // non e' caricato: il watcher loadOrReset lo legge gia' valorizzato.
    emittente_fiscale_id: defaultEmittenteId.value ?? null,
    billing_account_id: null,
    billing_account_obj: null,
    istanza_utility_id: null,
    // Utility default da DEFAULT_UTILITY parameter (codice_interno
    // risolto a id locale). Pre-filtra il BillingAccountLookup
    // sull'utility dell'operatore; viene sovrascritta da onBaSelected
    // quando l'operatore sceglie il BA (e' la utility canonical del BA).
    utility_id: utilityDefaultId.value,
    listino_id: null,
    listino_versione_id: null,
    valuta_id: null,
    tipo_variazione_globale: null,
    valore_variazione_globale: null,
    validita_dal: toDateString(new Date()),
    validita_al: null,
    // Sezione utility inline (mirror contratti_utilities)
    utility_tipo_utenza_id: null,
    utility_classe_utenza_id: null,
    utility_param_1_num: null,
    utility_param_2_txt: null,
    utility_istanza_dati_precontrattuali_id: null,
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
  // Reset revisioni + tab attivo: il composable gestisce anche
  // l'invalidate del proprio guard di versione (vedi useRevisioniTab).
  revisioniTab.reset()
}

function populateFromDetail(d) {
  form.value = {
    emittente_fiscale_id: d.emittente_fiscale_id,
    billing_account_id: d.billing_account_id,
    billing_account_obj: d.billing_account_display ? {
      id: d.billing_account_id,
      ragione_sociale: d.billing_account_display,
      utility_codice: d.utility_codice || null,
      utility_descrizione: d.utility_display || null,
      pdp: d.pdp || null,
    } : null,
    istanza_utility_id: d.istanza_utility_id,
    utility_id: d.utility_id,
    listino_id: d.listino_id,
    listino_versione_id: d.listino_versione_id,
    valuta_id: d.valuta_id,
    tipo_variazione_globale: d.tipo_variazione_globale,
    valore_variazione_globale: d.valore_variazione_globale,
    validita_dal: d.validita_dal,
    validita_al: d.validita_al,
    utility_tipo_utenza_id: d.utility?.tipo_utenza_id || null,
    utility_classe_utenza_id: d.utility?.classe_utenza_id || null,
    utility_param_1_num: d.utility?.param_1_num ?? null,
    utility_param_2_txt: d.utility?.param_2_txt || null,
    utility_istanza_dati_precontrattuali_id: d.utility?.istanza_dati_precontrattuali_id || null,
  }
}

function toIsoDate(d) {
  return typeof d === 'string' ? d : toDateString(d)
}

// Coerenza coppia variazione globale: tipo e valore entrambi NULL o entrambi
// valorizzati (vincolo BE). Reset simmetrico: cancellare il valore azzera
// anche il tipo per evitare un "tipo orfano" che bloccherebbe canSave senza
// feedback visivo al campo (l'operatore vede tipo valorizzato e si chiede
// perche' Salva e' disabilitato). Inserire un valore pre-fill il tipo a
// PERCENTUALE (default coerente con vendite.contratti.tipo_variazione).
function onValoreVariazioneChange(nuovoValore) {
  if (nuovoValore == null || nuovoValore === '') {
    form.value.tipo_variazione_globale = null
  } else if (!form.value.tipo_variazione_globale) {
    form.value.tipo_variazione_globale = 'PERCENTUALE'
  }
}

function onListinoChange(nuovoListinoId) {
  if (!nuovoListinoId) {
    form.value.tipo_variazione_globale = null
    form.value.valore_variazione_globale = null
    form.value.listino_versione_id = null
  }
}

function onBaSelected(item) {
  if (!item) {
    form.value.billing_account_id = null
    form.value.billing_account_obj = null
    form.value.istanza_utility_id = null
    // Ripristina il default utility quando si pulisce il BA: l'operatore
    // mantiene il filtro lookup BA sull'utility tipica del proprio EF
    // invece di tornare a "vedo tutti i BA". Coerente col `defaultForm()`
    // che pre-popola `utility_id` da `utilityDefaultId.value` in CREATE.
    form.value.utility_id = utilityDefaultId.value
    return
  }
  form.value.billing_account_id = item.id
  form.value.billing_account_obj = item
  form.value.istanza_utility_id = item.istanza_utility_id || null
  form.value.utility_id = item.utility_id || null
}

// Auto-fill valuta dal form-defaults BE (BB resolve_valuta_default), al cambio
// BA in CREATE: la valuta del BA vince (regola di coerenza dominio). Watcher
// condiviso `useBaFormDefaults` con guard latest-wins inclusa.
useBaFormDefaults({ form, isEdit, fetchDefaults: getOffertaFormDefaults })

// Carica/resetta su apertura/chiusura/cambio-id.
// Watch composito [visible, offertaId]: scatena ricaricamento sia quando il
// drawer si apre, sia quando il padre cambia offertaId con drawer ancora
// aperto (rev N+1 dopo crea_revisione e' lo scenario tipico). Senza il
// secondo elemento, editRow al volo non innescherebbe il fetch del nuovo
// detail e il drawer mostrerebbe la rev vecchia con i bottoni della nuova.
async function loadOrReset() {
  if (!props.visible) {
    fv.invalidate()
    revisioniTab.reset()
    return
  }
  const t = fv.tag()

  // Reset tab attivo + revisioni sempre, su qualunque apertura (EDIT e
  // CREATE): senza questo, riaprendo il drawer su un'altra offerta il tab
  // restava quello dell'apertura precedente (es. chiudo su "Revisioni",
  // riapro su una nuova offerta → si vede "Revisioni" invece di "Testata").
  // `resetForm` lo fa solo nel ramo CREATE, quindi qui copre anche
  // EDIT/cambio-offertaId.
  revisioniTab.reset()

  if (isEdit.value && props.offertaId) {
    const d = await loadDetailOrClose(() => store.fetchDetail(props.offertaId))
    if (!fv.isCurrent(t)) return
    if (d == null) return  // dettaglio non accessibile → drawer già chiuso
    detail.value = d
    populateFromDetail(d)
    // revisioniTab usa il proprio guard interno (useFetchVersion incluso).
    revisioniTab.loadRevisioni(props.offertaId)
  } else {
    // CREATE: precarica DEFAULT_UTILITY (codice_interno -> id locale)
    // prima di resetForm cosi' che il defaultForm() ne legga il valore
    // gia' risolto. L'emittente fiscale arriva dal profilo gia' caricato
    // in `useAuthStore` (zero round-trip).
    await loadUtilityDefault()
    if (!fv.isCurrent(t)) return
    resetForm()
    if (props.initialBillingAccount?.id) {
      onBaSelected(props.initialBillingAccount)
    } else {
      // CREATE senza BA: pre-popoliamo la valuta dal BB resolve_valuta_default
      // lato BE (catena EF utente → gestore). Mirror PreventiviDrawer.
      // Se BA viene selezionato dopo, il watch su billing_account_id
      // sovrascrive col valore BA-resolved.
      try {
        const res = await getOffertaFormDefaults(null)
        if (!fv.isCurrent(t)) return
        const data = res?.data?.data
        if (data && form.value.valuta_id == null && data.valuta_id != null) {
          form.value.valuta_id = data.valuta_id
        }
      } catch {
        // Best-effort: trigger DB risolverà la valuta al save.
      }
    }
  }
}
watch(() => [props.visible, props.offertaId], loadOrReset)

// Validazione FE create: campi obbligatori secondo whitelist BE.
const canSave = computed(() => {
  if (isReadonly.value) return false
  const f = form.value
  const hasTipo = !!f.tipo_variazione_globale
  const hasValore = f.valore_variazione_globale != null && f.valore_variazione_globale !== ''
  if (hasTipo !== hasValore) return false
  if (isEdit.value) return true
  return !!(f.emittente_fiscale_id
    && f.billing_account_id
    && f.istanza_utility_id
    && f.utility_id
    && f.listino_id
    && f.validita_dal)
})

function buildPayload() {
  const f = form.value
  // Guard difensivo: in EDIT solo se la testata e' editabile (canEditTestata
  // BE-driven). Il footer Salva ha gia' `v-if="!isReadonly"` quindi questo
  // branch non dovrebbe essere mai raggiunto in pratica; ritorniamo dict
  // vuoto per safety, evitando PATCH inutili.
  if (isEdit.value && !canEditTestata.value) return {}
  return {
    emittente_fiscale_id: f.emittente_fiscale_id,
    billing_account_id: f.billing_account_id,
    istanza_utility_id: f.istanza_utility_id,
    utility_id: f.utility_id,
    listino_id: f.listino_id,
    listino_versione_id: f.listino_versione_id || null,
    // Valuta inviata SOLO in CREATE: snapshot immutabile post-INSERT.
    // In EDIT (PATCH) il BE rifiuta come unknown_key. Se f.valuta_id è
    // null in CREATE, il trigger DB la risolve via fn_get_valuta_id.
    ...(isEdit.value ? {} : { valuta_id: f.valuta_id || null }),
    tipo_variazione_globale: f.tipo_variazione_globale || null,
    valore_variazione_globale: f.valore_variazione_globale != null && f.valore_variazione_globale !== ''
      ? String(f.valore_variazione_globale)
      : null,
    validita_dal: toIsoDate(f.validita_dal),
    validita_al: f.validita_al ? toIsoDate(f.validita_al) : null,
  }
}

function buildUtilityPayloadFromForm() {
  const f = form.value
  return {
    istanza_utility_id: f.istanza_utility_id,
    utility_id: f.utility_id,
    tipo_utenza_id: f.utility_tipo_utenza_id || null,
    classe_utenza_id: f.utility_classe_utenza_id || null,
    param_1_num: f.utility_param_1_num != null && f.utility_param_1_num !== ''
      ? String(f.utility_param_1_num) : null,
    param_2_txt: f.utility_param_2_txt || null,
    istanza_dati_precontrattuali_id: f.utility_istanza_dati_precontrattuali_id || null,
  }
}

// Costruisce il sub-oggetto `utility` opzionale per le chiamate atomiche
// CREATE/UPDATE testata. Restituisce null se i campi business non sono
// valorizzati (nessuna ragione di toccare il record satellite).
function buildUtilityInline() {
  const u = buildUtilityPayloadFromForm()
  if (!u.istanza_utility_id || !u.utility_id) return null
  return {
    // istanza_utility_id/utility_id sono richiesti dal BE in create della
    // utility; nella UPDATE vengono ignorati perche' immutabili (lo split
    // BE filtra solo i campi business sulla whitelist update).
    istanza_utility_id: u.istanza_utility_id,
    utility_id: u.utility_id,
    tipo_utenza_id: u.tipo_utenza_id,
    classe_utenza_id: u.classe_utenza_id,
    param_1_num: u.param_1_num,
    param_2_txt: u.param_2_txt,
    istanza_dati_precontrattuali_id: u.istanza_dati_precontrattuali_id,
  }
}

async function handleSave() {
  // CREATE e UPDATE seguono lo stesso pattern atomico: testata + utility
  // 1:1 in un singolo round-trip con `utility: {...}` inline. Il BE fa
  // l'upsert dentro la stessa transaction.atomic() (mirror del pattern
  // ContrattoDrawer). Niente piu' fallimento parziale ne' .catch() silenziosi.
  const payload = buildPayload()
  const utilityInline = buildUtilityInline()
  if (utilityInline) payload.utility = utilityInline

  const isCreate = !isEdit.value
  const result = await execute(
    () => isCreate
      ? store.create(payload)
      : store.update(props.offertaId, payload),
    {
      successMessage: isCreate
        ? t('vendite.offerte.creata')
        : t('vendite.offerte.salvata'),
    },
  )
  if (result !== null) {
    if (!isCreate) await refreshDetail()
    emit('saved', result)
  }
}

async function refreshDetail() {
  if (!props.offertaId) return
  // Guard `fv` (useFetchVersion): protegge contro l'apply di un detail stantio
  // se l'operatore chiude/cambia offerta mentre il fetch e' in volo. Stesso
  // pattern del watcher loadOrReset.
  const t = fv.tag()
  const d = await store.fetchDetail(props.offertaId)
  if (!fv.isCurrent(t)) return
  detail.value = d
  populateFromDetail(d)
}

// Reload revisioni: thin wrapper su `revisioniTab.loadRevisioni` che ha gia'
// guard di versione interno (useFetchVersion). Esposto per i callsite che
// vogliono ricaricare solo le revisioni (post-save, post-revisione).
function reloadRevisioni() {
  if (!props.offertaId) return
  revisioniTab.loadRevisioni(props.offertaId)
}

// --- Dispatch azioni data-driven ---
//
// `mapAvailableActionsToDrawerActions` produce le entry kind:'state' dalla
// lista BE (script.fn_available_actions_offerta). Il callback unico
// `onActionDispatch` riceve l'action raw e fa routing sul `key`:
//   - emetti                -> OffertaEmissioneDialog
//   - annulla/accetta/rifiuta -> OffertaEsitoDialog (modalita = target_state
//     della transizione corrispondente)
//   - crea_revisione        -> confirmAction + chiamata store
//   - push_contratto        -> OffertaPushDialog (con guard proattivo
//     contratto_id per la race-condition cross-tab)
// `requires_motivazione` arriva dalla fn DB ma non viene letta qui: la
// motivazione obbligatoria e' enforced dal dialog esito + dal BE
// (motivazione_rifiuto NOT NULL su RIFIUTATA/ANNULLATA).
function onActionDispatch(action) {
  switch (action.key) {
    case 'emetti':
      emissioneDialogVisible.value = true
      return
    case 'annulla':
    case 'accetta':
    case 'rifiuta':
      // target_state della fn DB e' lo stato di destinazione (ANNULLATA /
      // ACCETTATA / RIFIUTATA). Coincide con la modalita' del dialog esito.
      esitoDialogModalita.value = action.target_state
      esitoDialogVisible.value = true
      return
    case 'crea_revisione':
      confirmAction({
        header: t('vendite.offerte.crea_revisione_titolo'),
        message: t('vendite.offerte.crea_revisione_messaggio'),
        acceptLabel: t('vendite.offerte.crea_revisione_conferma'),
        onAccept: async () => {
          const result = await execute(
            () => store.creaRevisione(props.offertaId),
            { successMessage: t('vendite.offerte.revisione_creata') },
          )
          if (result !== null) {
            // Apri la nuova rev nel drawer: emit `saved` con la nuova rev
            // permette al parent (OfferteView) di passare al nuovo id.
            emit('saved', result)
          }
        },
      })
      return
    case 'push_contratto':
      // Guard proattivo: la fn DB non ritorna l'azione se il contratto e'
      // gia' generato, ma manteniamo il check FE come safety net per la
      // race condition (un altro tab/operatore ha pushato fra fetch e click).
      if (detail.value?.contratto_id) {
        giaGeneratoDialogVisible.value = true
        return
      }
      pushDialogVisible.value = true
      return
    default:
      // Action key sconosciuta: log + no-op. Capita se il BE aggiunge un'azione
      // nuova e il FE non e' stato aggiornato. Difensivo, non bloccante.
      console.warn(`OffertaDrawer: action key non gestita: ${action.key}`)
  }
}

// Reazione al codice errore: la race condition resta possibile (contratto
// creato in altro tab tra fetch detail e push). In quel caso il BE solleva
// `E_OFFERTA_CONTRATTO_GIA_GENERATO`: ricarichiamo il detail per leggere
// `contratto_id` aggiornato e mostriamo il dialog parlante.
async function handleGiaGeneratoFromBackend() {
  await refreshDetail()
  giaGeneratoDialogVisible.value = true
}

function onApriContrattoEsistente() {
  giaGeneratoDialogVisible.value = false
  if (detail.value?.contratto_id) {
    emit('navigate-contratto', { contrattoId: detail.value.contratto_id })
  }
}

// Apre il contratto sovrapposto in sola lettura (ContrattoDrawer read-only,
// righe incluse) per ispezione dal dialog di successione: nasconde il dialog
// e apre il drawer. Niente navigazione → l'offerta resta montata sotto.
function onIspezionaContrattoSovrapposto({ contrattoId }) {
  if (!contrattoId) return
  successioneDialogVisible.value = false
  // Prima monta il drawer (v-if sull'id) con `visible` ancora false, poi in
  // nextTick lo apre: ContrattoDrawer carica il detail nel watch su `visible`
  // (transizione false→true), NON immediate. Settare id+visible nello stesso
  // tick monterebbe il drawer già visibile → il watch non scatterebbe → vuoto.
  contrattoIspezioneId.value = contrattoId
  nextTick(() => { contrattoIspezioneVisible.value = true })
}

// Chiusura del drawer di ispezione: ri-apre il dialog di successione cosi'
// l'operatore conferma/annulla con il contesto ancora valorizzato.
function onChiudiIspezioneContratto(visible) {
  contrattoIspezioneVisible.value = visible
  if (!visible) {
    contrattoIspezioneId.value = null
    // Ri-apre la successione solo se il push è ancora in corso (contratto in
    // conflitto noto): evita riaperture spurie se lo stato è stato resettato.
    if (contrattoSovrapposto.value) successioneDialogVisible.value = true
  }
}

// Handler delegati ai dialog ---

async function handleEmissioneConferma(payload = {}) {
  // payload.files = allegati staged nel DocumentoEmissioneDialog. L'emissione
  // genera+persiste il documento + allegati lato BE (transazione atomica).
  const allegati = payload?.files || []
  const result = await execute(
    () => store.emetti(props.offertaId, { allegati }),
    { successMessage: t('vendite.offerte.emessa') },
  )
  if (result !== null) {
    emissioneDialogVisible.value = false
    await refreshDetail()
    await reloadRevisioni()
  }
}

async function handleEsitoConferma({ esito, motivazione }) {
  let action
  if (esito === 'ANNULLATA') {
    action = () => store.annulla(props.offertaId, { motivazione })
  } else {
    action = () => store.registraEsito(props.offertaId, { esito, motivazione })
  }
  const result = await execute(action, {
    successMessage: t('vendite.offerte.esito_salvato'),
  })
  if (result !== null) {
    esitoDialogVisible.value = false
    await refreshDetail()
    await reloadRevisioni()
  }
}

async function handlePushConferma({ praticaId }) {
  pushPraticaId.value = praticaId
  await runPush({ praticaId, chiudiEsistente: false })
}

// Conferma successione: l'operatore ha visto il contratto in conflitto e
// accetta di chiuderlo. Ri-esegue il push con chiudi_esistente=true,
// riusando la pratica eventualmente scelta nel push dialog.
async function handleSuccessioneConferma() {
  await runPush({ praticaId: pushPraticaId.value, chiudiEsistente: true })
}

// Esegue il push gestendo i due esiti "parlanti":
//   - E_OFFERTA_CONTRATTO_GIA_GENERATO -> dialog "gia' generato" (idempotenza)
//   - E_CONTRATTO_OVERLAP_ESISTENTE    -> dialog di successione (overlap)
// Bypass useApiHandler.execute() perche' serve routing sull'error code:
// execute() inghiotte l'errore e ritorna null senza esporre il code.
async function runPush({ praticaId, chiudiEsistente }) {
  loading.value = true
  try {
    const data = await store.pushAContratto(props.offertaId, {
      praticaId,
      chiudiEsistente,
    })
    notify.success(t('vendite.offerte.push_eseguito'))
    pushDialogVisible.value = false
    successioneDialogVisible.value = false
    contrattoSovrapposto.value = null
    pushPraticaId.value = null
    await refreshDetail()
    emit('navigate-contratto', { contrattoId: data.contratto_id })
  } catch (err) {
    const code = extractApiErrorCode(err)
    if (code === 'E_OFFERTA_CONTRATTO_GIA_GENERATO') {
      pushDialogVisible.value = false
      await handleGiaGeneratoFromBackend()
    } else if (code === 'E_CONTRATTO_OVERLAP_ESISTENTE') {
      // Overlap: chiudiamo il push dialog e apriamo quello di successione
      // con il contratto in conflitto (read-only dal BE).
      pushDialogVisible.value = false
      contrattoSovrapposto.value = await store.loadContrattoSovrapposto(props.offertaId)
      successioneDialogVisible.value = true
    } else {
      notify.error(extractApiError(err, t('vendite.offerte.push_errore_generico')))
    }
  } finally {
    loading.value = false
  }
}

// Barra azioni del drawer: composizione di
//   1) Transizioni di stato data-driven dal BE
//      (script.fn_available_actions_offerta, mapped 1:1 in azioni
//      `kind:'state'` con label/icona/severity dal jsonb).
//   2) Manage action `manage-eccezioni` per il sub-drawer eccezioni
//      (master-detail inline). Allineato al pattern ContrattoDrawer:
//      l'eccezione vive in un sub-drawer dedicato col proprio CRUD, non
//      in una tab del drawer principale (UX UI 2026-05-26).
//   3) Manage action `manage-note` per il sub-drawer note partizionate.
const drawerActions = computed(() => {
  if (!isEdit.value || !detail.value) return []
  const eccCount = detail.value.eccezioni?.length ?? 0
  return [
    // Read-only puro (permesso LETTURA / pannello split): niente azioni di
    // stato (emetti/accetta/rifiuta/push/revisione). Restano i pannelli
    // gestisci-eccezioni/note (sub-drawer in sola lettura).
    ...mapAvailableActionsToDrawerActions({
      availableActions,
      t,
      onAction: onActionDispatch,
      readonly: parentReadonly.value,
    }),
    {
      key: 'manage-eccezioni',
      kind: 'manage',
      label: t('vendite.offerte.gestisci_eccezioni'),
      icon: MANAGE_ICONS.RIGHE,
      badge: eccCount,
      command: () => { eccezioniDrawerVisible.value = true },
    },
    {
      key: 'manage-note',
      kind: 'manage',
      label: t('vendite.offerte.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => { noteDrawerVisible.value = true },
    },
  ]
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
    @update:visible="(val) => emit('update:visible', val)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('vendite.offerte.titolo_drawer')"
        :icon="NAV_ICONS.OFFERTE"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">

        <template v-if="isEdit && detail">
          <DrawerEntityHeader>
            <Tag :value="detail.codice" severity="secondary" />
            <span v-if="detail.revisione_numero > 1" class="app-drawer-header-muted">
              rev.{{ detail.revisione_numero }}
            </span>
            <span v-if="detail.data_emissione" class="app-drawer-header-muted">
              {{ displayDate(detail.data_emissione) }}
            </span>
            <Tag
              v-if="detail.is_scaduta && STATI_OFFERTA_SEGNALA_SCADENZA.includes(stato)"
              :value="t('vendite.offerte.badge_scaduta')"
              severity="warn"
            />
            <template #status>
              <Tag
                :value="detail.stato_descrizione"
                :severity="statoOffertaSeverity(stato)"
              />
            </template>
          </DrawerEntityHeader>

          <DrawerActionsBar :actions="drawerActions">
            <template #suffix>
              <EntityPdfButton
                :sorgente-code="SORGENTE_CODES.OFFERTA_COMMERCIALE"
                :entity-id="props.offertaId"
                :stato-codice="detail.stato_codice_interno"
                :stati-preview="STATI_OFFERTA_ANTEPRIMA_PDF"
                :stati-con-documento="STATI_OFFERTA_CON_DOCUMENTO"
                :stati-append-allegati="STATI_OFFERTA_APPEND_ALLEGATI"
                i18n-prefix="vendite.offerte.pdf"
                :dialog-title="detail.codice
                  ? t('vendite.offerte.pdf.dialog_title', { codice: detail.codice })
                  : ''"
              />
            </template>
          </DrawerActionsBar>

          <Message
            v-if="isStatoTerminale"
            severity="warn"
            :closable="false"
            size="small"
            class="mt-2"
          >
            {{ t('vendite.offerte.banner_stato_terminale', { stato: detail.stato_descrizione }) }}
          </Message>
          <Message
            v-else-if="!canEditTestata"
            severity="info"
            :closable="false"
            size="small"
            class="mt-2"
          >
            {{ t('vendite.offerte.banner_locked_post_bozza', { stato: detail.stato_descrizione }) }}
          </Message>
        </template>

        <Tabs v-model:value="activeTab">
          <TabList>
            <Tab value="testata">{{ t('vendite.offerte.tab_testata') }}</Tab>
            <!-- Tab "Eccezioni" rimossa (UX UI 2026-05-26): l'entry-point
                 e' il bottone "Gestisci eccezioni" nella DrawerActionsBar
                 (con badge counter), che apre il sub-drawer master-detail
                 dedicato. Pattern allineato a ContrattoDrawer. -->
            <Tab value="revisioni" :disabled="!isEdit">
              {{ t('vendite.offerte.tab_revisioni') }}
              <span v-if="isEdit && revisioni.length">({{ revisioni.length }})</span>
            </Tab>
          </TabList>

          <TabPanels>
            <!-- ====================== TAB TESTATA ====================== -->
            <TabPanel value="testata">

              <h4>{{ t('vendite.offerte.section_emittente') }}</h4>
              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_emittente_fiscale') }} <span v-if="!isEdit">*</span></label>
                  <!-- Campo emittente fiscale auto-adattivo (pattern preventivi/contratti):
                       - edit                 -> testo read-only dal record (codice + RS denormalizzati)
                       - create + operatore   -> testo read-only dal profilo (derivato 1-a-1)
                       - create + admin glob. -> Select sugli EF disponibili
                       In CREATE per operatore non-admin il valore arriva da
                       `useEmittenteFiscaleField().defaultEmittenteId`. -->
                  <EmittenteFiscaleField
                    v-model="form.emittente_fiscale_id"
                    :record="detail"
                    :is-edit="isEdit"
                    :disabled="isReadonly"
                  />
                </div>
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_utility') }} <span v-if="!isEdit">*</span></label>
                  <!-- Building block standard utility-per-ruolo-EF
                       (`UtilityPerRuoloSelect`). Filtra le utility configurate
                       per l'EF dell'operatore + ammesse al ruolo CLIENTE
                       (intersezione `emittenti_fiscali_utilities` x
                       `utilities_tipi_ruolo`). Pre-popolata dal `defaultForm()`
                       via `utilityDefaultId` (parametro `DEFAULT_UTILITY`,
                       codice_interno -> id locale). Quando l'operatore sceglie
                       il BA, `onBaSelected` sovrascrive con la utility canonical
                       del BA (coerenza FK garantita); se l'operatore pulisce
                       il BA, ripristiniamo il default per mantenere il filtro
                       lookup BA sull'utility tipica. -->
                  <UtilityPerRuoloSelect
                    v-model="form.utility_id"
                    :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
                    :placeholder="t('vendite.offerte.field_utility')"
                    :disabled="isReadonly"
                  />
                </div>
              </div>

              <h4 class="mt-3">{{ t('vendite.offerte.section_cliente') }}</h4>
              <div class="form-field">
                <label>{{ t('vendite.offerte.field_billing_account') }} <span v-if="!isEdit">*</span></label>
                <!-- `utility-id` (da utilityDefaultId in CREATE) pre-filtra
                     il lookup BA sull'utility dell'operatore. Lookup ricco
                     (3 righe: ragione sociale + codice + PDP) — sta a tutta
                     larghezza in una propria riga. -->
                <BillingAccountLookup
                  v-if="!isEdit"
                  :model-value="form.billing_account_obj"
                  :utility-id="form.utility_id"
                  :placeholder="t('vendite.offerte.select_billing_account')"
                  @update:model-value="onBaSelected"
                />
                <InputText
                  v-else
                  :model-value="detail?.billing_account_display"
                  disabled
                  class="w-full"
                />
              </div>

              <h4 class="mt-3">{{ t('vendite.offerte.section_listino') }}</h4>
              <div class="form-field">
                <label>{{ t('vendite.offerte.field_listino') }} <span v-if="!isEdit">*</span></label>
                <Select
                  v-model="form.listino_id"
                  :options="listiniLookup.items.value"
                  :option-label="formatListinoOption"
                  option-value="id"
                  :loading="listiniLookup.loading.value"
                  class="w-full"
                  :placeholder="t('vendite.offerte.select_listino')"
                  show-clear
                  filter
                  :disabled="isReadonly"
                  @update:model-value="onListinoChange"
                />
                <small v-if="isEdit && detail?.listino_versione_codice"
                  class="text-color-secondary">
                  {{ t('vendite.offerte.hint_versione_fissata', { codice: detail.listino_versione_codice }) }}
                </small>
              </div>

              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_tipo_variazione') }}</label>
                  <TipoVariazioneSelect
                    v-model="form.tipo_variazione_globale"
                    scope="contratto"
                    show-clear
                    class="w-full"
                    :disabled="isReadonly"
                  />
                </div>
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_valore_variazione') }}</label>
                  <InputNumber
                    v-model="form.valore_variazione_globale"
                    class="w-full"
                    :min-fraction-digits="0"
                    :max-fraction-digits="4"
                    show-buttons
                    :disabled="isReadonly"
                    :suffix="form.tipo_variazione_globale === 'PERCENTUALE' ? ' %' : ''"
                    @update:model-value="onValoreVariazioneChange"
                  />
                </div>
              </div>

              <!-- Valuta: snapshot fissato al CREATE, immutabile in EDIT
                   (allineato a preventivi/contratti). Pre-popolata da
                   ApiOffertaFormDefaults via cascata BB resolve_valuta_default. -->
              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_valuta') }}</label>
                  <LookupSelect
                    v-model="form.valuta_id"
                    rel="config.valute"
                    class="w-full"
                    :placeholder="t('vendite.offerte.field_valuta')"
                    :disabled="isReadonly || isEdit"
                    show-clear
                  />
                </div>
              </div>

              <h4 class="mt-3">{{ t('vendite.offerte.section_validita') }}</h4>
              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_validita_dal') }} <span v-if="!isEdit">*</span></label>
                  <DatePicker
                    :model-value="parseIsoDate(form.validita_dal)"
                    :disabled="isReadonly"
                    date-format="dd/mm/yy"
                    show-icon
                    class="w-full"
                    @update:model-value="form.validita_dal = toIsoDate($event)"
                  />
                </div>
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_validita_al') }}</label>
                  <DatePicker
                    :model-value="parseIsoDate(form.validita_al)"
                    :disabled="isReadonly"
                    date-format="dd/mm/yy"
                    show-icon
                    show-button-bar
                    class="w-full"
                    @update:model-value="form.validita_al = toIsoDate($event)"
                  />
                </div>
              </div>

              <!-- === Utility inline (mirror ContrattoDrawer) === -->
              <h4 class="mt-3">{{ t('vendite.offerte.section_utenza') }}</h4>
              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_tipo_utenza') }}</label>
                  <LookupSelect
                    v-model="form.utility_tipo_utenza_id"
                    rel="config.tipi_utenze"
                    class="w-full"
                    :placeholder="t('vendite.offerte.select_tipo_utenza')"
                    show-clear
                    :disabled="isReadonly"
                  />
                </div>
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_classe_utenza') }}</label>
                  <LookupSelect
                    v-model="form.utility_classe_utenza_id"
                    rel="config.classi_utenze"
                    class="w-full"
                    :placeholder="t('vendite.offerte.select_classe_utenza')"
                    show-clear
                    :disabled="isReadonly"
                  />
                </div>
              </div>
              <div class="form-grid-2col">
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_param_1_num') }}</label>
                  <InputNumber
                    v-model="form.utility_param_1_num"
                    class="w-full"
                    :min-fraction-digits="0"
                    :max-fraction-digits="6"
                    :disabled="isReadonly"
                  />
                </div>
                <div class="form-field">
                  <label>{{ t('vendite.offerte.field_param_2_txt') }}</label>
                  <InputText
                    v-model="form.utility_param_2_txt"
                    class="w-full"
                    :disabled="isReadonly"
                  />
                </div>
              </div>

              <!-- Motivazione (sola lettura, valorizzata su RIFIUTATA/ANNULLATA) -->
              <template v-if="isEdit && detail?.motivazione_rifiuto">
                <h4 class="mt-3">{{ t('vendite.offerte.section_motivazione') }}</h4>
                <Message severity="warn" :closable="false" size="small">
                  {{ detail.motivazione_rifiuto }}
                </Message>
              </template>

            </TabPanel>

            <!-- ====================== TAB REVISIONI ====================== -->
            <TabPanel value="revisioni">
              <p class="text-color-secondary mt-1">
                {{ t('vendite.offerte.revisioni_intro') }}
              </p>
              <div v-if="!revisioni.length" class="app-empty-state">
                <i class="pi pi-history" style="font-size: 2rem;" />
                <div>{{ t('vendite.offerte.revisioni_empty') }}</div>
              </div>
              <DataTable
                v-else
                :value="revisioni"
                striped-rows
                class="app-datatable app-datatable--inner"
                data-key="id"
              >
                <Column field="revisione_numero"
                  :header="t('vendite.offerte.col_revisione')"
                  style="width: 80px;" />
                <Column field="codice"
                  :header="t('vendite.offerte.col_codice')"
                  style="width: 140px;" />
                <Column field="data_emissione"
                  :header="t('vendite.offerte.col_emissione')"
                  style="width: 120px;">
                  <template #body="{ data }">{{ displayDate(data.data_emissione) }}</template>
                </Column>
                <Column field="stato_codice_interno"
                  :header="t('vendite.offerte.col_stato')"
                  style="width: 130px;">
                  <template #body="{ data }">
                    <Tag
                      :value="data.stato_descrizione"
                      :severity="statoOffertaSeverity(data.stato_codice_interno)"
                    />
                  </template>
                </Column>
              </DataTable>
            </TabPanel>
          </TabPanels>
        </Tabs>

        <!-- Footer: Salva visibile solo in CREATE o EDIT BOZZA. Negli stati
             post-BOZZA mostriamo Chiudi (close-only) — il footer Salva non ha
             senso (cambio stato passa dalla DrawerActionsBar). -->
        <FormFooter
          v-if="!isReadonly"
          :loading="loading"
          :disabled="!canSave"
          @save="handleSave"
          @cancel="onClose"
        />
        <FormFooter v-else-if="isEdit" close-only @cancel="onClose" />
      </template>
    </div>

    <!-- Sub-drawer eccezioni (master-detail inline). -->
    <OffertaEccezioniDrawer
      v-if="isEdit && detail"
      v-model:visible="eccezioniDrawerVisible"
      :offerta-id="props.offertaId"
      :offerta-codice="detail.codice"
      :offerta-stato-codice="stato"
      :offerta-stato-descrizione="detail.stato_descrizione"
      :offerta-cliente="detail.billing_account_display"
      :offerta-validita-dal="detail.validita_dal"
      :offerta-validita-al="detail.validita_al"
      :eccezioni-iniziali="detail.eccezioni || []"
      @changed="refreshDetail"
    />

    <!-- Sub-drawer note partizionate. Le eccezioni vengono passate per
         popolare il select RIGA nel form note (anchor RIGA). -->
    <OffertaNoteDrawer
      v-if="isEdit && detail"
      v-model:visible="noteDrawerVisible"
      :offerta-id="props.offertaId"
      :eccezioni="detail.eccezioni || []"
    />

    <!-- Dialogs di processo (state machine FE). -->
    <OffertaEmissioneDialog
      v-model:visible="emissioneDialogVisible"
      :offerta="detail"
      :loading="loading"
      @confirm="handleEmissioneConferma"
    />
    <OffertaEsitoDialog
      v-model:visible="esitoDialogVisible"
      :offerta="detail"
      :modalita="esitoDialogModalita"
      :loading="loading"
      @confirm="handleEsitoConferma"
    />
    <OffertaPushDialog
      v-model:visible="pushDialogVisible"
      :offerta="detail"
      :loading="loading"
      @confirm="handlePushConferma"
    />

    <!-- Dialog di successione — overlap su contratto esistente
         (E_CONTRATTO_OVERLAP_ESISTENTE). Conferma esplicita per chiudere il
         vecchio (valido_al = nuova decorrenza - 1) e generare il nuovo. -->
    <OffertaSuccessioneDialog
      v-model:visible="successioneDialogVisible"
      :contratto="contrattoSovrapposto"
      :nuova-validita-dal="detail?.validita_dal"
      :loading="loading"
      @confirm="handleSuccessioneConferma"
      @ispeziona-contratto="onIspezionaContrattoSovrapposto"
    />

    <!-- Ispezione read-only del contratto sovrapposto: riuso integrale del
         ContrattoDrawer (testata + righe + utility) in sola lettura forzata.
         Niente navigazione: alla chiusura ri-apre il dialog di successione. -->
    <ContrattoDrawer
      v-if="contrattoIspezioneId"
      :visible="contrattoIspezioneVisible"
      mode="edit"
      :contratto-id="contrattoIspezioneId"
      :readonly="true"
      @update:visible="onChiudiIspezioneContratto"
    />

    <!-- Dialog "contratto gia' generato" — idempotenza Pattern A.
         Si apre proattivamente se `detail.contratto_id` e' valorizzato
         (LEFT JOIN BE) oppure reattivamente se il BE solleva
         E_OFFERTA_CONTRATTO_GIA_GENERATO. Offre link diretto al
         ContrattoDrawer esistente, niente push doppio. -->
    <AppDialog
      v-model:visible="giaGeneratoDialogVisible"
      :header="t('vendite.offerte.gia_generato_titolo')"
      width="md"
    >
      <Message severity="info" :closable="false" size="small">
        {{ t('vendite.offerte.gia_generato_messaggio') }}
      </Message>
      <div v-if="detail?.contratto_numero" class="app-preview-box">
        <strong>{{ t('vendite.offerte.gia_generato_contratto_label') }}:</strong>
        {{ detail.contratto_numero }}
      </div>
      <!-- Footer custom: navigazione (apri contratto esistente), non Annulla/Salva. -->
      <template #footer>
        <Button
          :label="t('common.close')"
          text
          severity="secondary"
          @click="giaGeneratoDialogVisible = false"
        />
        <Button
          :label="t('vendite.offerte.gia_generato_apri_contratto')"
          icon="pi pi-arrow-right"
          severity="primary"
          :disabled="!detail?.contratto_id"
          @click="onApriContrattoEsistente"
        />
      </template>
    </AppDialog>
  </Drawer>
</template>
