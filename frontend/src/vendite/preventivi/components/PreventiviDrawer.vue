<script setup>
// Scopo: Drawer crea/modifica preventivo vendita.
// CREATE: form testata semplice per creazione rapida.
// EDIT: testata + righe + totali + integrazione (con azioni stato).
import { ref, watch, computed, nextTick, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreventiviStore } from '../stores/preventivi'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useInjectReadonly, READONLY_KEY } from '../../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { statoPreventiveSeverity } from '../../../core/utils/severity'
import { STATO_PREVENTIVO } from '../../constants'
import { addDaysToToday, displayDate, toDateString } from '../../../core/utils/date'
import { formatCurrency } from '../../../core/utils/format'
import { paramBool, paramInt } from '../../../core/utils/parameterCast'
import { useParameterDefaults } from '../../../core/composables/useParameterDefaults'
import { useUtilityDefaultId } from '../../../core/composables/useUtilityDefaultId'
import { useEmittenteFiscaleField } from '../../../core/composables/useEmittenteFiscaleField'
import { useTabEvents } from '../../../core/composables/useTabEvents'
import { getPreventivoFormDefaults } from '../../api/formDefaults'
import { createPreventivo, getContestoPricing } from '../api/preventiviApi'
import { getBillingAccountLookupById, getIstanzaUtilityLookupById } from '../../../core/apiCore'
import { DRAWER_WIDTH, MANAGE_ICONS, TAB_ENTITIES } from '../../../core/constants'
import { NAV_ICONS } from '../../../core/navigation'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../../core/components/DrawerFooter.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../../core/components/DrawerActionsBar.vue'
import { mapAvailableActionsToDrawerActions } from '../../../core/composables/useDrawerActions'
import { useDrawerContentReady } from '../../../core/composables/useDrawerContentReady'
import PreventiviForm from './PreventiviForm.vue'
import PreventiviRigheTable from './PreventiviRigheTable.vue'
import PreventiviIntegrazione from './PreventiviIntegrazione.vue'
import RiepilogoIvaTable from '../../../core/components/RiepilogoIvaTable.vue'
import PreventivoPdfButton from './PreventivoPdfButton.vue'
import DocumentiGeneratiSorgenteList from '../../../documenti/components/DocumentiGeneratiSorgenteList.vue'
import PreventivoNoteDrawer from '../../components/PreventivoNoteDrawer.vue'
import Drawer from 'primevue/drawer'
import Dialog from 'primevue/dialog'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import Message from 'primevue/message'

const { t } = useI18n()
const store = usePreventiviStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const { emitDataChanged } = useTabEvents()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  preventivoId: { type: [Number, null], default: null },
  // Readonly cumulativo: si somma all'inject del provider area (frontend-standards
  // §"Modalita' sola lettura", regola "drawer admin DEVE esporre prop readonly").
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

// Readonly effettivo = prop esplicita OR readonly area iniettato dal parent
// OR revisione superseded: esiste un'altra revisione "viva" con rev maggiore
// per lo stesso numero. In quel caso questo documento va trattato come
// storico immutabile (non si possono avere due revisioni "vive" sullo stesso
// numero che possano essere accettate o annullate in parallelo).
//
// Predicato: `!detail.is_attiva` (post-refactor 2026-05-15, predicato derivato
// da `vendite.vw_preventivi.is_attiva`). Ignora le rev abortite (ANNULLATO):
//   - rev 0 EMESSO + rev 1 DRAFT     → rev 0 is_attiva=F → superseded
//   - rev 0 EMESSO + rev 1 ANNULLATO → rev 0 is_attiva=T → NON superseded
// La seconda casistica chiude il flusso "ho sbagliato a revisionare, annullo
// e torno a operare sul predecessore". Diverso dal flag `has_next_revision`
// (esposto comunque dal BE per usi diagnostici), che resta TRUE anche se la
// rev superiore e' abortita.
const parentReadonly = useInjectReadonly()
const isSuperseded = computed(
  () => detail.value !== null && detail.value.is_attiva === false,
)
// isReadonly cumulativo: include permessi area parent + props.readonly +
// is_attiva=false (revisione superseded) + stato post-DRAFT del preventivo.
// Lo stato post-DRAFT entra qui perche' la regola di dominio "modifiche
// libere solo in BOZZA" si applica a tutti i sub-drawer (note, righe). Le
// azioni di stato (Accetta/Rifiuta/Annulla dal BE `availableActions`)
// restano cliccabili in readonly grazie alla classe `app-escape` applicata
// automaticamente da `DrawerActionsBar` ai suoi pulsanti — coerente con
// frontend-standards.md "Transizione a stato terminale".
//
// Allineato al pattern ContrattoDrawer: stesso modello "drawer parent calcola
// readonly + provide(READONLY_KEY) ai figli, sub-drawer usano solo
// useInjectReadonly() senza logica locale".
const isReadonly = computed(
  () => props.readonly
    || parentReadonly.value
    || isSuperseded.value
    || (props.mode === 'edit'
        && detail.value
        && detail.value.stato_codice_interno !== 'DRAFT'),
)
provide(READONLY_KEY, isReadonly)

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)
// Riepilogo IVA aggregato per aliquota (lettura da `vw_preventivi_riepilogo_iva_dettaglio`).
// Auto-popolato a ogni loadDetail e ogni `@changed` delle righe (regola fiscale
// DPR 633/72 art. 21: il calcolo IVA aggregato e' la single source of truth
// per i totali del documento).
const riepilogoIva = ref([])
// Pannello riepilogo IVA visibile sempre (almeno 1 riga). Il footer della
// RiepilogoIvaTable mostra gia' totale imponibile + imposta + totale doc,
// quindi i 3 totali compatti sotto diventano ridondanti e sono rimossi.
const showRiepilogoIva = computed(
  () => Array.isArray(riepilogoIva.value) && riepilogoIva.value.length > 0,
)

