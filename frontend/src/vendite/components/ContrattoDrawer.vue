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
import { useNotify } from '../../core/composables/useNotify'
import { useContatoreNote } from '../../core/composables/useContatoreNote'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useInjectReadonly, READONLY_KEY } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useForzaturaConfermata } from '../../core/composables/useForzaturaConfermata'
import { useEntityCapabilities } from '../../core/composables/useEntityCapabilities'
import { useTestataDocumento } from '../../core/composables/useTestataDocumento'
import { DRAWER_WIDTH, MANAGE_ICONS, TIPO_RUOLO, STATUS_ICONS, DATE_FORMAT } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { addDaysToToday, toDateString, parseIsoDate, displayDate, oggiAziendale, giornoDi } from '../../core/utils/date'
import { paramInt, paramString } from '../../core/utils/parameterCast'
import { statoContrattoSeverity } from '../../core/utils/severity'
import AppDrawer from '../../core/components/AppDrawer.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import DocumentoIndirizziSection from '../_shared/indirizzi/DocumentoIndirizziSection.vue'
import DocumentoCollegamentiBar from '../_shared/lineage/DocumentoCollegamentiBar.vue'
import { mapAvailableActionsToDrawerActions } from '../../core/composables/useDrawerActions'
import LookupSelect from '../../core/components/LookupSelect.vue'
import ListinoDocumentoSelect from './ListinoDocumentoSelect.vue'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import { ripristinaBillingAccount } from '../../core/utils/ripristinaLookup'
import { CLIENTE_BA } from '../_shared/cliente/clienteCambiato'
import { useCambioClienteDocumento } from '../_shared/cliente/useCambioClienteDocumento'
import EmittenteFiscaleField from '../../core/components/EmittenteFiscaleField.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import ContrattoNoteDrawer from './ContrattoNoteDrawer.vue'
import ContrattoEmissioneDialog from './dialogs/ContrattoEmissioneDialog.vue'
import DocumentoAnnulloLegamiDialog from '../_shared/annullo/DocumentoAnnulloLegamiDialog.vue'
import ContrattoRigheDrawer from './ContrattoRigheDrawer.vue'
import EntityPdfButton from '../../documenti/components/EntityPdfButton.vue'
import { SORGENTE_CODES } from '../../documenti/constants'
import { CAMPI_FORM_TESTATA_CONTRATTO, FORMA_CONTRATTO, STATO_CONTRATTO } from '../constants'
import TipoVariazioneSelect from './TipoVariazioneSelect.vue'
import AmbitoContrattoSelect from './AmbitoContrattoSelect.vue'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { useUtilityDefaultId } from '../../core/composables/useUtilityDefaultId'
import { useEmittenteFiscaleField } from '../../core/composables/useEmittenteFiscaleField'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { useFooterDocumento } from '../../core/composables/useFooterDocumento'
import { getContrattoFormDefaults } from '../api/formDefaults'
import { useBaFormDefaults } from '../_shared/baDefaults/useBaFormDefaults'
import {
  applicaFornituraDaDefaults, schedaDaForm, schedaDaFornitura, schedaVuota,
} from '../_shared/fornitura/schedaFornitura'
import AppDialog from '../../core/components/AppDialog.vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import ToggleSwitch from 'primevue/toggleswitch'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

const { t, te } = useI18n()
const store = useContrattiStore()
const { execute, loading, campiErrati } = useApiHandler()
const notify = useNotify()
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
// Modifiche non salvate: fotografia a form popolato (apertura, ricarica,
// salvataggio), chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { preserva, fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

// Capability dal detail backend (Fase 1.B2: script.fn_available_actions_contratto).
// Il drawer NON ricalcola lo stato: tutto deriva dai metadata API.
// Composable centralizzato (Fase 4.F2): isLocked(field) = !canEdit OR Set lookup.
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })

const capabilities = caps.capabilities
const availableActions = caps.availableActions
const isLocked = caps.isLocked
const righeCount = computed(() => detail.value?.righe_count ?? detail.value?.righe?.length ?? 0)

// isContractLocked = stato post-DRAFT. La regola di dominio e' "modifiche
// libere via form solo in DRAFT". In ATTIVO quali colonne si cambiano lo dice
// il lock di testata del DB (`valido_al` passa dal dialog «Cessa contratto»),
// non il form drawer. CESSATO/ANNULLATO interamente immutabili.
// Prima usava `!canEditTestata` (true in ATTIVO/ANNULLATO perche' la fn DB
// considera ATTIVO parzialmente editabile) -> sub-drawer righe restava
// erroneamente editabile in stati terminali. Allineato al footer
// Salva/Chiudi.
const isContractLocked = computed(
  () => isEdit.value && detail.value?.stato_codice_interno !== STATO_CONTRATTO.DRAFT,
)

// isReadonly effettivo del drawer: OR tra permessi area e stato post-DRAFT.
// Tutti i campi/azioni del drawer principale e dei sub-drawer (righe, utility)
// si basano su questo computed. Propagato via provide ai figli, che usano
// solo `useInjectReadonly()` senza logica locale (standard del progetto).
const isReadonly = computed(
  () => props.readonly || parentReadonly.value || isContractLocked.value,
)
provide(READONLY_KEY, isReadonly)

// La scheda di fornitura si cambia finche' il DB lo dice (`can_edit_utility`,
// il lock dei satelliti); in creazione e' aperta.
const schedaBloccata = computed(
  () => isReadonly.value || (isEdit.value && !caps.flag('can_edit_utility')),
)

