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
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../../core/composables/useDrawerDetailLoad'
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { useFetchVersion } from '../../../core/composables/useFetchVersion'
import { useRevisioniTab } from '../../../core/composables/useRevisioniTab'
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
import { useBaFormDefaults } from '../../_shared/baDefaults/useBaFormDefaults'
import { createPreventivo, getContestoPricing } from '../api/preventiviApi'
import { useDrawerAutosaveBozza } from '../../../core/composables/useDrawerAutosaveBozza'
import { getBillingAccountLookupById, getIstanzaUtilityLookupById } from '../../../core/apiCore'
import { DRAWER_WIDTH, MANAGE_ICONS, TAB_ENTITIES } from '../../../core/constants'
import { NAV_ICONS } from '../../../core/navigation'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import FormFooter from '../../../core/components/FormFooter.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../../core/components/DrawerActionsBar.vue'
import { mapAvailableActionsToDrawerActions } from '../../../core/composables/useDrawerActions'
import { useDrawerContentReady } from '../../../core/composables/useDrawerContentReady'
import { useDrawerFormPreserve } from '../../../core/composables/useDrawerFormPreserve'
import PreventiviForm from './PreventiviForm.vue'
import PreventiviRigheTable from './PreventiviRigheTable.vue'
import PreventiviSmistamentoDialog from './dialogs/PreventiviSmistamentoDialog.vue'
import RiepilogoIvaTable from '../../../core/components/RiepilogoIvaTable.vue'
import DocumentoIndirizziSection from '../../_shared/indirizzi/DocumentoIndirizziSection.vue'
import DocumentoCollegamentiBar from '../../_shared/lineage/DocumentoCollegamentiBar.vue'
import EntityPdfButton from '../../../documenti/components/EntityPdfButton.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'
import PreventivoNoteDrawer from '../../components/PreventivoNoteDrawer.vue'
import PreventivoEmissioneDialog from './dialogs/PreventivoEmissioneDialog.vue'
import PreventivoAccettazioneDialog from './dialogs/PreventivoAccettazioneDialog.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'
import Message from 'primevue/message'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const { t, te } = useI18n()
const store = usePreventiviStore()
const { execute, loading, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()
const { emitDataChanged } = useTabEvents()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  preventivoId: { type: [Number, null], default: null },
  // Readonly cumulativo: si somma all'inject del provider area (frontend-standards
  // §"Modalita' sola lettura", regola "drawer admin DEVE esporre prop readonly").
  readonly: { type: Boolean, default: false },
  // Pratica collegata (percorso pratica-first PREVENTIVI): quando valorizzata,
  // l'accettazione NON avviene dal drawer (azione → ACCETTATO nascosta) ma dal
  // flusso APPROVAZIONE_CLIENTE (endpoint M2), che applica la politica di
  // fatturazione dalla configurazione, non i campi scelti qui.
  praticaId: { type: [Number, null], default: null },
  // Contesto cliente ereditato dalla pratica (percorso pratica-first): quando
  // valorizzato, in CREATE il drawer pre-compila istanza (+ BA se cliente
  // attivo) e li BLOCCA da subito (non possono divergere dalla pratica). Shape:
  // { billingAccountId: number|null, istanzaUtilityId: number|null }.
  praticaContext: { type: [Object, null], default: null },
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])
const onClose = useDrawerClose(emit, 'cancelled')
// Detail fuori scope (RLS) / inesistente → toast + chiusura, niente drawer vuoto.
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

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
// Readonly PURO: permesso LETTURA / readonly forzato / revisione superseded —
// SENZA il lock-di-stato post-DRAFT. Distinzione necessaria per le azioni di
// processo (PreventiviSmistamentoDialog): in ACCETTATO il drawer e'
// `app-readonly` per il lock-di-stato, ma lo smistamento e' legittimo e la
// dialog deve restare operativa (`readonly` esplicito su AppDialog, che
// altrimenti erediterebbe il lock e nasconderebbe il pulsante); in readonly
// puro invece la scrittura e' vietata: la dialog riceve `consuntivo=true`
// (niente selezione/azioni).
// Stessa semantica del gate `drawerActions` (props.readonly || parentReadonly).
const isReadonlyPuro = computed(
  () => props.readonly || parentReadonly.value || isSuperseded.value,
)

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
// Preserva le modifiche non salvate quando `loadDetail` sostituisce il form:
// senza, compilare la testata e poi salvare una RIGA (`@changed` → loadDetail)
// la riportava com'era sul server, in silenzio. BB condiviso coi drawer
// gemelli (difetto trovato sul DDT, 2026-08-17, identico qui).
const { preserva: preservaForm, reset: resetFormPreserve } = useDrawerFormPreserve(form)
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
// una riga, il FormFooter (Salva/Annulla testata) si nasconde per
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
// `can_create_revisione`: il flag BE resta esposto per backward-compat, ma il
// FE non lo legge piu' — l'azione `crea_revisione` arriva ora data-driven in
// `available_actions` (post brief DB 2026-05-28, mirror offerte).
const canPushCommessa = computed(() => caps.flag('can_push_commessa'))
const pushCommessaReasonKey = computed(() => detail.value?.can_push_commessa_reason_key || null)
// Ramo gemello dello smistamento: `genera_ordine` ha la sua reason, che finora
// nessuno mostrava (il banner sotto copriva solo il ramo commessa).
const canGeneraOrdine = computed(() => caps.flag('can_genera_ordine'))
const generaOrdineReasonKey = computed(() => detail.value?.can_genera_ordine_reason_key || null)
// Pannello Smistamento visibile da ACCETTATO in poi (EVASO = consuntivo):
// prima dell'accettazione non c'e' nulla da smistare e il pannello sarebbe
// solo rumore (tutte RESIDUA, azioni rifiutate dal BE).
const showSmistamento = computed(() => {
  const stato = detail.value?.stato_codice_interno
  return stato === STATO_PREVENTIVO.ACCETTATO || stato === STATO_PREVENTIVO.EVASO
})
// Per PreventiviForm passiamo l'array originale (no Set): il prop e' typed Array.
// Quando il drawer ha gia' un detail (CREATE post auto-save bozza o EDIT classico)
// blocchiamo lato UX il cambio di billing_account_id e istanza_utility_id: il
// preventivo a quel punto e' agganciato al BA/istanza scelti e si sta gestendo
// il dettaglio righe; un cambio sarebbe un nuovo preventivo, non una modifica
// della testata. utility_id era gia' immutabile via metadata BE.
const nonEditableFields = computed(() => {
  const base = detail.value?.non_editable_fields || []
  // Post auto-save bozza / EDIT: cambiare BA o istanza sarebbe un altro
  // preventivo, non una modifica → entrambi bloccati. utility_id è già
  // immutabile via metadata BE.
  if (hasDetail.value) return [...base, 'billing_account_id', 'istanza_utility_id']
  // Aperto da pratica: blocca SOLO i campi effettivamente ereditati (passati,
  // non-null) dal contesto — "se passati da esterno → valorizzati e non
  // modificabili". Un campo assente (es. prospect senza BA) resta editabile:
  // niente lock a vuoto che impedirebbe il salvataggio.
  const ctx = props.praticaContext
  if (ctx) {
    const locked = [...base]
    if (ctx.istanzaUtilityId != null) locked.push('istanza_utility_id')
    if (ctx.billingAccountId != null) locked.push('billing_account_id')
    return locked
  }
  return base
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

// Tab "Testata | Revisioni" — state + load con guard di race incapsulati nel
// building block `useRevisioniTab` (regola del 2, estratto da
// PreventiviDrawer + OffertaDrawer). `activeTab`, `revisioni`,
// `loadRevisioni`, `reset` arrivano da li'.
const revisioniTab = useRevisioniTab({
  load: (id) => store.loadRevisioni(id),
})
const { activeTab, revisioni } = revisioniTab

// Guard di race anti-stale per `getContestoPricing` (fetch fire-and-forget
// in `loadDetail`). Stesso pattern di `revisioniTab`: una risposta arrivata
// dopo cambio entita' o chiusura drawer viene scartata.
const contestoFv = useFetchVersion()

function resetForm() {
  form.value = defaultForm()
  resetFormPreserve()
  detail.value = null
  createdId.value = null
  contestoPricing.value = null
}

async function loadDetail(id = null) {
  const targetId = id ?? effectivePreventivoId.value
  if (!targetId) return
  const applicaModifiche = preservaForm()
  // Fuori scope (RLS) / inesistente → loadDetailOrClose avvisa, chiude e
  // ritorna null; `if (!data) return` sotto salta il populate.
  const data = await loadDetailOrClose(() => store.fetchDetail(targetId))
  if (!data) return
  detail.value = data
  // Carica in parallelo il contesto pricing per l'header del drawer (audit
  // visivo: contratto attivo o listino categoria fallback). Best-effort:
  // un fail non blocca il drawer ma logga in console per debug.
  // Guard di versione via `contestoFv`: cambio entita' / chiusura drawer
  // invalida la call in volo, evita di mostrare il contesto del preventivo
  // precedente in quello nuovo.
  const cTag = contestoFv.tag()
  getContestoPricing(targetId)
    .then((res) => {
      if (!contestoFv.isCurrent(cTag)) return
      contestoPricing.value = res?.data?.data || null
    })
    .catch((err) => {
      if (!contestoFv.isCurrent(cTag)) return
      contestoPricing.value = null
      console.warn('contesto pricing fetch failed', err?.response?.data || err)
    })
  // Carica la catena revisioni (tab Revisioni). Guard di versione interno a
  // `revisioniTab` (useFetchVersion). Mirror OffertaDrawer.
  revisioniTab.loadRevisioni(targetId)
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
  // Fissa la baseline e ripristina il non-salvato che la sostituzione
  // avrebbe cancellato (BB useDrawerFormPreserve).
  applicaModifiche()
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

// Scopo: in CREATE da pratica, pre-compila cliente/istanza dal contesto pratica
// e ne ripristina gli _obj per i lookup (stesso restore di loadDetail). I campi
// sono già bloccati da nonEditableFields (props.praticaContext). istanza sempre
// presente dalla pratica; BA presente solo se cliente attivo (prospect → solo
// istanza, picker istanza visibile ma disabilitato).
async function prefillFromPratica() {
  const ctx = props.praticaContext
  if (!ctx) return
  if (ctx.istanzaUtilityId) form.value.istanza_utility_id = ctx.istanzaUtilityId
  if (ctx.billingAccountId) {
    // Cliente attivo: BA-first, istanza derivata dal BA (picker istanza nascosto).
    form.value.billing_account_id = ctx.billingAccountId
    try {
      const res = await getBillingAccountLookupById(ctx.billingAccountId)
      const ba = res?.data?.data
      if (ba) form.value.billing_account_obj = ba
    } catch { /* best-effort: il campo resta col solo id, comunque bloccato */ }
  } else if (ctx.istanzaUtilityId) {
    // Prospect: nessun BA, istanza diretta (picker istanza visibile, disabilitato).
    try {
      const res = await getIstanzaUtilityLookupById(ctx.istanzaUtilityId)
      const iu = res?.data?.data
      if (iu) form.value.istanza_utility_obj = iu
    } catch { /* best-effort */ }
  }
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
  if (!v) {
    // contentReady reset gestito da useDrawerContentReady. Invalida le load
    // in volo (revisioni + contesto pricing): una risposta stantia che
    // arrivasse dopo la chiusura non deve popolare lo stato del prossimo
    // preventivo aperto.
    revisioniTab.reset()
    contestoFv.invalidate()
    return
  }
  // Reset tab attivo sempre, EDIT o CREATE: senza questo, riaprendo il drawer
  // su un altro preventivo il tab restava quello dell'apertura precedente
  // (es. chiudo su "Revisioni", riapro su un nuovo preventivo → si vedeva
  // "Revisioni" invece di "Testata"). Mirror OffertaDrawer.
  revisioniTab.reset()
  contestoFv.invalidate()
  // Reset stato "edit-evolved" a OGNI apertura: questo drawer e' montato una
  // sola volta come attivita' dinamica nella dashboard pratiche e riusato tra
  // aperture diverse (l'istanza persiste). Senza azzerare createdId/detail, un
  // createdId rimasto da una sessione CREATE precedente (bozza auto-salvata)
  // farebbe puntare `effectivePreventivoId` al preventivo sbagliato riaprendo
  // un'altra pratica in EDIT. In CREATE resetForm() li riazzera comunque.
  createdId.value = null
  detail.value = null
  // loadParamDefaults serve in entrambi i mode (paramBool/paramInt usati anche
  // in defaultForm). loadUtilityDefault serve solo in CREATE (in EDIT utility_id
  // arriva dal detail BE).
  if (isEdit.value) {
    await loadParamDefaults()
    loadDetail()
  } else {
    await Promise.all([loadParamDefaults(), loadUtilityDefault()])
    resetForm()
    // Contesto pratica (percorso pratica-first): eredita+blocca cliente/istanza.
    await prefillFromPratica()
    // CREATE: default dal BE (catena BA -> EF-del-BA -> EF-utente; senza BA
    // il BE applica il livello 3). Stessa funzione che usa il watcher sul
    // cambio BA: quando il BA arriva già precompilato dalla pratica non c'è
    // nessun cambio da osservare, e prima di questo giro il termine di
    // pagamento — che è nella stessa risposta — restava a terra.
    await applicaDefaultsBa(form.value.billing_account_id ?? null)
  }
})

// Auto-save bozza + abbandono bozza orfana via BB condiviso (B13, regola del 2).
// Trigger: utility + istanza entrambi valorizzati in CREATE → crea la BOZZA così
// l'operatore inserisce subito le righe. `close`/`onVisibleChange` usati dal
// template; createdId resta ref del drawer. (I default BA-derived sono gestiti
// separatamente da useBaFormDefaults qui sotto.)
const { close, onVisibleChange } = useDrawerAutosaveBozza({
  emit,
  execute,
  loading,
  createdId,
  isEdit: () => isEdit.value,
  contentReady: () => contentReady.value,
  triggerSources: () => [form.value.utility_id, form.value.istanza_utility_id],
  isReady: ([utility, istanza]) => utility != null && istanza != null,
  createDraftApi: createPreventivo,
  buildDraftPayload: () => {
    const f = form.value
    return {
      utility_id: f.utility_id,
      // Opzionale per BE: trigger DB da app.current_user_id; admin globale esplicito.
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
  },
  tabEntity: TAB_ENTITIES.PREVENTIVO,
  fetchDetail: (id) => loadDetail(id),
  // Il BB preserva i campi compilati MENTRE la POST di creazione viaggia:
  // senza il form li perderebbe, perche' `loadDetail` sostituisce il form
  // coi dati del server (fix 2026-08-17).
  form,
  deleteDraft: (id) => store.elimina(id),
  righeCountGetter: () => detail.value?.righe_count ?? 0,
  messages: {
    bozzaCreata: t('vendite.preventivi.bozza_creata'),
    abbandonoTitolo: t('vendite.preventivi.abbandono_bozza_titolo'),
    abbandonoMessage: t('vendite.preventivi.conferma_abbandono_bozza'),
    abbandonoConferma: t('vendite.preventivi.abbandono_bozza_conferma'),
    bozzaEliminata: t('vendite.preventivi.bozza_eliminata'),
  },
})

// Fase 2.B4 + 2.F6: quando l'operatore valorizza/cambia il BA in create,
// chiediamo al BE i defaults BA-derived (valuta_id, termine_pagamento_id,
// iva_id) dal cliente associato. Per termine/iva sovrascriviamo solo se
// vuoti (proteggiamo scelte utente). Per la valuta SEMPRE sovrascriviamo
// con il valore BA-resolved: la valuta del BA (o del suo EF) prevale sulla
// valuta dell'EF utente caricata al mount (regola di coerenza dominio:
// "valuta del BA wins se specificata"). Skippiamo in edit (campi gia'
// persistiti dal payload preventivo).
// Watcher BA→defaults condiviso (guard token + valuta BA-wins nel composable).
// Extra preventivo: termine pagamento (solo se l'operatore non l'ha scelto).
const { applicaDefaults: applicaDefaultsBa } = useBaFormDefaults({
  form,
  isEdit,
  fetchDefaults: getPreventivoFormDefaults,
  apply: (data, f) => {
    if (f.termine_pagamento_id == null && data.termine_pagamento_id != null) {
      f.termine_pagamento_id = data.termine_pagamento_id
    }
  },
})

// In CREATE servono utility e istanza (regola di dominio post brief DB rev2:
// preventivo deve essere collegato a un'istanza utility, derivabile dal BA o
// selezionata standalone per prospect). In EDIT l'istanza e' gia' persistita
// e il backend non richiede di rispedirla.
// Defense-in-depth: anche se il FormFooter e' nascosto da
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
      { successMessage: t('vendite.preventivi.preventivo_salvato') }
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
      { successMessage: t('vendite.preventivi.preventivo_creato') }
    )
    if (result !== null) emit('saved', result)
  }
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
// Dialog emissione preventivo: aperto quando l'azione di stato porta a EMESSO
// (transizione BOZZA → EMESSO). Sostituisce il confirmAction generico perche'
// l'emissione orchestra atomic state + genera documento + allegati lato BE
// (refactor 2026-05-28, mirror del flusso offerta `ApiOffertaEmetti`).
const emissioneDialogVisible = ref(false)
const emissioneLoading = ref(false)
// Dialog Smistamento: aperta dal pulsante in barra azioni (2026-07-25). Era un
// pannello in coda al contenuto del drawer — le azioni di processo stanno in
// alto, come per il «Genera reso» del DDT.
const smistamentoDialogVisible = ref(false)
// Ref alla barra collegamenti: lo smistamento crea archi verso ordine/commessa,
// quindi i chip vanno ricaricati insieme al detail (vedi `onSmistato`).
const collegamentiRef = ref(null)
// Dialog accettazione estratto in PreventivoAccettazioneDialog (componente
// condiviso col percorso pratica): qui resta solo apertura + conferma. Il
// payload {fatturazione_immediata, competenza_mese} arriva gia' BE-ready.
function openAcceptDialog() {
  acceptDialogVisible.value = true
}

async function confirmAcceptDialog(payload) {
  acceptDialogVisible.value = false
  await eseguiCambioStato(STATO_PREVENTIVO.ACCETTATO, payload)
}


// Scopo: il nome dello STATO di destinazione per la frase di conferma («Portare
//   il documento nello stato {stato}?»). La descrizione leggibile la sa solo il
//   database (`DRAFT` -> «Bozza», `ALLOCATO` -> «Allocato a magazzino»: non e'
//   derivabile dal codice), quindi arriva dalla capability come
//   `target_state_descrizione`. Finche' il DB non la espone si ripiega sulla
//   label dell'azione — comportamento invariato, nessun testo mancante.
function statoDestinazione(action) {
  return action.target_state_descrizione || t(action.label_key)
}

function onCambiaStato(action) {
  // Dispatch azioni speciali (target_state=null): post brief DB 2026-05-28 le
  // azioni `crea_revisione` e `push_commessa` arrivano da `available_actions`
  // come voci data-driven (mirror offerte). Routing su `action.key`.
  if (action.key === 'crea_revisione') {
    onNuovaRevisione()
    return
  }
  if (action.key === 'push_commessa' || action.key === 'genera_ordine') {
    // Entrambi i rami dello smistamento vivono nella dialog Smistamento
    // (PreventiviSmistamentoDialog: selezione righe, routing per natura,
    // progress EVASO), aperta dal suo pulsante dedicato. Le azioni restano
    // esposte dal BE per coerenza modello ma i bottoni drawer sono filtrati a
    // monte (vedi `availableActionsHeader` in `drawerActions`): difensivo.
    return
  }
  // Transizione → EMESSO: dialog dedicato con anteprima documento + allegati.
  // L'endpoint /emetti/ (multipart) orchestra atomic state + genera + allegati
  // (refactor 2026-05-28). NB: il BE rifiuta la transizione via /stato/ con
  // E_PREV_VALIDAZIONE — questa intercettazione e' la sola via supportata.
  if (action.target_state === STATO_PREVENTIVO.EMESSO) {
    emissioneDialogVisible.value = true
    return
  }
  // Transizione → ACCETTATO: richiede dialog dedicato per scegliere modalita'
  // di fatturazione. Tutte le altre transizioni usano la conferma generica.
  if (action.target_state === STATO_PREVENTIVO.ACCETTATO) {
    openAcceptDialog()
    return
  }
  if (action.requires_confirm) {
    confirmAction({
      message: t('vendite.preventivi.conferma_cambio_stato', { stato: statoDestinazione(action) }),
      onAccept: () => eseguiCambioStato(action.target_state),
    })
  } else {
    eseguiCambioStato(action.target_state)
  }
}

// Scopo: callback @confirm del PreventivoEmissioneDialog. Riceve i file
// staged dall'utente e chiama store.emetti (POST multipart /emetti/).
// Loading e abandon-warning sono gestiti dal building block generico.
async function handleEmissioneConferma({ files }) {
  emissioneLoading.value = true
  const result = await execute(
    () => store.emetti(effectivePreventivoId.value, { allegati: files || [] }),
    { successMessage: t('vendite.preventivi.stato_cambiato') },
  )
  emissioneLoading.value = false
  if (result !== null) {
    emissioneDialogVisible.value = false
    await loadDetail()
    emit('saved', result)
  }
}

async function eseguiCambioStato(nuovoStato, extras = {}) {
  const result = await execute(
    () => store.cambiaStato(effectivePreventivoId.value, nuovoStato, extras),
    { successMessage: t('vendite.preventivi.stato_cambiato') }
  )
  if (result !== null) {
    await loadDetail()
    emit('saved', result)
  }
}

// Scopo: Crea nuova revisione del preventivo.
function onNuovaRevisione() {
  confirmAction({
    message: t('vendite.preventivi.conferma_revisione'),
    onAccept: async () => {
      const result = await execute(
        () => store.nuovaRevisione(effectivePreventivoId.value),
        { successMessage: t('vendite.preventivi.revisione_creata') }
      )
      if (result !== null) emit('saved', result)
    }
  })
}

// Scopo: callback @smistato della PreventiviSmistamentoDialog — almeno un ramo
// dello smistamento e' andato a buon fine: ricarica il detail (la transizione
// automatica ACCETTATO → EVASO e le capability si vedono solo dopo il reload),
// i chip dei collegamenti (lo smistamento crea gli archi preventivo→ordine e
// preventivo→commessa: senza reload il chip comparirebbe solo alla riapertura
// del drawer) e, se il ramo merce ha creato un ordine, notifica il tab ordini.
async function onSmistato({ ordineId } = {}) {
  if (ordineId) emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
  await loadDetail()
  collegamentiRef.value?.reload()
}

// Azioni della testata preventivo consumate da DrawerActionsBar.
// Read-only PURO (permesso LETTURA / pannello split / readonly forzato): le
// azioni di stato (Accetta/Rifiuta/Annulla/revisione) — che abilitano un
// aggiornamento — vengono NASCOSTE (2026-06-01, allineamento ai drawer senza
// barra azioni tipo soggetti/BA). Gate su `props.readonly || parentReadonly`,
// NON su `isReadonly`: quest'ultimo include il lock-di-stato post-DRAFT, ma in
// stato post-DRAFT con operatore abilitato le transizioni devono restare
// visibili. Il BE resta come difesa (defense-in-depth).
const drawerActions = computed(() => {
  if (!hasDetail.value) return []
  // Azioni di stato data-driven dal BE (`script.fn_available_actions_preventivo`,
  // post brief DB 2026-05-28). `crea_revisione` arriva qui come voce normale
  // con target_state=null; il dispatch e' su `action.key` in `onCambiaStato`.
  // `push_commessa` e `genera_ordine` vengono filtrati: entrambi i rami dello
  // smistamento vivono nella dialog Smistamento (PreventiviSmistamentoDialog:
  // selezione righe, routing per natura, progress EVASO) — un bottone header
  // duplicherebbe il percorso. Le azioni restano esposte dal BE per coerenza
  // modello (capability + gate residuo per ramo).
  // Sul percorso pratica (praticaId valorizzato) l'accettazione e' guidata dal
  // flusso APPROVAZIONE_CLIENTE (M2): nascondi l'azione → ACCETTATO dal drawer
  // per non creare un secondo percorso con politica fatturazione divergente.
  const availableActionsHeader = (availableActions.value || [])
    .filter(a => a.key !== 'push_commessa' && a.key !== 'genera_ordine')
    .filter(a => !(props.praticaId && a.target_state === STATO_PREVENTIVO.ACCETTATO))
  const list = mapAvailableActionsToDrawerActions({
    availableActions: availableActionsHeader,
    t,
    te,
    onAction: onCambiaStato,
    readonly: props.readonly || parentReadonly.value,
  })
  // Smistamento: apre la dialog dedicata (righe residue instradate per natura
  // verso ordine/commessa). Da ACCETTATO in poi; resta visibile anche in
  // readonly puro — la dialog si apre consuntiva (footer di sola chiusura).
  if (showSmistamento.value) {
    list.push({
      key: 'smistamento',
      kind: 'manage',
      label: t('vendite.preventivi.section_smistamento'),
      icon: MANAGE_ICONS.SEND,
      command: () => { smistamentoDialogVisible.value = true },
    })
  }
  list.push({
    key: 'manage-note',
    kind: 'manage',
    label: t('vendite.preventivi.gestisci_note'),
    icon: MANAGE_ICONS.NOTE,
    command: () => { noteDrawerVisible.value = true },
  })
  return list
})

</script>

<template>
  <Drawer :visible="visible" @update:visible="onVisibleChange"
    @after-show="onAfterShow"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE_PLUS }" :dismissable="true">
    <template #header>
      <DrawerTitle
        :action="(isEdit || hasDetail) ? t('common.edit') : t('common.new')"
        :title="t('vendite.preventivi.preventivo')"
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
          <Tag v-if="isSuperseded" :value="t('vendite.preventivi.tag_superseded')" severity="warn" icon="pi pi-history" />
          <span v-if="detail.data" class="app-drawer-header-muted font-bold">
            {{ displayDate(detail.data) }}
          </span>
          <template v-if="contestoPricing && contestoPricing.fonte === 'CONTRATTO'">
            <Tag
              :value="t('vendite.preventivi.contesto_pricing_contratto', {
                contratto: contestoPricing.contratto_numero,
                listino: contestoPricing.listino_codice,
              })"
              severity="info"
              icon="pi pi-file-edit"
              v-tooltip.bottom="t('vendite.preventivi.contesto_pricing_contratto_tooltip')"
            />
          </template>
          <template v-else-if="contestoPricing && contestoPricing.fonte === 'CATEGORIA'">
            <Tag
              :value="t('vendite.preventivi.contesto_pricing_categoria', {
                listino: contestoPricing.listino_codice,
                categoria: contestoPricing.categoria_cliente_codice,
              })"
              severity="info"
              icon="pi pi-tag"
              v-tooltip.bottom="t('vendite.preventivi.contesto_pricing_categoria_tooltip')"
            />
          </template>
          <template v-else-if="contestoPricing && contestoPricing.fonte === 'NONE'">
            <Tag
              :value="t('vendite.preventivi.contesto_pricing_none')"
              severity="warn"
              icon="pi pi-exclamation-triangle"
              v-tooltip.bottom="t('vendite.preventivi.contesto_pricing_none_tooltip')"
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
        <DrawerActionsBar :actions="drawerActions" :info-key="detail?.stato_info_key || ''">
          <template #suffix>
            <EntityPdfButton
              :sorgente-code="SORGENTE_CODES.PREVENTIVO"
              :entity-id="effectivePreventivoId"
              :pdf="detail.pdf"
              i18n-prefix="vendite.preventivi.pdf"
              :dialog-title="detail.numero
                ? t('vendite.preventivi.pdf.dialog_title', { numero: detail.numero })
                : ''"
            />
          </template>
        </DrawerActionsBar>

        <!-- Collegamenti diretti (pratica + origine + destinazioni di livello 1):
             segnalazione a colpo d'occhio sotto i pulsanti — «Ordine»,
             «Contratto». Il grafo completo si apre dai chip stessi in dialog. -->
        <DocumentoCollegamentiBar
          ref="collegamentiRef"
          base-path="/vendite/preventivi"
          :doc-id="effectivePreventivoId"
          :readonly="isReadonlyPuro" />
      </template>

      <!-- Banner revisione superseded: visibile sotto le azioni quando il
           preventivo aperto e' una versione storica (esiste una revisione
           successiva). Il drawer e' interamente readonly: niente azioni stato,
           niente nuova revisione, niente edit testata/righe. -->
      <Message v-if="isSuperseded" severity="warn" :closable="false" class="mt-1">
        {{ t('vendite.preventivi.banner_revisione_superseded') }}
      </Message>

      <!-- Sprint E (autorizzazioni prezzi L3): preventivo "congelato" se ha
           righe PENDING (in attesa esito) o REJECTED (da correggere). I 2
           messaggi sono distinti per dare azioni diverse all'operatore:
           - PENDING → "attendi esito"
           - REJECTED → "correggi la riga o eliminala". -->
      <Message v-if="hasDetail && detail.frozen_for_pending_pricing"
        severity="warn" :closable="false" class="mt-1">
        {{ t('vendite.preventivi.banner_frozen_pending_pricing', { count: detail.pending_pricing_count }) }}
      </Message>
      <Message v-if="hasDetail && detail.frozen_for_rejected_pricing"
        severity="error" :closable="false" class="mt-1">
        {{ t('vendite.preventivi.banner_frozen_rejected_pricing', { count: detail.rejected_pricing_count }) }}
      </Message>
      <!-- Area banner informativi non bloccanti: tenere qui i messaggi di
           contesto del preventivo, evitando banner sparsi in fondo al drawer. -->
      <Message v-if="hasDetail && detail.ba_ha_contratto_attivo === false"
        severity="info" :closable="false" class="mt-1">
        {{ t('vendite.preventivi.banner_no_contratto_attivo') }}
      </Message>
      <Message v-if="hasDetail && !canPushCommessa && pushCommessaReasonKey && te(pushCommessaReasonKey)"
        severity="info" :closable="false" class="mt-1">
        {{ t(pushCommessaReasonKey) }}
      </Message>
      <!-- Ramo ordine dello smistamento: stessa forma del ramo commessa sopra. -->
      <Message v-if="hasDetail && !canGeneraOrdine && generaOrdineReasonKey && te(generaOrdineReasonKey)"
        severity="info" :closable="false" class="mt-1">
        {{ t(generaOrdineReasonKey) }}
      </Message>

      <Divider v-if="hasDetail" />

      <!-- Tabs Testata | Revisioni (mirror OffertaDrawer). Tab "Revisioni"
           disabilitato in CREATE (non c'e' un preventivo da revisionare).
           Default tab "Testata" resettato all'apertura del drawer. -->
      <Tabs v-model:value="activeTab">
        <TabList>
          <Tab value="testata">{{ t('vendite.preventivi.tab_testata') }}</Tab>
          <Tab value="revisioni" :disabled="!isEdit">
            {{ t('vendite.preventivi.tab_revisioni') }}
            <span v-if="isEdit && revisioni.length">({{ revisioni.length }})</span>
          </Tab>
        </TabList>

        <TabPanels>
          <!-- ====================== TAB TESTATA ====================== -->
          <TabPanel value="testata">
            <!-- Form testata: monta dopo l'animazione drawer per evitare rimbalzo lookup -->
            <PreventiviForm v-if="contentReady"
              :form="form" :is-modificabile="canEditTestataEffective && !isReadonly"
              :non-editable-fields="nonEditableFields"
              :is-edit="isEdit || createdId !== null"
              :record="detail" />

            <!-- Righe: visibili appena c'e' detail (EDIT classico o CREATE post auto-save). -->
            <template v-if="contentReady && hasDetail">
              <!-- Sezione indirizzi (UX v2, BB condiviso): solo il default,
                   contatore "+N altri", pulsante "Indirizzi" che apre il
                   drawer di gestione. -->
              <DocumentoIndirizziSection
                dominio="preventivi"
                :doc-id="effectivePreventivoId"
                :soggetto-ruolo-id="detail?.soggetto_ruolo_id ?? null"
                :istanza-utility-id="detail?.istanza_utility_id ?? null"
                :readonly="!(canEditTestataEffective && !isReadonly)" />

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

            <!-- L'area inline "Documenti generati" e' stata rimossa 2026-07-16
                 (doppione): l'archivio PDF si consulta dal pulsante PDF in
                 testata (EntityPdfButton -> PdfDocumentiSorgenteDialog, stesso
                 BB con in piu' expand automatico e append allegati). -->

          </TabPanel>

          <!-- ====================== TAB REVISIONI ====================== -->
          <TabPanel value="revisioni">
            <p class="text-color-secondary mt-1">
              {{ t('vendite.preventivi.revisioni_intro') }}
            </p>
            <div v-if="!revisioni.length" class="app-empty-state">
              <i class="pi pi-history" style="font-size: 2rem;" />
              <div>{{ t('vendite.preventivi.revisioni_empty') }}</div>
            </div>
            <DataTable
              v-else
              :value="revisioni"
              striped-rows
              class="app-datatable app-datatable--inner"
              data-key="id"
            >
              <Column field="rev"
                :header="t('vendite.preventivi.col_rev')"
                style="width: 70px;" />
              <Column field="data"
                :header="t('vendite.preventivi.col_data')"
                style="width: 130px;">
                <template #body="{ data }">{{ displayDate(data.data) }}</template>
              </Column>
              <Column field="stato_codice_interno"
                :header="t('vendite.preventivi.col_stato')"
                style="width: 140px;">
                <template #body="{ data }">
                  <Tag
                    :value="data.stato_descrizione"
                    :severity="statoPreventiveSeverity(data.stato_codice_interno)"
                  />
                </template>
              </Column>
              <Column field="totale_documento"
                :header="t('vendite.preventivi.col_totale')"
                style="width: 130px;">
                <template #body="{ data }">{{ formatCurrency(data.totale_documento) }}</template>
              </Column>
            </DataTable>
          </TabPanel>
        </TabPanels>
      </Tabs>

      <FormFooter v-if="canEditTestataEffective && !isReadonly && !formRigaAperto" :loading="loading" :disabled="!canSave"
        @save="handleSave" @cancel="close" />
      <!-- Fallback close-only: in stati post-DRAFT (readonly, no Salva/Annulla)
           l'utente deve poter uscire deliberatamente dal footer in basso, non
           solo dalla X in alto (semantica diversa: X=dismiss/escape,
           Chiudi=completion). Pattern coerente con `feedback_drawer_footer_close_only`
           e ContrattoRigheDrawer. Nascosto quando il form riga e' aperto per
           non duplicare l'azione Annulla del form. -->
      <FormFooter v-else-if="hasDetail && !formRigaAperto" close-only @cancel="close" />
    </div>
  </Drawer>

  <!-- Sub-drawer note: cablato sull'id effettivo del preventivo, montato
       solo quando il drawer principale e' aperto E c'e' un preventivo reale. -->
  <PreventivoNoteDrawer
    v-if="effectivePreventivoId"
    v-model:visible="noteDrawerVisible"
    :preventivo-id="effectivePreventivoId"
  />

  <!-- Dialog emissione preventivo (transizione BOZZA → EMESSO). Wrapper sul
       building block DocumentoEmissioneDialog: anteprima PDF + allegati,
       conferma orchestra atomic state + genera + allegati via /emetti/. -->
  <PreventivoEmissioneDialog
    v-if="effectivePreventivoId"
    v-model:visible="emissioneDialogVisible"
    :preventivo="detail"
    :loading="emissioneLoading"
    @confirm="handleEmissioneConferma"
  />

  <!-- Dialog accettazione preventivo (EMESSO → ACCETTATO): componente condiviso
       col percorso pratica. Emette il payload {fatturazione_immediata,
       competenza_mese} gia' BE-ready. -->
  <PreventivoAccettazioneDialog
    :campi-errati="campiErrati"
    v-model:visible="acceptDialogVisible"
    :readonly="props.readonly || parentReadonly"
    @confirm="confirmAcceptDialog"
  />

  <!-- Dialog Smistamento (righe residue → ordine / commessa per natura),
       aperta dal pulsante in barra azioni. Le capability per ramo
       (can_push_commessa / can_genera_ordine + reason) restano la difesa BE;
       il Message hint con la reason e' nell'area banner in alto. Sul percorso
       pratica (step SMISTAMENTO) e' INTERATTIVA come nello standalone
       (uniformita', Fase 2): l'operatore smista qui e il post_smistamento
       aggancia ordine e crea i flussi a valle. Solo in readonly PURO
       (LETTURA/forzato/superseded) e' `consuntivo`. -->
  <PreventiviSmistamentoDialog
    v-if="effectivePreventivoId && showSmistamento"
    v-model:visible="smistamentoDialogVisible"
    :preventivo-id="effectivePreventivoId"
    :consuntivo="isReadonlyPuro"
    @smistato="onSmistato"
  />
</template>