// Sub-drawer note partizionate. Cablato sull'id effettivo del preventivo;
// gestisce sia note di testata sia di riga (BE supporta entrambi via
// target_riga_id). Le righe non sono esposte qui come state (vivono in
// PreventiviRigheTable): per ora la nota-di-riga si crea conoscendo l'id;
// quando arrivera' il drawer note dalla singola riga il dropdown sara' popolato.
const noteDrawerVisible = ref(false)
// Auto-save bozza: in CREATE, appena utility + istanza sono valorizzati, il
// drawer crea il preventivo in BOZZA e si comporta da "edit-evolved" (mostra
// righe + integrazione, salvataggi successivi diventano UPDATE). createdId
// tiene l'id del preventivo creato in modalita' CREATE, null se ancora non
// salvato. Pattern: master-detail inline (memoria feedback_master_detail_inline).
const createdId = ref(null)
// Stato form riga inline: quando l'operatore sta editando/aggiungendo
// una riga, il DrawerFooter (Salva/Annulla testata) si nasconde per
// evitare duplicazione con i bottoni del PreventiviRigaForm.
// Aggiornato via `@form-aperto` (kebab) da PreventiviRigheTable.
const formRigaAperto = ref(false)
// Id effettivo per le sub-API (righe, integrazione, cambio stato): props.preventivoId
// in EDIT classico, createdId dopo auto-save in CREATE.
const effectivePreventivoId = computed(() => createdId.value ?? props.preventivoId)
// hasDetail = drawer popolato col detail BE (vale sia per EDIT classico sia
// per CREATE post auto-save). Sostituisce il check `isEdit && detail` per la
// visibilita' di righe / integrazione / azioni stato.
const hasDetail = computed(() => detail.value !== null)

// Deferimento contenuto: i LookupSelect/AutoComplete montano dopo l'animazione
// di apertura del drawer per evitare il rimbalzo iniziale (pattern
// feedback_content_ready_after_show centralizzato in useDrawerContentReady).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

// Capability dal detail backend (Fase 1: script.fn_available_actions_preventivo).
// Il drawer NON ricalcola lo stato: tutto deriva dai metadata API.
// Composable centralizzato (Fase 4.F2): availableActions/canEdit/flag/isLocked/
// nonEditableFields uniformi a Contratti/Promo. Qui editFlag = can_edit_testata.
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })
const availableActions = caps.availableActions
const canEditTestata = caps.canEdit
// In CREATE non c'e' detail BE: il drawer e' editabile per default (gated solo
// da isReadonly). In EDIT vale la capability BE. Pattern allineato a
// ContrattoDrawer (`isEdit && isLocked('field')`).
const canEditTestataEffective = computed(() => !isEdit.value || canEditTestata.value)
const canEditRighe = computed(() => caps.flag('can_edit_righe'))
// Nuova revisione: capability calcolata dal BE in
// `script.fn_available_actions_preventivo`. Regola di dominio applicata lato
// DB: solo preventivi in stato EMESSO ammettono revisione (ACCETTATO chiude
// la negoziazione, modifiche post-accettazione passano da nuovo preventivo).
const canCreateRevisione = computed(() => caps.flag('can_create_revisione'))
const canPushCommessa = computed(() => caps.flag('can_push_commessa'))
const pushCommessaReasonKey = computed(() => detail.value?.can_push_commessa_reason_key || null)
// Per PreventiviForm passiamo l'array originale (no Set): il prop e' typed Array.
// Quando il drawer ha gia' un detail (CREATE post auto-save bozza o EDIT classico)
// blocchiamo lato UX il cambio di billing_account_id e istanza_utility_id: il
// preventivo a quel punto e' agganciato al BA/istanza scelti e si sta gestendo
// il dettaglio righe; un cambio sarebbe un nuovo preventivo, non una modifica
// della testata. utility_id era gia' immutabile via metadata BE.
const nonEditableFields = computed(() => {
  const base = detail.value?.non_editable_fields || []
  if (!hasDetail.value) return base
  return [...base, 'billing_account_id', 'istanza_utility_id']
})

// Defaults non-BA da config.parameters (Fase 2 refactor frontend vendite).
// Caricati on-open drawer prima di resetForm; cache modulo `useParameterDefaults`.
// I defaults BA-dipendenti (valuta_id, termine_pagamento_id) NON stanno qui:
// arriveranno dall'endpoint dedicato form-defaults?billing_account_id=... (2.B4).
const { defaults: paramDefaults, load: loadParamDefaults } = useParameterDefaults([
  'VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG',
  'VENDITE_PREVENTIVO_DEFAULT_FATTURAZIONE_IMMEDIATA',
])

// Default utility globale: il parametro DEFAULT_UTILITY stocca un codice_interno
// (framework FK-surrogata, DB 2026-05-02). Composable risolve a id locale.
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

// Default emittente fiscale: per operatore con EF assegnato ritorna l'id;
// per admin globale (multi-EF) ritorna null e l'utente sceglie via
// EmittenteFiscaleField in modalita' Select. Necessario in CREATE per
// permettere all'admin globale di valorizzare il campo (BE crea_preventivo
// si aspetta emittente_fiscale_id se la GUC non lo deriva).
const { defaultEmittenteId } = useEmittenteFiscaleField()