// I tre riferimenti dell'atto (CIG/CUP/commessa, I8/D9) sono l'ECCEZIONE al
// lock post-DRAFT, per decisione Q1 di Tid (2026-08-29): non toccano prezzo,
// validita' o perimetro, e non producono nessun effetto finche' la fattura non
// ne fa lo snapshot (I4). Negli appalti PA il CIG arriva quando arriva, e puo'
// arrivare a contratto gia' ATTIVO.
// ⚠️ NON si allarga `isReadonly`: quello e' propagato via provide a TUTTI i
//    figli e sbloccherebbe righe, utility e pricing. L'eccezione resta una
//    condizione a se', letta solo dai tre campi, dal footer e da `canSave`.
// ⛔ In CESSATO/ANNULLATO restano bloccati: li' la regola e' immutabilita'
//    piena. E i permessi d'area vincono su tutto.
// ⭐ In CREATE compaiono dal 2026-08-31 (slice S3-b): la whitelist interna di
//    `vendite.fn_create_contratto` li ammette dal changeSet `20260831-24`.
//    Prima erano spenti perche' quella whitelist non RESPINGE una chiave che
//    non conosce — la SCARTA, e il CIG sarebbe sparito con un 200 a video.
// ⭐ Dal 2026-10-10 non e' piu' uno specchio di stati: in quali stati i tre
//    campi si cambiano lo dice il montaggio del lock di testata del DB
//    (brief-db-testata-dopo-emissione, D-8/D-10: aperti in DRAFT e ATTIVO,
//    fermi a contratto chiuso), e la capability lo porta in
//    `can_edit_testata` + `non_editable_fields` (`isLocked`). La costante
//    `STATI_CODICI_ATTO_EDITABILI` specchiava la tabella per stato del BE,
//    ritirata lo stesso giorno.

// Lunghezze massime, speculari alle colonne di `vendite.contratti`
// (VARCHAR(15)/VARCHAR(15)/VARCHAR(100)) e al guard `_CODICI_ATTO_MAX_LEN` del
// BE, che resta la difesa vera: qui il `maxlength` serve solo a non far digitare
// all'operatore caratteri che verrebbero poi respinti.
const CODICI_ATTO_MAX_LEN = { cig: 15, cup: 15, commessa: 100 }

// I tre campi aperti dopo la bozza, dalla capability (BB `useTestataDocumento`,
// R-FE-3; regola del 2): fino al 2026-10-10 qui c'era `codiciAttoEditabili`,
// la prima copia della regola, con gli stati scritti a mano.
// ⭐ In CREATE editabili (slice S3-b, 2026-08-31): la whitelist di
//    `vendite.fn_create_contratto` li ammette dal changeSet `20260831-24` — un
//    CIG nasce con la gara, cioe' PRIMA del contratto. Senza dettaglio il BB
//    tiene il form aperto.
// ⚠️ `presente` e' il modo EDIT, non il dettaglio arrivato: prima che arrivi la
//    capability e' vuota e il BB dice «fermo» (fail-closed), come prima.
const testata = useTestataDocumento({
  caps,
  campi: CAMPI_FORM_TESTATA_CONTRATTO,
  readonlyPuro: () => props.readonly || parentReadonly.value,
  presente: () => isEdit.value,
  corpoProtetto: () => isReadonly.value,
})

// Il footer Salva compare in CREATE e in DRAFT (form pieno: `isReadonly`
// comprende gia' lo stato, via `isContractLocked`) oppure quando restano
// modificabili i soli tre riferimenti dell'atto.
const mostraFooterSalva = computed(
  () => !isReadonly.value || testata.modificabile.value,
)

// Sub-drawer
const righeVisible = ref(false)
const noteDrawerVisible = ref(false)
// Il pulsante «Gestisci note» standard, col numero delle note del documento
// (BB `useContatoreNote`: dal dettaglio, poi dal sotto-drawer dopo un salvataggio).
const contatoreNote = useContatoreNote(() => detail.value)

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
    // Riferimenti dell'atto (I8/D9). Esposti anche in CREATE dalla slice S3-b
    // (2026-08-31): la fn madre DB li whitelista dal changeSet `20260831-24`.
    codice_cig: null,
    codice_cup: null,
    codice_commessa: null,
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
    // Scheda di fornitura inline (BB `schedaFornitura`, come l'offerta)
    ...schedaVuota(),
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
}

function populateFromDetail(d) {
  const stessoCliente = form.value.billing_account_id === d.billing_account_id
    && form.value.billing_account_obj != null
  form.value = {
    emittente_fiscale_id: d.emittente_fiscale_id,
    billing_account_id: d.billing_account_id,
    // Il cliente per il lookup: lo stesso oggetto se il cliente non e' cambiato
    // (niente lampeggio alla ricarica), altrimenti lo rilegge
    // `ripristinaBillingAccount` qui sotto. ⛔ Fino al 2026-10-19 si costruiva a
    // mano dai campi del dettaglio, con la chiave sbagliata della ragione
    // sociale: riaperto, il campo mostrava il solo codice (collaudo di Tid).
    billing_account_obj: stessoCliente ? form.value.billing_account_obj : null,
    istanza_utility_id: d.istanza_utility_id,
    utility_id: d.utility_id,
    ambito: d.ambito || 'COMMODITY',
    valido_dal: d.valido_dal,
    valido_al: d.valido_al,
    data: d.data,
    parent_contratto_id: d.parent_contratto_id,
    categoria_cliente_id_snapshot: d.categoria_cliente_id_snapshot || null,
    codice_cig: d.codice_cig || null,
    codice_cup: d.codice_cup || null,
    codice_commessa: d.codice_commessa || null,
    fatturazione_immediata: d.fatturazione_immediata ?? false,
    listino_id: d.listino_id,
    tipo_variazione_globale: d.tipo_variazione_globale,
    valore_variazione_globale: d.valore_variazione_globale,
    valuta_id: d.valuta_id,
    ...schedaDaFornitura(d.utility),
  }
  if (!stessoCliente) ripristinaBillingAccount(form.value, d.billing_account_id)
}