function defaultForm() {
  const p = paramDefaults.value
  // validita_dal default = oggi (data emissione presunta del preventivo).
  // validita_al = validita_dal + N gg dal parameter; il watch su validita_dal
  // mantiene l'invariante anche quando l'operatore sposta la data di partenza.
  const validitaGg = paramInt(p.VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG, 30)
  return {
    utility_id: utilityDefaultId.value,
    // Operatore: pre-popolato dal profilo (read-only nel field).
    // Admin globale: null → il field rendera' una Select per scegliere.
    emittente_fiscale_id: defaultEmittenteId.value ?? null,
    billing_account_id: null,
    // _obj per BillingAccountLookup AutoComplete (pattern restore lookup ricco,
    // memoria feedback_autocomplete_restore). Popolato da onBaSelected (FE)
    // o da loadDetail() via getBillingAccountLookupById in edit.
    billing_account_obj: null,
    istanza_utility_id: null,
    // _obj per IstanzaUtilityLookup AutoComplete (pattern restore lookup ricco).
    // Popolato da onIstanzaSelected (FE) o da loadDetail() via
    // getIstanzaUtilityLookupById in edit (solo se BA assente: con BA presente
    // l'istanza e' derivata e il picker e' nascosto).
    istanza_utility_obj: null,
    valuta_id: null,
    termine_pagamento_id: null,
    validita_dal: addDaysToToday(0),
    validita_al: addDaysToToday(validitaGg),
    competenza_mese: null,
    fatturazione_immediata: paramBool(p.VENDITE_PREVENTIVO_DEFAULT_FATTURAZIONE_IMMEDIATA, false),
  }
}

// Sospende il ricalcolo automatico di validita_al durante l'inizializzazione
// del form (loadDetail in EDIT): senza questa guard il watch sotto sovrascrive
// validita_al persistita col valore = validita_dal + N gg.
const _suspendDateRecalc = ref(false)

// Auto-ricalcolo validita_al = validita_dal + VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG
// quando l'operatore modifica validita_dal. Vale sia in CREATE sia in EDIT
// (chi sposta la data di partenza si aspetta che la finestra di validita'
// scorra di conseguenza). validita_al resta comunque editabile manualmente:
// il watch non ha contropartita su validita_al, quindi l'override utente
// dura finche' non viene ritoccato validita_dal.
watch(() => form.value.validita_dal, (nuovaDal) => {
  if (_suspendDateRecalc.value) return
  if (!nuovaDal) return
  const validitaGg = paramInt(paramDefaults.value.VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG, 30)
  const dal = nuovaDal instanceof Date ? nuovaDal : new Date(nuovaDal)
  if (isNaN(dal.getTime())) return
  const al = new Date(dal)
  al.setHours(0, 0, 0, 0)
  al.setDate(al.getDate() + validitaGg)
  form.value.validita_al = al
})

// Contesto pricing del preventivo (audit visivo in header drawer):
// contratto attivo applicabile o listino categoria fallback. Caricato in
// parallelo al detail; assente in CREATE (nessun preventivo ancora salvato).
const contestoPricing = ref(null)

function resetForm() {
  form.value = defaultForm()
  detail.value = null
  createdId.value = null
  contestoPricing.value = null
}

async function loadDetail(id = null) {
  const targetId = id ?? effectivePreventivoId.value
  if (!targetId) return
  const data = await store.fetchDetail(targetId)
  if (!data) return
  detail.value = data
  // Carica in parallelo il contesto pricing per l'header del drawer (audit
  // visivo: contratto attivo o listino categoria fallback). Best-effort:
  // un fail non blocca il drawer ma logga in console per debug.
  getContestoPricing(targetId)
    .then((res) => { contestoPricing.value = res?.data?.data || null })
    .catch((err) => {
      contestoPricing.value = null
      console.warn('contesto pricing fetch failed', err?.response?.data || err)
    })
  // Sospende il watch di ricalcolo finche' non scarica entrambi i campi data:
  // assegnando form.value il watch fires su validita_dal e sovrascriverebbe
  // validita_al persistita.
  _suspendDateRecalc.value = true
  form.value = {
    utility_id: data.utility_id,
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    billing_account_id: data.billing_account_id,
    billing_account_obj: null,  // popolato sotto via getBillingAccountLookupById
    istanza_utility_id: data.istanza_utility_id,
    istanza_utility_obj: null,  // popolato sotto via getIstanzaUtilityLookupById (no BA)
    valuta_id: data.valuta_id,
    termine_pagamento_id: data.termine_pagamento_id,
    validita_dal: data.validita_dal ? new Date(data.validita_dal + 'T00:00:00') : null,
    validita_al: data.validita_al ? new Date(data.validita_al + 'T00:00:00') : null,
    competenza_mese: data.competenza_mese ? new Date(data.competenza_mese + 'T00:00:00') : null,
    fatturazione_immediata: data.fatturazione_immediata || false,
  }
  await nextTick()
  _suspendDateRecalc.value = false
  // Restore BillingAccountLookup _obj per visualizzazione ricca (codice, ragione
  // sociale, id fiscale, PDP). Best-effort: in caso di failure il drawer mostra
  // l'autocomplete vuoto e l'operatore puo' ri-selezionare. Skip se BA assente.
  if (data.billing_account_id) {
    try {
      const res = await getBillingAccountLookupById(data.billing_account_id)
      const ba = res?.data?.data
      if (ba) form.value.billing_account_obj = ba
    } catch {
      // Resto: form parte senza _obj, l'utente puo' rieseguire la ricerca.
    }
  } else if (data.istanza_utility_id) {
    // Restore IstanzaUtilityLookup _obj solo per preventivi prospect senza BA:
    // il picker istanza e' visibile solo in quel caso. Best-effort.
    try {
      const res = await getIstanzaUtilityLookupById(data.istanza_utility_id)
      const iu = res?.data?.data
      if (iu) form.value.istanza_utility_obj = iu
    } catch {
      // Resto: il picker mostra solo l'id risolto al prossimo focus.
    }
  }
  // Riepilogo IVA aggregato: il trigger DB lo mantiene in sync con le righe
  // su ogni mutazione, qui leggiamo lo stato corrente. Best-effort: in caso
  // di failure il pannello resta vuoto, i totali aggregati nella testata
  // restano comunque visibili.
  await loadRiepilogoIva(targetId)
}

// Scopo: ricarica solo il riepilogo IVA. Chiamato dopo ogni `@changed` delle
// righe (in coppia con loadDetail per i totali aggregati di testata).
async function loadRiepilogoIva(targetId = null) {
  const id = targetId ?? effectivePreventivoId.value
  if (!id) return
  try {
    riepilogoIva.value = await store.loadRiepilogoIva(id)
  } catch {
    riepilogoIva.value = []
  }
}

watch(() => props.visible, async (v) => {
  if (!v) return  // contentReady reset gestito da useDrawerContentReady
  // loadParamDefaults serve in entrambi i mode (paramBool/paramInt usati anche
  // in defaultForm). loadUtilityDefault serve solo in CREATE (in EDIT utility_id
  // arriva dal detail BE).
  if (isEdit.value) {
    await loadParamDefaults()
    loadDetail()
  } else {
    await Promise.all([loadParamDefaults(), loadUtilityDefault()])
    resetForm()
    // CREATE: pre-popoliamo la valuta dal BB resolve_valuta_default lato BE
    // (catena BA -> EF-del-BA -> EF-utente). Senza BA il BE applica il
    // livello 3 (EF dell'utente loggato, fallback gestore globale per admin
    // globale). Best-effort: se l'API fallisce il form resta vuoto.
    try {
      const res = await getPreventivoFormDefaults(null)
      const data = res?.data?.data
      if (data && form.value.valuta_id == null && data.valuta_id != null) {
        form.value.valuta_id = data.valuta_id
      }
    } catch {
      // Non blocchiamo l'apertura del drawer se l'API e' giu'.
    }
  }
})

// Auto-save bozza in CREATE quando utility + istanza sono entrambi valorizzati.
// Pattern master-detail inline: il drawer crea automaticamente la BOZZA cosi'
// l'operatore puo' iniziare subito a inserire righe senza click intermedi.
// Le successive modifiche alla testata diventano UPDATE (vedi handleSave).
//
// Skipped:
// - in EDIT classico (gia' c'e' il preventivo)
// - se createdId gia' valorizzato (auto-save gia' avvenuto)
// - se contentReady=false (drawer ancora in animazione apertura)
// - se loading=true (race con un'altra operazione)
async function autoSaveBozza() {
  const f = form.value
  const payload = {
    utility_id: f.utility_id,
    // Opzionale per BE: se omesso (operatore) il trigger DB lo deriva da
    // app.current_user_id. Per admin globale serve esplicito (no GUC EF).
    emittente_fiscale_id: f.emittente_fiscale_id || null,
    billing_account_id: f.billing_account_id || null,
    istanza_utility_id: f.istanza_utility_id || null,
    valuta_id: f.valuta_id || null,
    termine_pagamento_id: f.termine_pagamento_id || null,
    validita_dal: f.validita_dal ? toDateString(f.validita_dal) : null,
    validita_al: f.validita_al ? toDateString(f.validita_al) : null,
    competenza_mese: f.competenza_mese ? toDateString(f.competenza_mese) : null,
    fatturazione_immediata: f.fatturazione_immediata,
  }
  // useApiHandler.execute esegue l'unwrap dell'envelope axios { data, meta }.
  // Va chiamato con la fn axios diretta (NON con store.create che ritorna gia'
  // il valore unwrappato → execute riapplicherebbe .data e ritornerebbe undefined,
  // memoria progetto `feedback_useapihandler_solo_axios`).
  const result = await execute(
    () => createPreventivo(payload),
    { successMessage: t('preventivi.bozza_creata') }
  )
  if (result && result.id) {
    createdId.value = result.id
    // Notifica le altre tab del progetto del nuovo preventivo (allineato a
    // store.create che lo fa via emitDataChanged: chiamando createPreventivo
    // direttamente l'avremmo perso).
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, result.id)
    await loadDetail(result.id)
    // NON emettiamo 'saved': la transizione CREATE → "edit-evolved" e' un
    // dettaglio interno del drawer (createdId + hasDetail). Il padre non
    // deve passare a mode='edit' ne' chiudere/riaprire. Il prossimo emit
    // 'saved' parte da handleSave su click manuale dell'utente.
  }
}

watch(
  () => [form.value.utility_id, form.value.istanza_utility_id],
  async ([utility, istanza]) => {
    if (isEdit.value) return
    if (createdId.value !== null) return
    if (utility == null || istanza == null) return
    if (!contentReady.value) return
    if (loading.value) return
    await autoSaveBozza()
  },
)