// Forma derivata (refactor modalita 2026-05-15): "con_listino" se l'operatore
// ha indicato un listino di riferimento, "senza_listino" altrimenti. Usata per
// il badge informativo readonly nell'header drawer post-save. Non e' una scelta
// dell'operatore — segue automaticamente i campi compilati.
const formaDerivata = computed(() => {
  return form.value.listino_id ? FORMA_CONTRATTO.CON_LISTINO : FORMA_CONTRATTO.SENZA_LISTINO
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
  // il rifiuto della sovrapposizione (oggi E_CONTRATTO_OVERLAP_ESISTENTE) con un
  // generico "Payload contratto non valido"
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

// Carica dati all'apertura (il montaggio a fine animazione e' di AppDrawer).
// Alla chiusura resta solo l'invalidation del guard di versione, per scartare
// fetch stantii in caso di apertura/chiusura rapide.
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
    fissa()
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
    fissa()
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
  // ⛔ In modifica la utility del contratto e' immutabile (B-4 di Tid): il
  //    cliente si cambia DENTRO la stessa utility, e `utility_id` filtra il
  //    lookup. Riscriverla qui (col default dell'operatore alla pulizia, o con
  //    quella del BA) lascerebbe scegliere un cliente di un'altra utility, che
  //    il backend rifiuta al salvataggio.
  if (!item) {
    form.value.billing_account_id = null
    form.value.billing_account_obj = null
    form.value.istanza_utility_id = null
    // Ripristina il default utility quando si pulisce il BA: l'operatore
    // mantiene il filtro lookup BA sull'utility tipica del proprio EF
    // invece di tornare a "vedo tutti i BA". Allinea OffertaDrawer.
    if (!isEdit.value) form.value.utility_id = utilityDefaultId.value
    form.value.categoria_cliente_id_snapshot = null
    return
  }
  form.value.billing_account_id = item.id
  form.value.billing_account_obj = item
  form.value.istanza_utility_id = item.istanza_utility_id || null
  if (!isEdit.value) form.value.utility_id = item.utility_id || null
  // Pre-compila la categoria dal BA; l'operatore puo' cambiarla.
  form.value.categoria_cliente_id_snapshot = item.categoria_cliente_id || null
}

// Auto-fill valuta dal form-defaults BE (BB resolve_valuta_default), al cambio
// BA in CREATE: la valuta del BA vince (regola di coerenza dominio). Watcher
// condiviso `useBaFormDefaults` con guard latest-wins inclusa.
// ⭐ In creazione la scheda di fornitura segue il cliente scelto: quella che
//    l'anagrafica gli da', che l'operatore vede e corregge prima di salvare
//    (R-FE-3 di brief-db-indirizzi-documento-seguono-il-cliente, D-7 di Tid:
//    alla nascita il DB parte dall'anagrafica e applica la scheda del form).
const { inCorso: defaultsClienteInCorso } = useBaFormDefaults({
  form, isEdit, fetchDefaults: getContrattoFormDefaults, apply: applicaFornituraDaDefaults,
})

// Validazione FE (refactor modalita 2026-05-15: niente piu' check su modalita).
// Vincolo strutturale unico sulla coppia variazione globale: tipo e valore
// devono essere entrambi presenti o entrambi null (vincolo BE
// _validate_variazione_globale_coppia_coerente). Listino e variazione sono
// indipendenti: contratto senza listino e' valido (forma "senza_listino"),
// contratto con listino senza variazione e' valido (forma "con_listino"
// listino tal quale), contratto con listino + variazione e' valido.
const canSave = computed(() => {
  // I tre riferimenti dell'atto restano salvabili anche a contratto ATTIVO
  // (Q1): il lock post-DRAFT non li riguarda.
  if (isReadonly.value && !testata.modificabile.value) return false
  // Finche' arrivano i dati del cliente (BB `useBaFormDefaults`) il Salva
  // aspetta: la scheda di fornitura partirebbe vuota sopra quella
  // dell'anagrafica (D-7: il DB applica la scheda del form).
  if (defaultsClienteInCorso.value) return false
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
  // In bozza il cliente si cambia ma non si toglie (B-1 di Tid).
  if (isEdit.value) return !isContractLocked.value ? !!f.billing_account_id : true
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
  // Il payload PATCH va limitato ai campi che il form lascia toccare nello
  // stato corrente: fuori bozza la testata la ferma il lock del DB colonna per
  // colonna (`E_DOC_*`), e mandare campi spenti farebbe rifiutare l'intera PATCH.
  // - DRAFT:    tutti i campi
  // - ATTIVO:   valido_al + meta (via dialog "Cessa contratto") e i TRE
  //             RIFERIMENTI DELL'ATTO (I8/D9, decisione Q1 del 2026-08-29),
  //             che il form spedisce da qui
  // - CESSATO / ANNULLATO: nessuno
  //
  // ⛔ ATTENZIONE, ed e' la trappola di questa funzione: `buildPayload()` NON
  //    serve solo la PATCH — `handleSave` lo SPREADA dentro il payload di
  //    CREATE. Quindi ogni chiave aggiunta qui finisce anche nella create, e la
  //    create BE (`validate_allowed_keys` su `_CREATE_KEYS_TESTATA`) RIFIUTA
  //    l'intero payload se contiene una chiave che non ammette — non la ignora.
  //    Una chiave accettata in PATCH ma non in CREATE va quindi cancellata qui
  //    sotto, o rompe la creazione contratto.
  const stato = isEdit.value ? (detail.value?.stato_codice_interno || null) : STATO_CONTRATTO.DRAFT
  const isDraft = stato === STATO_CONTRATTO.DRAFT

  if (!isDraft) {
    // Post-DRAFT il form e' bloccato tranne i tre riferimenti dell'atto: si
    // spedisce SOLO quello che il BE accetta nello stato corrente. Mandare di
    // piu' significherebbe farsi rifiutare l'intera PATCH per campi che
    // l'operatore non ha nemmeno potuto toccare.
    if (testata.modificabile.value) return buildCodiciAttoPayload(f)
    // CESSATO/ANNULLATO: il Salva non e' nemmeno visibile. Payload vuoto per
    // sicurezza — le operazioni li' passano solo dal cambio stato.
    return {}
  }

  const payload = {
    ambito: f.ambito,
    valido_dal: toIsoDate(f.valido_dal),
    valido_al: toIsoDate(f.valido_al),
    data: toIsoDate(f.data),
    parent_contratto_id: f.parent_contratto_id || null,
    categoria_cliente_id_snapshot: f.categoria_cliente_id_snapshot || null,
    // Corsia di instradamento: accettata sia in create sia in PATCH dal
    // 2026-07-27 (changeset DB 20260727-40, che ha esteso la whitelist della
    // fn madre `vendite.fn_create_contratto`). Sempre un booleano, mai null:
    // la colonna e' NOT NULL e la fn madre filtra sulla presenza della chiave.
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
  // ⭐ Anche in CREATE dalla slice S3-b (2026-08-31): `_CREATE_KEYS_TESTATA` le
  //    ammette, e la whitelist della fn madre DB pure (`20260831-24`).
  // ⚠️ Le tre chiavi viaggiano SEMPRE, anche a `null`: sono colonne nullable, e
  //    mandare `null` significa «non compilato» — non e' il caso di
  //    `fatturazione_immediata`, che e' NOT NULL e dove la chiave va OMESSA.
  Object.assign(payload, buildCodiciAttoPayload(f))
  return payload
}

// Scopo: i tre riferimenti dell'atto (I8/D9), stessa forma in DRAFT e in ATTIVO.
// ⚠️ Stringa vuota -> null e non '': la colonna e' nullable e un '' sarebbe un
//    valore che SEMBRA un codice (`feedback_null_vs_empty`).
function buildCodiciAttoPayload(f) {
  return {
    codice_cig: f.codice_cig?.trim() || null,
    codice_cup: f.codice_cup?.trim() || null,
    codice_commessa: f.codice_commessa?.trim() || null,
  }
}

async function handleSave() {
  if (isEdit.value) {
    const payload = buildPayload()
    // Il cliente NON viaggia: il cambio si e' gia' salvato alla scelta, con la
    // conferma (BB `useCambioClienteDocumento`, 2026-10-19), e la scheda del
    // form e' gia' quella del cliente nuovo. Fino ad allora qui si mandava la
    // coppia BA/istanza e si tratteneva la scheda del cliente vecchio.
    // La scheda di fornitura viaggia se si cambia ancora (`can_edit_utility`:
    // il lock dei satelliti del DB).
    if (caps.flag('can_edit_utility')) {
      payload.utility = schedaDaForm(form.value)
    }
    const result = await execute(
      () => store.update(props.contrattoId, payload),
      { successMessage: t('vendite.contratti.contratto_salvato') }
    )
    if (result !== null) {
      // La fotografia e' il form com'e' ora, PRIMA della ricarica (come
      // l'offerta): la rilettura porta il cliente, la scheda e gli indirizzi
      // che il DB ha rifatto, e la sezione indirizzi segue il `detail` (R-FE-2).
      fissa()
      await refreshDetail()
      emit('saved', result)
    }
  } else {
    const f = form.value
    const payload = {
      emittente_fiscale_id: f.emittente_fiscale_id,
      billing_account_id: f.billing_account_id,
      istanza_utility_id: f.istanza_utility_id,
      utility_id: f.utility_id,
      // Valuta inviata SOLO in CREATE: snapshot immutabile post-INSERT
      // (non in _UPDATE_KEYS_TESTATA BE). Se null, il trigger DB la
      // risolve via fn_get_valuta_id (BA→emittente→gestore).
      valuta_id: f.valuta_id || null,
      ...buildPayload(),
    }
    // La scheda di fornitura com'e' a video: precompilata dall'anagrafica del
    // cliente e corretta dall'operatore. Il DB parte dall'anagrafica e ci
    // applica questa (D-7): quello che si vede e' quello che si scrive.
    payload.utility = schedaDaForm(f)
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('vendite.contratti.contratto_creato') }
    )
    if (result !== null) { fissa(); emit('saved', result) }
  }
}

// Ricarica dettaglio (usata dopo cambio stato o mutazioni righe/utility).
async function refreshDetail() {
  if (!props.contrattoId) return
  // `preserva`: salvare una riga o cambiare stato ricarica la testata, e senza
  // la modifica di testata non ancora salvata tornava com'era, in silenzio
  // (stesso difetto gia' corretto su ordini/DDT/preventivi, 2026-09-26).
  const applica = preserva()
  const d = await store.fetchDetail(props.contrattoId)
  detail.value = d
  populateFromDetail(d)
  applica()
}

// ⭐ Il cambio di cliente in modifica si salva subito, con conferma (BB
//    `useCambioClienteDocumento`, decisione di Tid 2026-10-19): il DB rifa'
//    indirizzi e scheda, e pannello e «Indirizzi» mostrano subito quelli del
//    cliente nuovo. La scheda non salvata del cliente vecchio si scarta.
useCambioClienteDocumento({
  form,
  detail,
  // La categoria la pre-compila la scelta del BA (`onBaSelected`): un Annulla
  // la riporta al salvato con BA e istanza, o resterebbe quella del cliente
  // scartato. A conferma resta nel form, correggibile, e si salva col Salva.
  colonne: [...CLIENTE_BA, 'istanza_utility_id', 'categoria_cliente_id_snapshot'],
  // La stessa condizione che spegne il lookup del cliente nel form.
  attivo: () => isEdit.value && detail.value != null && !isLocked('billing_account_id'),
  salva: (corpo) => execute(
    () => store.update(props.contrattoId, corpo),
    { successMessage: t('vendite.contratti.contratto_salvato') },
  ),
  ricarica: refreshDetail,
  scartaDipendenti: () => Object.assign(form.value, schedaDaFornitura(detail.value?.utility)),
  messaggio: 'vendite.cliente.cambio_messaggio_con_fornitura',
})

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
  const oggi = oggiAziendale()
  const beMin = parseIsoDate(cessaDialogAction.value?.min_date)
  return beMin && beMin > oggi ? beMin : oggi
})