// Fase 2.B4 + 2.F6: quando l'operatore valorizza/cambia il BA in create,
// chiediamo al BE i defaults BA-derived (valuta_id, termine_pagamento_id,
// iva_id) dal cliente associato. Per termine/iva sovrascriviamo solo se
// vuoti (proteggiamo scelte utente). Per la valuta SEMPRE sovrascriviamo
// con il valore BA-resolved: la valuta del BA (o del suo EF) prevale sulla
// valuta dell'EF utente caricata al mount (regola di coerenza dominio:
// "valuta del BA wins se specificata"). Skippiamo in edit (campi gia'
// persistiti dal payload preventivo).
let _baDefaultsToken = 0
watch(() => form.value.billing_account_id, async (newBaId, oldBaId) => {
  if (isEdit.value) return
  if (!newBaId || newBaId === oldBaId) return
  const tk = ++_baDefaultsToken
  let res
  try {
    res = await getPreventivoFormDefaults(newBaId)
  } catch {
    return  // Best-effort: il fallback resta "form vuoto, l'operatore valorizza".
  }
  if (tk !== _baDefaultsToken) return  // Apertura/chiusura veloce: scarta stantio.
  const data = res?.data?.data
  if (!data) return
  // Valuta: il BA (o il suo EF) vince sempre sull'EF utente caricato al mount.
  if (data.valuta_id != null) {
    form.value.valuta_id = data.valuta_id
  }
  if (form.value.termine_pagamento_id == null && data.termine_pagamento_id != null) {
    form.value.termine_pagamento_id = data.termine_pagamento_id
  }
})

// In CREATE servono utility e istanza (regola di dominio post brief DB rev2:
// preventivo deve essere collegato a un'istanza utility, derivabile dal BA o
// selezionata standalone per prospect). In EDIT l'istanza e' gia' persistita
// e il backend non richiede di rispedirla.
// Defense-in-depth: anche se il DrawerFooter e' nascosto da
// `v-if="canEditTestataEffective && !isReadonly"`, includiamo isReadonly qui
// cosi' qualsiasi consumer futuro del computed (shortcut tastiera, save
// programmato) e' coperto dalla stessa guard.
const canSave = computed(() => {
  if (isReadonly.value) return false
  const f = form.value
  if (f.utility_id == null) return false
  if (!isEdit.value && f.istanza_utility_id == null) return false
  return true
})

async function handleSave() {
  const f = form.value
  // Branch update: EDIT classico oppure CREATE post auto-save (createdId valorizzato).
  // In entrambi i casi il preventivo esiste gia' lato DB e si invia un UPDATE.
  // utility_id NON viene spedito: e' immutabile post-create (regola di dominio,
  // script.fn_available_actions_preventivo lo mette sempre in non_editable_fields).
  // Inviamo sempre tutti i campi della whitelist: il backend e' tollerante a NULL
  // (empty_to_none), cosi' un clear di valuta/termine viene davvero persistito.
  if (isEdit.value || createdId.value !== null) {
    const payload = {
      billing_account_id: f.billing_account_id ?? null,
      istanza_utility_id: f.istanza_utility_id ?? null,
      valuta_id: f.valuta_id ?? null,
      termine_pagamento_id: f.termine_pagamento_id ?? null,
      validita_dal: f.validita_dal ? toDateString(f.validita_dal) : null,
      validita_al: f.validita_al ? toDateString(f.validita_al) : null,
      competenza_mese: f.competenza_mese ? toDateString(f.competenza_mese) : null,
      fatturazione_immediata: f.fatturazione_immediata,
    }
    const result = await execute(
      () => store.update(effectivePreventivoId.value, payload),
      { successMessage: t('preventivi.preventivo_salvato') }
    )
    if (result !== null) {
      await loadDetail()
      emit('saved', result)
    }
  } else {
    // Fallback: CREATE manuale senza auto-save preventivo (caso edge se l'auto-save
    // non e' scattato — es. utente ha disabilitato istanza). Stesso payload di
    // autoSaveBozza ma senza transizione a "edit-evolved": il drawer si chiude
    // dopo create.
    const payload = {
      utility_id: f.utility_id,
      // Stessa regola di autoSaveBozza: opzionale per operatore (trigger DB),
      // necessario per admin globale che sceglie l'EF dal field.
      emittente_fiscale_id: f.emittente_fiscale_id || null,
      billing_account_id: f.billing_account_id || null,
      istanza_utility_id: f.istanza_utility_id || null,
      valuta_id: f.valuta_id || null,
      termine_pagamento_id: f.termine_pagamento_id || null,
      validita_dal: f.validita_dal ? toDateString(f.validita_dal) : null,
      validita_al: f.validita_al ? toDateString(f.validita_al) : null,
      competenza_mese: f.competenza_mese ? toDateString(f.competenza_mese) : null,
      fatturazione_immediata: f.fatturazione_immediata,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('preventivi.preventivo_creato') }
    )
    if (result !== null) emit('saved', result)
  }
}

// hasOrphanedDraft = bozza creata in CREATE via auto-save ma rimasta vuota.
// Quando il drawer viene chiuso senza aver inserito righe, chiediamo conferma
// e cancelliamo la bozza con DELETE preventivo (guard BE: solo BOZZA + 0 righe
// + 0 pratiche). Per bozze gia' con righe il drawer si chiude direttamente: il
// preventivo resta in lista e l'operatore puo' riprenderlo o cambiare stato a
// ANNULLATO esplicitamente.
const hasOrphanedDraft = computed(() => {
  if (createdId.value === null) return false
  const count = detail.value?.righe_count ?? 0
  return count === 0
})

function close() {
  attemptClose()
}

// Intercetta tutti i tipi di chiusura (Annulla, ESC, click outside, X header):
// se la bozza e' orfana mostra conferma; in caso di ok cancella la bozza, in
// caso di reject lascia il drawer aperto (NON emette update:visible(false) al
// parent → visible resta true → drawer riaperto da PrimeVue).
function attemptClose() {
  if (!hasOrphanedDraft.value) {
    emit('update:visible', false)
    emit('cancelled')
    return
  }
  confirmAction({
    title: t('preventivi.abbandono_bozza_titolo'),
    message: t('preventivi.conferma_abbandono_bozza'),
    acceptLabel: t('preventivi.abbandono_bozza_conferma'),
    danger: true,
    onAccept: async () => {
      const id = createdId.value
      const result = await execute(
        () => store.elimina(id),
        { successMessage: t('preventivi.bozza_eliminata') }
      )
      if (result !== null) {
        emit('update:visible', false)
        emit('cancelled')
      }
    },
  })
}

// Wrapper per l'evento update:visible del Drawer PrimeVue. In apertura passa
// al parent senza domande; in chiusura delega a attemptClose (che decide se
// chiedere conferma o chiudere direttamente).
function onVisibleChange(v) {
  if (v) {
    emit('update:visible', true)
    return
  }
  attemptClose()
}

// --- Azioni stato (data-driven da detail.available_actions) ---

// Scopo: handler unico bottone azione. Usa requires_confirm dai metadata
//        per decidere se mostrare il dialog di conferma. La label nel
//        messaggio di conferma e' tradotta dalla label_key dell'azione.
// Dialog accettazione preventivo: aperto quando l'azione di stato porta a
// ACCETTATO (transizione EMESSO → ACCETTATO). Sostituisce il confirmAction
// generico per questa transizione, perche' richiede dati di processo
// (fatturazione_immediata + competenza_mese, vedi BE preventivi_service.cambia_stato).
const acceptDialogVisible = ref(false)
const acceptForm = ref({
  fatturazione_immediata: false,
  // Default 1° del mese corrente: scelta sensata se l'operatore conferma "non
  // immediata" senza modificare. Comunque editabile.
  competenza_mese: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
})
// Regola di priorita': immediata=true ⇒ competenza forzata al mese corrente.
// Il BE applica comunque la stessa regola lato server (defense-in-depth);
// qui pre-blocchiamo il datepicker per chiarezza UX.
const acceptCompetenzaDisabled = computed(
  () => acceptForm.value.fatturazione_immediata === true,
)

// Helper: primo giorno del mese corrente (snapshot tx-time, allineato BE).
function _firstOfCurrentMonth() {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), 1)
}

// Sync UX↔BE: quando l'utente attiva "fatturazione immediata", il datepicker
// si disabilita e mostriamo il mese corrente (= valore che il BE forzera').
// Evita drift tra valore visibile e valore effettivamente persistito.
watch(() => acceptForm.value.fatturazione_immediata, (immediata) => {
  if (immediata) {
    acceptForm.value.competenza_mese = _firstOfCurrentMonth()
  }
})

function openAcceptDialog() {
  acceptForm.value = {
    fatturazione_immediata: false,
    competenza_mese: _firstOfCurrentMonth(),
  }
  acceptDialogVisible.value = true
}

async function confirmAcceptDialog() {
  const f = acceptForm.value
  acceptDialogVisible.value = false
  await eseguiCambioStato(STATO_PREVENTIVO.ACCETTATO, {
    fatturazione_immediata: f.fatturazione_immediata,
    competenza_mese: f.competenza_mese ? toDateString(f.competenza_mese) : null,
  })
}

function onCambiaStato(action) {
  // Transizione → ACCETTATO: richiede dialog dedicato per scegliere modalita'
  // di fatturazione. Tutte le altre transizioni usano la conferma generica.
  if (action.target_state === STATO_PREVENTIVO.ACCETTATO) {
    openAcceptDialog()
    return
  }
  if (action.requires_confirm) {
    confirmAction({
      message: t('preventivi.conferma_cambio_stato', { stato: t(action.label_key) }),
      onAccept: () => eseguiCambioStato(action.target_state),
    })
  } else {
    eseguiCambioStato(action.target_state)
  }
}

async function eseguiCambioStato(nuovoStato, extras = {}) {
  const result = await execute(
    () => store.cambiaStato(effectivePreventivoId.value, nuovoStato, extras),
    { successMessage: t('preventivi.stato_cambiato') }
  )
  if (result !== null) {
    await loadDetail()
    emit('saved', result)
  }
}

// Scopo: Crea nuova revisione del preventivo.
function onNuovaRevisione() {
  confirmAction({
    message: t('preventivi.conferma_revisione'),
    onAccept: async () => {
      const result = await execute(
        () => store.nuovaRevisione(effectivePreventivoId.value),
        { successMessage: t('preventivi.revisione_creata') }
      )
      if (result !== null) emit('saved', result)
    }
  })
}

// Azioni della testata preventivo consumate da DrawerActionsBar.
// Non filtrate da `isReadonly`: le actions di stato (BE data-driven) restano
// renderizzate anche in stati post-DRAFT o in LETTURA — `DrawerActionsBar`
// applica automaticamente `.app-escape` per renderle cliccabili sotto
// `.app-readonly`. La sicurezza e' garantita dal BE che rifiuta i comandi
// senza permesso (defense-in-depth, frontend-standards "Transizione a stato
// terminale" + "Tasti di uscita"). Allineato a ContrattoDrawer.
const drawerActions = computed(() => {
  if (!hasDetail.value) return []
  const list = mapAvailableActionsToDrawerActions({
    availableActions,
    t,
    onAction: onCambiaStato,
  })
  if (canCreateRevisione.value) {
    list.push({
      key: 'nuova-revisione',
      kind: 'state',
      label: t('preventivi.azione_revisione'),
      icon: 'pi pi-copy',
      severity: 'secondary',
      command: onNuovaRevisione,
    })
  }
  list.push({
    key: 'manage-note',
    kind: 'manage',
    label: t('preventivi.gestisci_note'),
    icon: MANAGE_ICONS.NOTE,
    command: () => { noteDrawerVisible.value = true },
  })
  return list
})