// Programmata SOLO se strettamente futura. Data odierna = cessazione immediata.
const cessazioneProgrammata = computed(() => {
  if (!cessaDialogData.value) return false
  const scelta = giornoDi(cessaDialogData.value)
  return scelta !== null && scelta > oggiAziendale()
})

function openCessaDialog(action) {
  cessaDialogAction.value = action
  // default_date dal BE; fallback oggi solo se la fn non lo fornisce.
  cessaDialogData.value = parseIsoDate(action?.default_date) || oggiAziendale()
  // Il dialog evidenzia `valido_al` da `campiErrati`, che e' lo stesso del
  // form: un rifiuto precedente del form non deve aprirlo gia' in rosso.
  campiErrati.value = []
  cessaDialogVisible.value = true
}

// Il messaggio dell'esito lo decide la risposta: se la cessazione e'
// programmata lo dice il verbo del DB (`programmata`, brief-modello-documento-
// vendita §11.6). `cessazioneProgrammata` qui sopra resta solo l'anteprima del
// dialog, prima della conferma.
async function onConfermaCessazione() {
  const validoAl = toDateString(cessaDialogData.value)
  const targetState = cessaDialogAction.value?.target_state || STATO_CONTRATTO.CESSATO
  const result = await execute(
    () => store.cambiaStato(props.contrattoId, targetState, { validoAl }),
  )
  if (result !== null) {
    notify.success(result?.programmata
      ? t('vendite.contratti.cessa_dialog_success_programmata', { data: validoAl })
      : t('vendite.contratti.cessa_dialog_success_immediata'))
    cessaDialogVisible.value = false
    await refreshDetail()
  }
}