</script>

<template>
  <Drawer :visible="visible" @update:visible="onVisibleChange"
    @after-show="onAfterShow"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE }" :dismissable="true">
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('preventivi.preventivo')"
        :icon="NAV_ICONS.PREVENTIVI"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- Header info: visibile in EDIT classico e in CREATE post auto-save (hasDetail).
           Cliente denominazione rimossa: gia' visibile nel form testata sotto.
           Contesto pricing (contratto/listino) mostrato come badge per audit visivo
           del path resolver applicato al preventivo.
           Refactor UI drawer 2026-05-21: header e azioni passano dai BB
           condivisi DrawerEntityHeader + DrawerActionsBar (vedi
           docs/it/dev/frontend/frontend-standards.md §"Azioni Drawer"). -->
      <template v-if="hasDetail">
        <DrawerEntityHeader>
          <Tag :value="`${detail.numero} rev.${detail.rev}`" severity="secondary" />
          <Tag v-if="isSuperseded" :value="t('preventivi.tag_superseded')" severity="warn" icon="pi pi-history" />
          <span v-if="detail.data" class="app-drawer-header-muted">
            {{ displayDate(detail.data) }}
          </span>
          <template v-if="contestoPricing && contestoPricing.fonte === 'CONTRATTO'">
            <Tag
              :value="t('preventivi.contesto_pricing_contratto', {
                contratto: contestoPricing.contratto_numero,
                listino: contestoPricing.listino_codice,
              })"
              severity="info"
              icon="pi pi-file-edit"
              v-tooltip.bottom="t('preventivi.contesto_pricing_contratto_tooltip')"
            />
          </template>
          <template v-else-if="contestoPricing && contestoPricing.fonte === 'CATEGORIA'">
            <Tag
              :value="t('preventivi.contesto_pricing_categoria', {
                listino: contestoPricing.listino_codice,
                categoria: contestoPricing.categoria_cliente_codice,
              })"
              severity="info"
              icon="pi pi-tag"
              v-tooltip.bottom="t('preventivi.contesto_pricing_categoria_tooltip')"
            />
          </template>
          <template v-else-if="contestoPricing && contestoPricing.fonte === 'NONE'">
            <Tag
              :value="t('preventivi.contesto_pricing_none')"
              severity="warn"
              icon="pi pi-exclamation-triangle"
              v-tooltip.bottom="t('preventivi.contesto_pricing_none_tooltip')"
            />
          </template>

          <template #status>
            <Tag
              :value="detail.stato_descrizione"
              :severity="statoPreventiveSeverity(detail.stato_codice_interno)"
            />
          </template>
        </DrawerEntityHeader>

        <!-- Azioni testata: stato, PDF e note in posizione unica sopra il form.
             PDF stato-aware (Tranche M+):
               - DRAFT     -> Anteprima inline (no save)
               - EMESSO    -> Genera PDF (con dialog conferma rigenerazione)
               - ACCETTATO/EVASO/RIFIUTATO/SCADUTO/ANNULLATO -> Scarica (apre lista)
             Resta componente dedicato dentro #suffix (stateful), non rappresentabile
             come azione `command: () => void`. -->
        <DrawerActionsBar :actions="drawerActions">
          <template #suffix>
            <PreventivoPdfButton
              v-if="detail.emittente_fiscale_id"
              :preventivo-id="effectivePreventivoId"
              :emittente-fiscale-id="detail.emittente_fiscale_id"
              :stato-codice="detail.stato_codice_interno"
            />
          </template>
        </DrawerActionsBar>
      </template>

      <!-- Banner revisione superseded: visibile sotto le azioni quando il
           preventivo aperto e' una versione storica (esiste una revisione
           successiva). Il drawer e' interamente readonly: niente azioni stato,
           niente nuova revisione, niente edit testata/righe. -->
      <Message v-if="isSuperseded" severity="warn" :closable="false" class="mt-1">
        {{ t('preventivi.banner_revisione_superseded') }}
      </Message>

      <!-- Sprint E (autorizzazioni prezzi L3): preventivo "congelato" se ha
           righe PENDING (in attesa esito) o REJECTED (da correggere). I 2
           messaggi sono distinti per dare azioni diverse all'operatore:
           - PENDING → "attendi esito"
           - REJECTED → "correggi la riga o eliminala". -->
      <Message v-if="hasDetail && detail.frozen_for_pending_pricing"
        severity="warn" :closable="false" class="mt-1">
        {{ t('preventivi.banner_frozen_pending_pricing', { count: detail.pending_pricing_count }) }}
      </Message>
      <Message v-if="hasDetail && detail.frozen_for_rejected_pricing"
        severity="error" :closable="false" class="mt-1">
        {{ t('preventivi.banner_frozen_rejected_pricing', { count: detail.rejected_pricing_count }) }}
      </Message>
      <!-- Area banner informativi non bloccanti: tenere qui i messaggi di
           contesto del preventivo, evitando banner sparsi in fondo al drawer. -->
      <Message v-if="hasDetail && detail.ba_ha_contratto_attivo === false"
        severity="info" :closable="false" class="mt-1">
        {{ t('preventivi.banner_no_contratto_attivo') }}
      </Message>
      <Message v-if="hasDetail && !canPushCommessa && pushCommessaReasonKey"
        severity="info" :closable="false" class="mt-1">
        {{ t(pushCommessaReasonKey) }}
      </Message>

      <Divider v-if="hasDetail" />

      <!-- Form testata: monta dopo l'animazione drawer per evitare rimbalzo lookup -->
      <PreventiviForm v-if="contentReady"
        :form="form" :is-modificabile="canEditTestataEffective && !isReadonly"
        :non-editable-fields="nonEditableFields"
        :is-edit="isEdit || createdId !== null"
        :record="detail" />

      <!-- Righe: visibili appena c'e' detail (EDIT classico o CREATE post auto-save). -->
      <template v-if="contentReady && hasDetail">
        <Divider />
        <PreventiviRigheTable
          :preventivo-id="effectivePreventivoId"
          :billing-account-id="form.billing_account_id"
          :is-modificabile="canEditRighe && !isReadonly"
          @changed="loadDetail()"
          @form-aperto="(v) => { formRigaAperto = v }" />

        <!-- Riepilogo IVA aggregato (regola fiscale DPR 633/72 art. 21).
             Sempre visibile quando c'e' almeno una riga (mono o multi
             aliquota). Il footer della tabella mostra gia' totale
             imponibile + imposta + totale documento. Componente riusabile
             cross-dominio (stesso pattern arrivera' su fatture). -->
        <template v-if="showRiepilogoIva">
          <Divider />
          <RiepilogoIvaTable :items="riepilogoIva" :show-subtitle="true" />
        </template>
      </template>

      <!-- Integrazione: visibile quando il backend conferma can_push_commessa.
           Se non ammessa ma con reason i18n-ready, il Message hint e'
           mostrato nell'area banner in alto. -->
      <template v-if="contentReady && hasDetail">
        <template v-if="canPushCommessa">
          <Divider />
          <PreventiviIntegrazione :preventivo-id="effectivePreventivoId"
            @push-completato="loadDetail()" />
        </template>
      </template>

      <!-- Documenti generati per il preventivo (Tranche M motore documentale).
           Building block riusabile da qualsiasi sorgente.
           Visibilita': nascosta in DRAFT (= bozza) — l'anteprima PDF e'
           inline e non persistita, quindi la lista sarebbe sempre vuota e
           il messaggio "lista vuota" e' rumore visivo. Mostrata da EMESSO
           in poi (stato in cui esiste almeno una versione PDF persistita,
           regola di dominio "EMESSO == almeno una versione PDF" gia'
           applicata atomica BE).
           NB: il codice_interno e' `DRAFT` (vedi seed
           config/stati_doc_preventivi.csv); 'Bozza' e' solo la descrizione
           localizzata. -->
      <template v-if="contentReady && hasDetail && detail.uid && detail.stato_codice_interno !== STATO_PREVENTIVO.DRAFT">
        <Divider />
        <DocumentiGeneratiSorgenteList
          sorgente-code="PREVENTIVO"
          :sorgente-id="effectivePreventivoId"
        />
      </template>

      <DrawerFooter v-if="canEditTestataEffective && !isReadonly && !formRigaAperto" :loading="loading" :disabled="!canSave"
        @save="handleSave" @cancel="close" />
      <!-- Fallback close-only: in stati post-DRAFT (readonly, no Salva/Annulla)
           l'utente deve poter uscire deliberatamente dal footer in basso, non
           solo dalla X in alto (semantica diversa: X=dismiss/escape,
           Chiudi=completion). Pattern coerente con `feedback_drawer_footer_close_only`
           e ContrattoRigheDrawer. Nascosto quando il form riga e' aperto per
           non duplicare l'azione Annulla del form. -->
      <DrawerFooter v-else-if="hasDetail && !formRigaAperto" close-only @cancel="close" />
    </div>
  </Drawer>

  <!-- Sub-drawer note: cablato sull'id effettivo del preventivo, montato
       solo quando il drawer principale e' aperto E c'e' un preventivo reale. -->
  <PreventivoNoteDrawer
    v-if="effectivePreventivoId"
    v-model:visible="noteDrawerVisible"
    :preventivo-id="effectivePreventivoId"
  />

  <!-- Dialog accettazione preventivo (transizione EMESSO → ACCETTATO).
       Richiede modalita' di fatturazione: toggle immediata + datepicker mese
       di competenza. Regola di priorita' (BE+FE): immediata=true forza
       competenza al mese corrente. -->
  <Dialog v-model:visible="acceptDialogVisible" modal :closable="false"
    :header="t('preventivi.accetta_titolo')" :style="{ width: '420px' }">
    <p style="margin: 0 0 1rem 0; color: var(--text-color-secondary);">
      {{ t('preventivi.accetta_descrizione') }}
    </p>
    <div class="form-grid">
      <div class="form-field" style="display: flex; align-items: center; gap: 0.75rem;">
        <ToggleSwitch v-model="acceptForm.fatturazione_immediata" inputId="accept-immediata" />
        <label for="accept-immediata">{{ t('preventivi.accetta_fatturazione_immediata') }}</label>
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.accetta_competenza') }}</label>
        <DatePicker v-model="acceptForm.competenza_mese" :date-format="DATE_FORMAT"
          show-icon view="month" :disabled="acceptCompetenzaDisabled" />
        <small v-if="acceptCompetenzaDisabled" style="color: var(--text-color-secondary);">
          {{ t('preventivi.accetta_competenza_hint_immediata') }}
        </small>
        <small v-else-if="!acceptForm.competenza_mese" class="app-field-error">
          {{ t('preventivi.accetta_competenza_required') }}
        </small>
      </div>
    </div>
    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" text
        @click="acceptDialogVisible = false" />
      <Button :label="t('preventivi.accetta_conferma')" severity="primary"
        :disabled="!acceptForm.fatturazione_immediata && !acceptForm.competenza_mese"
        @click="confirmAcceptDialog" />
    </template>
  </Dialog>
</template>