// Cambio stato (edit). Le azioni vengono dal backend:
// - requires_date=true  -> dialog con DatePicker (es. "cessa")
// - requires_confirm    -> confirmAction con label_key dell'azione
// - altrimenti          -> diretto

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
  // Transizione → ATTIVO: dialog dedicato con anteprima documento + allegati.
  // L'endpoint /emetti/ (multipart) orchestra atomic state + genera + allegati
  // (refactor 2026-05-28). NB: il BE rifiuta la transizione via /cambia-stato/
  // con E_VENDITE_VALIDAZIONE — questa intercettazione e' la sola via supportata.
  if (action.target_state === STATO_CONTRATTO.ATTIVO) {
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
      header: t('vendite.contratti.conferma_titolo'),
      message: t('vendite.contratti.conferma_cambio_stato', { stato: statoDestinazione(action) }),
      onAccept: () => eseguiCambioStato(action.target_state),
    })
    return
  }
  eseguiCambioStato(action.target_state)
}

// ⭐ L'annullo e' un gesto CONFERMABILE (brief-db-annullo-documento-con-
//    legami): con legami (offerta d'origine, righe di commessa da emettere) il
//    DB lo rifiuta (`confirm_and_retry`) finche' chi conferma non dichiara
//    quanti legami ha visto; la domanda la porta a video
//    `DocumentoAnnulloLegamiDialog`. Le altre transizioni restano su `execute`.
const cambioStato = useForzaturaConfermata()
const { richiestaConferma: domandaAnnullo } = cambioStato

async function eseguiCambioStato(targetState) {
  const opts = { successMessage: t('vendite.contratti.stato_cambiato') }
  // L'annullo: primo tentativo SEMPRE senza dichiarazione.
  const result = targetState === STATO_CONTRATTO.ANNULLATO
    ? await cambioStato.esegui(
      (dichiarazione) => store.cambiaStato(props.contrattoId, targetState, { dichiarazione }),
      opts,
    )
    : await execute(() => store.cambiaStato(props.contrattoId, targetState), opts)
  if (result !== null) await refreshDetail()
}

// Scopo: l'operatore ha visto i legami e conferma l'annullo: si ripete la
//        chiamata DICHIARANDO quanti erano.
async function onConfermaAnnullo(dichiarazione) {
  const result = await cambioStato.conferma(dichiarazione)
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
  const targetState = action?.target_state || STATO_CONTRATTO.ANNULLATO
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
  list.push(contatoreNote.azione({
    label: t('vendite.contratti.gestisci_note'),
    command: () => { noteDrawerVisible.value = true },
  }))
  return list
})

const onClose = useDrawerClose(emit, 'cancelled')
// Detail fuori scope (RLS) / inesistente → toast + chiusura, niente drawer vuoto.
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

// Il footer del drawer segue lo stato del documento (BB useFooterDocumento,
// D-11 di work-done/analisi-fe-chrome-drawer.md).
// «Modificabile» qui e' `mostraFooterSalva`: in CREATE e in DRAFT, piu' l'ATTIVO
// per i soli riferimenti dell'atto (Q1). NB: ATTIVO ammette tecnicamente anche
// la modifica di `valido_al` + meta (lock di testata del DB), ma
// l'unica modifica operativa li' e' la cessazione programmata, dal dialog «Cessa
// contratto». ⚠️ In ATTIVO la catena readonly e' accesa (`isContractLocked`):
// il Salva lo riaccende `footer-readonly`, i tre campi l'`app-escape` della
// loro sezione — e il payload di `handleSave` porta solo quelli.
// Le righe hanno un drawer loro: nessun form di riga qui.
const footerDrawer = useFooterDocumento({
  modificabile: () => mostraFooterSalva.value,
  presente: () => detail.value != null,
})

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotoCessa = useFotografiaDialog(() => ({ data: cessaDialogData.value }), { visibile: () => cessaDialogVisible.value })
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="props.visible"
    :title="t('vendite.contratti.contratto')"
    :icon="NAV_ICONS.CONTRATTI"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.COMPLEX"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="footerDrawer"
    :loading="loading"
    :save-disabled="!canSave"
    :footer-readonly="testata.footerReadonly.value"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >

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
        :severity="formaDerivata === FORMA_CONTRATTO.SENZA_LISTINO ? 'warn' : 'info'"
      />
      <template #status>
        <Tag
          :value="detail.stato_descrizione"
          :severity="statoContrattoSeverity(detail.stato_codice_interno)"
        />
      </template>
    </DrawerEntityHeader>

    <DrawerActionsBar :actions="drawerActions" :info-key="capabilities.stato_info_key || ''">
      <template #suffix>
        <EntityPdfButton
          :sorgente-code="SORGENTE_CODES.CONTRATTO"
          :entity-id="props.contrattoId"
          :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
          :pdf="capabilities.pdf"
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
      :versione="detail"
      :doc-id="contrattoId"
      @documento-chiuso="refreshDetail"
      :readonly="readonly || parentReadonly" />

    <!-- Banner contratto bloccato: in stati post-DRAFT ammessa solo
         modifica valido_al (programma cessazione) + cambio stato.
         Coerente con Profilo A whitelist BE. -->
    <Message v-if="isContractLocked && detail.stato_codice_interno !== STATO_CONTRATTO.CESSATO"
      severity="info" :closable="false" size="small">
      {{ t('vendite.contratti.banner_locked_attivo', { stato: detail.stato_descrizione }) }}
    </Message>
    <Message v-else-if="isContractLocked && detail.stato_codice_interno === STATO_CONTRATTO.CESSATO"
      severity="warn" :closable="false" size="small">
      {{ t('vendite.contratti.banner_locked_cessato') }}
    </Message>
  </template>

  <!-- === Emittente fiscale === -->
  <!-- Sezione separata sopra il cliente (pattern offerte/preventivi).
       Operatore con EF assegnato -> read-only auto-popolato dal profilo;
       admin globale (multi-EF) -> Select sugli EF disponibili.
       In edit mostra codice + ragione sociale denormalizzati dal record. -->
  <h4>{{ t('vendite.contratti.section_emittente') }}</h4>
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
  <h4>
    {{ t('vendite.contratti.section_cliente') }}
    <Tag v-if="baBadgeLabel" :value="baBadgeLabel" severity="info" class="ml-05" />
  </h4>
  <div class="form-grid-2col">
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_billing_account') }} <span v-if="!isContractLocked">*</span></label>
      <!-- `utility-id` pre-filtra il lookup BA sull'utility selezionata
           (default = utility dell'operatore via `utilityDefaultId`).
           `onBaSelected` sovrascrive `utility_id` con quella canonical
           del BA scelto, mantenendo coerenza FK. Allinea OffertaDrawer. -->
      <!-- In bozza il cliente si cambia (B-1 di Tid): dentro la stessa utility,
           che il lookup filtra; fuori bozza lo ferma il lock di testata. -->
      <BillingAccountLookup
        :model-value="form.billing_account_obj"
        :utility-id="form.utility_id"
        @update:model-value="onBaSelected"
        :placeholder="t('vendite.contratti.select_billing_account')"
        :disabled="isEdit && isLocked('billing_account_id')"
      />
    </div>
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_utility') }} <span v-if="!isEdit">*</span></label>
      <!-- Building block standard utility-per-ruolo-EF: le utility ammesse
           per il ruolo EF e per il ruolo CLIENTE (`utilities_tipi_ruolo`). Pre-popolato da `defaultForm()` via
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
        :disabled="isEdit && isLocked('ambito')" />
    </div>
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_categoria_cliente_snapshot') }}</label>
      <LookupSelect
        v-model="form.categoria_cliente_id_snapshot"
        rel="anagrafiche.categorie_clienti"
        :placeholder="t('vendite.contratti.select_categoria_cliente')"
        show-clear
        :disabled="isEdit && isLocked('categoria_cliente_id_snapshot')"
      />
    </div>
  </div>

  <!-- Corsia di fatturazione: instradamento deciso PRIMA che il contratto
       entri in commessa; dopo il push il flag e' inerte e il DB respinge
       la modifica. Disponibile sia in creazione sia in modifica; in ATTIVO
       la PATCH ammette solo la data di fine validita', quindi il campo
       risulta bloccato da `isReadonly`. -->
  <div class="form-grid-2col mt-1">
    <div class="form-field">
      <label for="ctr-fatt-immediata">{{ t('vendite.contratti.field_fatturazione_immediata') }}</label>
      <div class="app-form-inline-toggle">
        <ToggleSwitch
          input-id="ctr-fatt-immediata"
          v-model="form.fatturazione_immediata"
          :disabled="(isEdit && isLocked('fatturazione_immediata')) || isReadonly"
          :invalid="campiErrati.includes('fatturazione_immediata')" />
        <small class="app-text-muted">
          {{ t('vendite.contratti.fatturazione_immediata_hint') }}
        </small>
      </div>
    </div>
    <div class="form-field"></div>
  </div>

  <!-- === Riferimenti dell'atto (CIG / CUP / commessa) ===
       I8/D9: prima stavano su `anagrafiche.clienti`, cioe' su una riga PER
       FORNITURA, mentre nominano un CONTRATTO — una PA con tre contratti ha
       tre CIG. In fattura elettronica viaggiano nello stesso blocco
       (DatiContratto/DatiOrdineAcquisto), quindi stanno insieme.
       ⭐ Visibili anche in CREATE dalla slice S3-b (2026-08-31). Prima no:
       la whitelist della fn madre DB non li conosceva e li avrebbe SCARTATI
       in silenzio — caselle che invitano a scrivere un valore che il
       database butta via sono peggio di caselle assenti. Il changeSet
       `20260831-24` le ha ammesse, e il momento naturale per digitare un
       CIG e' proprio la creazione: nasce con la gara.
       ⭐ Editabili anche a contratto ATTIVO (Q1): il CIG di una gara arriva
       quando arriva. -->
  <!-- `app-escape` solo quando la catena e' in sola lettura ma i tre campi no
       (contratto ATTIVO, Q1): il corpo protetto li spegnerebbe. -->
  <div :class="{ 'app-escape': testata.sopraCorpoProtetto.value }">
    <h4>{{ t('vendite.contratti.section_riferimenti_atto') }}</h4>
    <div class="form-grid-3col">
      <div class="form-field">
        <label>{{ t('vendite.contratti.field_codice_cig') }}</label>
        <InputText v-model="form.codice_cig"
          :maxlength="CODICI_ATTO_MAX_LEN.cig"
          :disabled="testata.bloccato('codice_cig')"
          :invalid="campiErrati.includes('codice_cig')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.contratti.field_codice_cup') }}</label>
        <InputText v-model="form.codice_cup"
          :maxlength="CODICI_ATTO_MAX_LEN.cup"
          :disabled="testata.bloccato('codice_cup')"
          :invalid="campiErrati.includes('codice_cup')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.contratti.field_codice_commessa') }}</label>
        <InputText v-model="form.codice_commessa"
          :maxlength="CODICI_ATTO_MAX_LEN.commessa"
          :disabled="testata.bloccato('codice_commessa')"
          :invalid="campiErrati.includes('codice_commessa')" />
      </div>
    </div>
  </div>

  <!-- === Validità === -->
  <h4>{{ t('vendite.contratti.section_validita') }}</h4>
  <div class="form-grid-3col">
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_data') }} *</label>
      <DatePicker :model-value="parseIsoDate(form.data)"
        @update:model-value="form.data = toIsoDate($event)"
        :disabled="isEdit && isLocked('data')"
        :date-format="DATE_FORMAT" show-icon />
    </div>
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_valido_dal') }} *</label>
      <DatePicker :model-value="parseIsoDate(form.valido_dal)"
        @update:model-value="form.valido_dal = toIsoDate($event)"
        :disabled="isEdit && isLocked('valido_dal')"
        :date-format="DATE_FORMAT" show-icon />
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
        || detail?.stato_codice_interno === STATO_CONTRATTO.DRAFT
        || detail?.stato_codice_interno === STATO_CONTRATTO.CESSATO
        || (form.valido_al && detail?.stato_codice_interno === STATO_CONTRATTO.ATTIVO)">
      <label>
        {{ detail?.stato_codice_interno === STATO_CONTRATTO.CESSATO
          ? t('vendite.contratti.field_data_cessazione')
          : detail?.stato_codice_interno === STATO_CONTRATTO.ATTIVO && form.valido_al
            ? t('vendite.contratti.field_cessazione_programmata')
            : t('vendite.contratti.field_valido_al') }}
      </label>
      <DatePicker :model-value="parseIsoDate(form.valido_al)"
        @update:model-value="form.valido_al = toIsoDate($event)"
        :disabled="isEdit && isLocked('valido_al')"
        :invalid="campiErrati.includes('valido_al')"
        :date-format="DATE_FORMAT" show-icon show-button-bar />
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
    :readonly="readonly || parentReadonly"
    :capabilities="capabilities" />

  <!-- === Pricing (refactor modalita 2026-05-15) === -->
  <!-- Niente piu' SelectButton A/B/C: l'operatore compila campi opzionali
       (listino + variazione globale). La "forma" derivata e' un badge
       informativo readonly mostrato sopra in detail (composable
       `formaDerivata`). -->
  <h4>{{ t('vendite.contratti.section_pricing') }}</h4>

  <!-- Badge forma derivata: visibile in EDIT come audit visivo del path. -->
  <Message
    v-if="isEdit && detail"
    :severity="formaDerivata === FORMA_CONTRATTO.SENZA_LISTINO ? 'warn' : 'info'"
    :closable="false" size="small"
  >
    {{ t(`vendite.contratti.forma_${formaDerivata}_descrizione`) }}
  </Message>

  <div class="form-field">
    <label>{{ t('vendite.contratti.field_listino') }}</label>
    <!-- I listini della utility e dell'emittente del form, dal DB: la tendina
         non propone cio' che il salvataggio rifiuterebbe (F-2). -->
    <ListinoDocumentoSelect v-model="form.listino_id"
      :utility-id="form.utility_id"
      :emittente-fiscale-id="form.emittente_fiscale_id"
      :record="detail"
      :placeholder="t('vendite.contratti.select_listino_opzionale')"
      :invalid="campiErrati.includes('listino_id')"
      @update:model-value="onListinoChange"
      :disabled="isEdit && (isLocked('listino_id') || righeCount > 0)" />
    <small v-if="isEdit && righeCount > 0 && !isLocked('listino_id')"
      style="color: var(--p-yellow-700, #b45309);">
      <i :class="STATUS_ICONS.ERRORE" />
      {{ t('vendite.contratti.hint_listino_lock_righe', { n: righeCount }) }}
    </small>
    <small v-else class="app-text-muted">
      {{ t('vendite.contratti.hint_listino_opzionale') }}
    </small>
  </div>

  <div class="form-grid-2col">
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_tipo_variazione') }}</label>
      <TipoVariazioneSelect v-model="form.tipo_variazione_globale"
        scope="contratto"
        show-clear
        :disabled="isEdit && isLocked('tipo_variazione_globale')" />
    </div>
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_valore_variazione') }}</label>
      <InputNumber v-model="form.valore_variazione_globale"
        :min-fraction-digits="0" :max-fraction-digits="4" showButtons
        @update:model-value="onValoreVariazioneChange"
        :disabled="isEdit && isLocked('valore_variazione_globale')"
        :suffix="form.tipo_variazione_globale === 'PERCENTUALE' ? ' %' : ''"
        :invalid="campiErrati.includes('valore_variazione_globale')" />
      <small class="app-text-muted">{{ t('vendite.contratti.hint_valore_variazione') }}</small>
    </div>
  </div>

  <!-- Valuta: snapshot fissato al CREATE, immutabile in EDIT
       (allineato a preventivi/offerte). Pre-popolata da
       ApiContrattoFormDefaults via cascata BB resolve_valuta_default. -->
  <div class="form-grid-2col">
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_valuta') }}</label>
      <LookupSelect v-model="form.valuta_id" rel="config.valute"
        :placeholder="t('vendite.contratti.field_valuta')"
        :disabled="isEdit"
        show-clear />
    </div>
  </div>

  <!-- === Tipo/Classe utenza (editabile in BOZZA, readonly dopo) === -->
  <h4>{{ t('vendite.contratti.section_utenza') }}</h4>
  <div class="form-grid-2col">
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_tipo_utenza') }}</label>
      <LookupSelect v-model="form.utility_tipo_utenza_id" rel="config.tipi_utenze"
        :placeholder="t('vendite.contratti.select_tipo_utenza')" show-clear
        :disabled="schedaBloccata" />
    </div>
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_classe_utenza') }}</label>
      <LookupSelect v-model="form.utility_classe_utenza_id" rel="config.classi_utenze"
        :placeholder="t('vendite.contratti.select_classe_utenza')" show-clear
        :disabled="schedaBloccata" />
    </div>
  </div>
  <!-- I due parametri della scheda, come sull'offerta: l'operatore vede quello
       che l'anagrafica scrive e lo corregge (D-7 di Tid). -->
  <div class="form-grid-2col">
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_param_1_num') }}</label>
      <InputNumber v-model="form.utility_param_1_num"
        :min-fraction-digits="0" :max-fraction-digits="6"
        :disabled="schedaBloccata" />
    </div>
    <div class="form-field">
      <label>{{ t('vendite.contratti.field_param_2_txt') }}</label>
      <InputText v-model="form.utility_param_2_txt" :disabled="schedaBloccata" />
    </div>
  </div>

  <!-- L'area inline "Documenti generati" e' stata rimossa 2026-07-16
       (doppione): l'archivio PDF si consulta dal pulsante PDF in testata
       (EntityPdfButton -> PdfDocumentiSorgenteDialog, stesso BB con in
       piu' expand automatico e append allegati). Il seed pdf_mode
       ANNULLATO=ARCHIVE (regola unica 5 domini: annullare non cancella
       la storia) tiene il pulsante consultabile anche sugli annullati. -->

    <!-- Sub-drawer: gestione righe -->
    <ContrattoRigheDrawer
      v-if="isEdit && detail"
      :visible="righeVisible"
      @update:visible="v => righeVisible = v"
      :contratto-id="props.contrattoId"
      :emittente-fiscale-id="detail.emittente_fiscale_id ?? null"
      :contratto-forma="formaDerivata"
      :contratto-numero="detail.numero"
      :contratto-cliente="detail.ba_ragione_sociale"
      :contratto-valido-dal="detail.valido_dal"
      :contratto-valido-al="detail.valido_al"
      :contratto-stato-codice="detail.stato_codice_interno"
      :contratto-stato-descrizione="detail.stato_descrizione"
      :righe-modificabili="caps.flag('can_edit_righe')"
      @changed="refreshDetail"
    />

    <!-- Sub-drawer note partizionate. Le righe sono passate per popolare il
         dropdown RIGA del form: detail.righe e' gia' caricato dal padre. -->
    <ContrattoNoteDrawer
      v-if="isEdit && detail"
      v-model:visible="noteDrawerVisible"
      @saved="contatoreNote.aggiorna"
      :contratto-id="props.contrattoId"
      :righe="detail.righe || []"
    />

    <!-- La conferma dell'annullo di un contratto con legami: aperta dalla
         domanda del DB, chiusa dalla conferma o dalla rinuncia. -->
    <DocumentoAnnulloLegamiDialog
      v-if="contrattoId"
      :visible="domandaAnnullo !== null"
      base-path="/vendite/contratti"
      :doc-id="contrattoId"
      :header="t('vendite.contratti.azione_annulla')"
      :domanda="domandaAnnullo"
      :loading="cambioStato.loading.value"
      :readonly="readonly || parentReadonly"
      @conferma="onConfermaAnnullo"
      @cancel="cambioStato.annulla()"
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
    <AppDialog
      :conferma-uscita="fotoCessa.chiudiConConferma" v-model:visible="cessaDialogVisible"
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
        <DatePicker v-model="cessaDialogData" :date-format="DATE_FORMAT"
          show-icon show-button-bar :min-date="cessaDialogMinDate"
          :invalid="campiErrati.includes('valido_al')" />
      </div>
      <Message :severity="cessazioneProgrammata ? 'info' : 'warn'"
        :closable="false" class="mt-1" size="small">
        {{ cessazioneProgrammata
          ? t('vendite.contratti.cessa_dialog_warning_programmata')
          : t('vendite.contratti.cessa_dialog_warning_immediata') }}
      </Message>
    </AppDialog>
  </AppDrawer>
</template>

