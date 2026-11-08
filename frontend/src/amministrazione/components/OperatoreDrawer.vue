<script setup>
// Scopo: Drawer unificato creazione/modifica operatore.
// Sezioni: Soggetto (resolver in crea, banner in modifica),
// Auth (solo crea), Dati anagrafici, Collocazione.
// Tabs: Dati + Permessi (permessi solo in modifica). Lo scope emittenti
// fiscali sta nei Dati (solo modifica) dal 2026-10-06.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOperatoriStore } from '../stores/operatori'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve, unisciFotografie } from '../../core/composables/useDrawerFormPreserve'
import { useAuthUser } from '../../core/composables/useAuthUser'
import { useLookup } from '../../core/composables/useLookup'
import { listUnitaOrganizzative, invitaOperatore, reinviaInvito, getCredenzialePerEmail } from '../api/amministrazione'
import { listEmittentiFiscali } from '../../core/apiCore'
import { DATE_FORMAT, DRAWER_WIDTH, MANAGE_ICONS, TIPO_RUOLO } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate, displayTimestamp, parseIsoDate, toDateStringOrNull } from '../../core/utils/date'
import { capitalizeWords } from '../../core/utils/string'
import { isEmailValid } from '../../core/utils/validators'
import { useNotify } from '../../core/composables/useNotify'
import { useEsitoInvito } from '../../core/composables/useEsitoInvito'
import { bloccoAttivo, motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useForzaturaConfermata } from '../../core/composables/useForzaturaConfermata'
import { etichettaRuoloApplicativo } from '../../core/utils/i18nLabel'
import SoggettoResolver from '../../anagrafiche/components/SoggettoResolver.vue'
import SoggettoMessageBanner from '../../core/components/SoggettoMessageBanner.vue'
import AuthUserForm from '../../core/components/AuthUserForm.vue'
import OperatorePermessiTab from './OperatorePermessiTab.vue'
import CredenzialeAzioni from './CredenzialeAzioni.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import AppDialog from '../../core/components/AppDialog.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import RadioButton from 'primevue/radiobutton'
import ToggleSwitch from 'primevue/toggleswitch'
import Tab from 'primevue/tab'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useConfirmAction } from '../../core/composables/useConfirmAction'

const { t, te } = useI18n()
const store = useOperatoriStore()
const { execute, loading, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()
const { notificaEsitoInvito } = useEsitoInvito()
const injectedReadonly = useInjectReadonly()

// ⭐ La creazione e' un gesto a DUE TEMPI quando l'email e' gia' di una
// credenziale (F-4, brief-db-credenziale-per-email §3): il DB rifiuta il primo
// tentativo (`E_CREDENZIALE_DA_CONFERMARE`, `ui_action = confirm_and_retry`) e
// accetta il secondo che DICHIARA l'id della credenziale vista. Il BB
// riconosce il comportamento, non il codice. ⛔ Il primo tentativo parte
// sempre senza `riusa_auth_user_id`: dichiararlo d'ufficio sarebbe un riuso
// silenzioso, cioe' il difetto che il `20260925-51` ha chiuso.
const creazione = useForzaturaConfermata()
const { richiestaConferma } = creazione
// La credenziale letta per il dialog: {auth_user_id, username, vesti}.
const credenzialeDaConfermare = ref(null)
// L'email del tentativo in corso (non reattiva: non serve alla resa).
let emailInDomanda = null
const dialogRiusoVisibile = computed(() =>
  richiestaConferma.value !== null && credenzialeDaConfermare.value !== null)

// Building block: auth user (solo creazione). Senza password: la sceglie
// l'operatore attivando l'invito (regola unica, L-3).
const auth = useAuthUser({ conPassword: false })

// SoggettoResolver: sotto-drawer per cerca/crea soggetto (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)

// Lookup
const unitaOrg = useLookup(listUnitaOrganizzative, { immediate: true })
const emittentiFiscali = useLookup(listEmittentiFiscali, { immediate: true })

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  authUserId: { type: Number, default: null },
  // Sola lettura CUMULATIVA con quella iniettata (standard drawer admin): il
  // chiamante può imporla anche dove il contesto non la fornisce, e non può
  // toglierla dove il contesto la impone.
  readonly: { type: Boolean, default: false }
})


const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const isReadonly = computed(() => props.readonly || injectedReadonly.value)
const invitaLoading = ref(false)
const emailEditInvalid = ref(false)

// Scopo: Mostra il pulsante invito quando il DB dice che l'operatore e'
// invitabile (`can_invite` di fn_get_operatore_detail: veste spenta, nella
// finestra, email presente). ⛔ Non ricopiare qui la regola: fino al
// 2026-09-25 era `!last_login && is_active`, e con la veste che nasce spenta
// (`is_active` falso) il pulsante non compariva mai.
const canInvite = computed(() => isEdit.value && store.currentOperatore?.can_invite === true)
// Scopo: Perche' l'invito non si puo' mandare: il motivo del DB
// (`invite_reason` codice + `invite_reason_key`, §16 del brief blocco-login),
// reso dal BB `bloccoMotivo` (chiave mancante ⇒ si vede il codice).
// ⛔ Nessun ramo su `veste_attiva`: dedurne «accesso gia' attivo» era una
// seconda copia della regola, giusta solo per l'ordine dei motivi del DB.
// Scopo: La frase del motivo di un verbo, '' quando l'azione e' ammessa.
function motivoSeBloccato(bloccato, prefisso) {
  return bloccato ? motivoBloccoRiga(t, te, store.currentOperatore, prefisso) : ''
}
const inviteReason = computed(() =>
  motivoSeBloccato(isEdit.value && !!store.currentOperatore && !canInvite.value, 'invite'))
// Scopo: Spegnere l'accesso e togliere il super admin all'ultimo SUPER_ADMIN
// attivo: il DB li rifiuta (trigger), il dettaglio lo dice prima
// (`can_disable`, `can_demote_super_admin`). Stato ⇒ controllo spento col
// motivo. `can_demote_super_admin` NULL = azione non applicabile: acceso
// (`bloccoAttivo` guarda il flag `=== false`).
const disableBloccato = computed(() =>
  isEdit.value && bloccoAttivo(store.currentOperatore, 'disable', 'can_disable'))
const demoteBloccato = computed(() =>
  isEdit.value && bloccoAttivo(store.currentOperatore, 'demote', 'can_demote_super_admin'))
const disableReason = computed(() => motivoSeBloccato(disableBloccato.value, 'disable'))
// Scopo: ⛔ D-3 (2026-10-04) — l'interruttore SPEGNE soltanto. Una veste
// spenta (disabilitata, o mai attivata) si riaccende col reinvio
// dell'invito, e la accende la persona attivando: da spento resta fermo col
// perche', e il pulsante d'invito sotto (da `can_invite`) e' la strada. Il
// backend rifiuta comunque `attivo: true` su una veste spenta.
const vesteSpenta = computed(() =>
  isEdit.value && !!store.currentOperatore && store.currentOperatore.veste_attiva !== true)
const demoteReason = computed(() => motivoSeBloccato(demoteBloccato.value, 'demote'))
// Scopo: La data di fine del RAPPORTO, spenta per l'ultimo SUPER_ADMIN senza
// data di fine (`can_set_valido_al` di fn_get_operatore_detail, brief-db-veste-
// utilizzabile §10): il DB la rifiuterebbe (409), il dettaglio lo dice prima.
// Chi ha gia' una data di fine risponde `true`: la puo' cambiare o togliere.
const validoAlBloccato = computed(() =>
  isEdit.value && bloccoAttivo(store.currentOperatore, 'valido_al', 'can_set_valido_al'))
const validoAlReason = computed(() => motivoSeBloccato(validoAlBloccato.value, 'valido_al'))
// La fine non precede l'inizio (lo giudica il DB, E_DATA_AL_MINORE_DAL): il
// calendario non la offre nemmeno.
const validoAlMin = computed(() => parseIsoDate(form.value.valido_dal) ?? undefined)
const hasBeenInvited = computed(() => !!store.currentOperatore?.invito_inviato_at)

// Multi-face auth Stage B: il vecchio radio ruolo_sistema (ADMIN/OPERATIVO/
// DISABILITATO) e' sostituito da due toggle indipendenti:
//   - is_super_admin: binding al profilo SUPER_ADMIN (id 9100)
//   - attivo:         stato della veste OPERATORE (`veste_attiva`): si
//                     spegne da qui, si riaccende solo con l'invito (D-3)
// Il ruolo applicativo resta implicito = OPERATORE per questo drawer
// (operatori interni). Portali e shop useranno drawer dedicati.
const INITIAL_FORM = Object.freeze({
  cognome: '',
  nome: '',
  email: '',
  is_super_admin: false,
  attivo: true,
  qualifica_id: null,
  unita_organizzativa_id: null,
  valido_dal: null,
  valido_al: null,
  soggetto_id: null,
  ragione_sociale: null,
  codice_fiscale: null
})

const form = ref({ ...INITIAL_FORM })
// Modifiche non salvate: fotografia all'apertura, e chiudere con modifiche
// chiede conferma (BB useDrawerFormPreserve). In creazione username/email
// stanno in `auth.form` e il soggetto in `soggettoSelezionato`: il confronto
// li raccoglie accanto al form (chiavi proprie, `form` ha gia' email/soggetto_id).
const formSalvato = computed(() => ({
  ...form.value,
  auth_username: auth.form.username,
  auth_email: auth.form.email,
  soggetto_selezionato_id: soggettoSelezionato.value?.id ?? null
}))
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(formSalvato, { visibile: () => props.visible })

// ═══ SCOPE EMITTENTI FISCALI (solo modifica) ═══════════════════════════════
// ⭐ Sta nei Dati, non nel pannello Permessi (Tid, 2026-10-06): e' il
//    perimetro dell'operatore — quale emittente vede — come il reparto e' la
//    sua collocazione, non una regola su area, oggetto o azione.
// ⚠️ Ha il SUO endpoint (`PUT .../emittenti-scope/`), quindi la SUA
//    fotografia: il Salva manda lo scope solo se e' cambiato, e se i dati
//    passano e lo scope no, i dati restano salvati e lo scope resta da
//    salvare (stessa regola del Salva unico dei permessi).
// ⚠️ Si confronta COME LO MANDA il Salva: con GLOBAL l'emittente non viaggia,
//    quindi un emittente scelto e poi abbandonato non e' una modifica.
const scopeMode = ref('GLOBAL')
const scopeEmittenteId = ref(null)

// Scopo: Payload dello scope: GLOBAL -> emittenti_ids: []; SINGLE -> [id].
// La validazione e' sul BE (E_AMM_SCOPE_NON_AMMESSO se SINGLE senza
// emittente): qui si blocca solo il Salva, per evitare il round-trip.
function buildScopePayload() {
  if (scopeMode.value === 'GLOBAL') return { scope_mode: 'GLOBAL', emittenti_ids: [] }
  return {
    scope_mode: 'SINGLE',
    emittenti_ids: scopeEmittenteId.value != null ? [scopeEmittenteId.value] : [],
  }
}
const scopeLocale = computed(() => buildScopePayload())
const scopeFoto = useDrawerFormPreserve(scopeLocale, { visibile: () => props.visible })

// Capability esposte dal BE: modalita' ammesse e blocco col suo motivo.
const allowedScopeModes = computed(() => store.emittentiScope.allowed_scope_modes || ['GLOBAL', 'SINGLE'])
const canChangeScope = computed(() => store.emittentiScope.can_change_scope !== false)
const changeScopeReason = computed(() => store.emittentiScope.change_scope_reason || null)
const scopeModeOptions = computed(() => [
  { value: 'GLOBAL', label: t('amministrazione.scope_mode_global'), disabled: !allowedScopeModes.value.includes('GLOBAL') },
  { value: 'SINGLE', label: t('amministrazione.scope_mode_single'), disabled: !allowedScopeModes.value.includes('SINGLE') },
])
const canSaveScope = computed(() =>
  canChangeScope.value
  && allowedScopeModes.value.includes(scopeMode.value)
  && (scopeMode.value !== 'SINGLE' || scopeEmittenteId.value != null)
)

// Scopo: Allinea lo scope a video a quello dello store e lo fotografa.
function syncScope() {
  scopeMode.value = store.emittentiScope.scope_mode || 'GLOBAL'
  scopeEmittenteId.value = (store.emittentiScope.emittenti_ids || [])[0] ?? null
  scopeFoto.fissa()
}

// Tab Permessi: ha la sua fotografia e il suo Salva (espone `modificato`,
// `chiudiConConferma`, `salva`, `puoSalvare`, `salvando`). Il footer e' uno:
// sulla scheda Permessi Salva chiama `salva` della scheda, sui Dati `onSave`.
// Chiudere il drawer chiede conferma se UNO dei due ha modifiche, con un
// solo dialog.
const permessiTab = ref(null)
const tutto = unisciFotografie({ modificato, chiudiConConferma }, scopeFoto, () => permessiTab.value)
const modificatoTutto = tutto.modificato

// Scopo: Reset form a valori iniziali.
function resetForm() {
  soggettoSelezionato.value = null
  emailEditInvalid.value = false
  auth.reset()
  form.value = { ...INITIAL_FORM }
}


// Carica dati quando il drawer si apre
watch(() => props.visible, async (val) => {
  // La domanda di riuso vive col drawer: si chiude con lui (il dialog e'
  // teleportato nel body, e resterebbe a video sopra un drawer chiuso) e non
  // sopravvive a una riapertura, dove l'email potrebbe essere un'altra.
  onAnnullaRiuso()
  if (!val) return
  emailEditInvalid.value = false
  activeTab.value = 'dati'
  if (isEdit.value && props.authUserId) {
    await Promise.all([
      store.fetchDetail(props.authUserId),
      store.fetchEmittentiScope(props.authUserId),
    ])
    syncScope()
    const u = store.currentOperatore
    if (u) {
      form.value = {
        username: u.username || '',
        cognome: u.soggetto_cognome || u.last_name || '',
        nome: u.soggetto_nome || u.first_name || '',
        email: u.email || '',
        // Multi-face auth: i flag nativi vengono dal BE. ⛔ L'interruttore
        // «Accesso attivo» e' lo stato della VESTE (`veste_attiva`), non
        // `attivo` del dettaglio, che e' la risorsa umana: un operatore
        // invitato e non ancora attivato ha il rapporto aperto e la veste
        // spenta, e fino al 2026-10-04 l'interruttore lo mostrava acceso.
        is_super_admin: u.is_super_admin === true,
        attivo: u.veste_attiva === true,
        qualifica_id: null,
        unita_organizzativa_id: u.unita_organizzativa_id,
        valido_dal: u.valido_dal || null,
        valido_al: parseIsoDate(u.valido_al),
        soggetto_id: u.soggetto_id || null,
        ragione_sociale: u.ragione_sociale_completa || null,
        codice_fiscale: u.codice_fiscale || null,
        last_login: u.last_login || null
      }
      fissa()
    }
  } else {
    resetForm()
    fissa()
    scopeMode.value = 'GLOBAL'
    scopeEmittenteId.value = null
    scopeFoto.fissa()
  }
})

// Scopo: Pre-compila email dal soggetto se il campo auth e' vuoto.
function prefillEmail(data) {
  if (data.email && !auth.form.email) {
    auth.form.email = data.email
  }
}

function onSoggettoSelezionato(data) {
  soggettoSelezionato.value = data
  prefillEmail(data)
}

function onSoggettoCreato(data) {
  soggettoSelezionato.value = data
  prefillEmail(data)
}

function clearSoggetto() {
  soggettoSelezionato.value = null
}

// Scopo: Valida il formato email in modifica usando il building block condiviso.
function validateEditEmail() {
  emailEditInvalid.value = !!form.value.email?.trim() && !isEmailValid(form.value.email)
}

// Scopo: Rimuove lo stato errore mentre l'utente corregge il campo email.
function clearEditEmailInvalid() {
  if (emailEditInvalid.value) emailEditInvalid.value = false
}

// Scopo: Salva operatore (crea o aggiorna).
// Contract multi-face (Fase 7): {is_super_admin, attivo, ...}. Il backend
// gestisce binding SUPER_ADMIN + stato identita_digitali in modo
// ortogonale tra i due flag.
// ⛔ Spegnere l'interruttore E' «Disabilita» (2026-10-04): il backend chiude
//    anche il rapporto a oggi, le sessioni e gli inviti della veste. Si
//    conferma al Salva, dove avviene, e solo se la veste PASSA da accesa a
//    spenta — la stessa transizione che il backend tratta da spegnimento: un
//    operatore gia' spento si salva senza domande.
async function onSave() {
  if (isEdit.value) {
    const payload = {
      email: form.value.email,
      first_name: form.value.nome,
      last_name: form.value.cognome,
      is_super_admin: form.value.is_super_admin,
      attivo: form.value.attivo,
      unita_organizzativa_id: form.value.unita_organizzativa_id
    }
    // La data di fine viaggia solo se e' cambiata: `null` la TOGLIE, e un
    // salvataggio che non la tocca non e' un gesto sulla scadenza.
    const validoAl = toDateStringOrNull(form.value.valido_al)
    if (validoAl !== (store.currentOperatore?.valido_al || null)) payload.valido_al = validoAl
    // I dati si mandano sempre, salvo quando l'unica modifica e' lo scope:
    // li' un PUT dei dati identici sarebbe una scrittura senza motivo.
    const inviaDati = modificato.value || !scopeFoto.modificato.value
    const inviaScope = scopeFoto.modificato.value
    const aggiorna = async () => {
      if (inviaDati) {
        const result = await execute(() => store.update(props.authUserId, payload))
        if (result === null) return
        fissa()
      }
      if (inviaScope) {
        const result = await execute(() => store.saveEmittentiScope(props.authUserId, buildScopePayload()))
        if (result === null) {
          // I dati, se c'erano, sono salvati: la lista lo deve sapere.
          if (inviaDati) emit('saved')
          return
        }
        scopeFoto.fissa()
      }
      notify.success(t('notifications.save_success'))
      emit('saved')
    }
    if (!vesteSpenta.value && form.value.attivo === false) {
      confirmAction({
        header: t('amministrazione.disabilita_title'),
        message: t('amministrazione.disabilita_confirm'),
        onAccept: aggiorna,
      })
      return
    }
    await aggiorna()
  } else {
    // Validazione client-side per creazione
    const authErrors = auth.validate()
    if (!form.value.qualifica_id) authErrors.push('qualifica_id')
    if (authErrors.length) {
      notify.error(t('notifications.validation_error'))
      return
    }

    const sogg = soggettoSelezionato.value
    // Contract multi-face (Fase 7): il payload create accetta `is_super_admin`
    // direttamente. Il BE rifiuta `ruolo_sistema` con E_AMM_VALIDAZIONE.
    // L'utente creato e' sempre attivo (la disabilitazione passa dal comando
    // dedicato `/disabilita/` in un secondo momento).
    const payload = {
      soggetto_id: sogg?.id || null,
      cognome: sogg?.cognome || null,
      nome: sogg?.nome || null,
      email: auth.form.email,
      username: auth.form.username,
      is_super_admin: form.value.is_super_admin,
      qualifica_id: form.value.qualifica_id,
      unita_organizzativa_id: form.value.unita_organizzativa_id
    }
    // L'email della domanda e' quella del PAYLOAD che si ripetera', non quella
    // del form al momento del dialog: dialog e ripetizione parlano della stessa.
    emailInDomanda = payload.email
    const result = await creazione.esegui(
      (dichiarazione) => store.create({ ...payload, ...dichiarazione }),
      { successMessage: t('amministrazione.operatore_creato') }
    )
    await dopoTentativoCreazione(result)
  }
}

// Scopo: Esito di un tentativo di creazione (primo o confermato). Creato ->
//        chiude; domanda del DB -> legge la credenziale e apre il dialog. Anche
//        dopo la conferma: se la credenziale e' cambiata nel frattempo, il DB
//        chiede di nuovo e il dialog si ripropone coi dati NUOVI.
async function dopoTentativoCreazione(result, domandaPrecedente = null) {
  if (result !== null) {
    credenzialeDaConfermare.value = null
    // Email gia' di una credenziale (D-6): la persona entrera' col suo
    // username e la sua password, e l'admin deve saperlo.
    if (result.credenziale_riusata) {
      notify.warn(t('amministrazione.credenziale_riusata', { username: result.username }))
    }
    fissa()
    emit('saved')
  } else if (richiestaConferma.value !== null && richiestaConferma.value !== domandaPrecedente) {
    // Solo una domanda NUOVA del DB si rilegge: dopo un errore vero alla
    // conferma la domanda resta quella di prima, e il dialog anche.
    await leggiCredenzialeDaConfermare()
  }
}

// Scopo: Legge la credenziale dell'email (B-20) per il dialog: la STESSA
//        lettura del rifiuto del DB (`fn_get_credenziale_per_email`), quindi
//        dialog e rifiuto dicono la stessa cosa.
async function leggiCredenzialeDaConfermare() {
  credenzialeDaConfermare.value = null
  const dati = await execute(() => getCredenzialePerEmail(emailInDomanda))
  credenzialeDaConfermare.value = dati?.credenziale ?? null
  if (credenzialeDaConfermare.value === null) {
    // Lettura fallita (toast gia' mostrato) o credenziale sparita nel frattempo:
    // non c'e' niente da confermare, si chiude la domanda.
    if (dati !== null) notify.warn(t('amministrazione.riuso_credenziale_sparita'))
    creazione.annulla()
  }
}

// Scopo: L'admin conferma il riuso: si ripete la creazione DICHIARANDO l'id
//        della credenziale che ha visto nel dialog.
async function onConfermaRiuso() {
  const domanda = richiestaConferma.value
  const result = await creazione.conferma({
    riusa_auth_user_id: credenzialeDaConfermare.value.auth_user_id,
  })
  await dopoTentativoCreazione(result, domanda)
}

// Scopo: L'admin rinuncia: la domanda si chiude, il form resta com'e' (puo'
// correggere l'email e salvare di nuovo).
function onAnnullaRiuso() {
  creazione.annulla()
  credenzialeDaConfermare.value = null
}


// Tab attivo. Riportato a 'dati' a ogni apertura del drawer: il tab
// 'permessi' esiste solo in modifica, quindi riaprendo in creazione un
// valore residuo punterebbe a un tab inesistente (nessun pannello reso).
const activeTab = ref('dati')

// ⭐ La larghezza segue il TAB, e non è un vezzo: i due tab chiedono due
// stanze diverse. «Dati» è un form a colonna singola — a 1360px sarebbe una
// riga di campi persi in mezzo al bianco. «Permessi» è una matrice
// slot/override a cinque colonne (voce, ereditato, override, stato, azione)
// per 13 aree, 34 azioni e 12 oggetti: a 800px le colonne si strizzano
// proprio dove la schermata esiste per farsi leggere.
// ℹ️ `XLARGE` è la taglia che la costante dedica alle «matrici
// parametri-per-entità (utility, slot/override)».
// La scheda Permessi ha il suo Salva: il footer lo chiama quando e' attiva.
const suPermessi = computed(() => activeTab.value === 'permessi')

const larghezzaDrawer = computed(() =>
  activeTab.value === 'permessi' ? DRAWER_WIDTH.XLARGE : DRAWER_WIDTH.COMPLEX
)

// Computed: form creazione completo
const canSaveCreate = computed(() =>
  !!soggettoSelezionato.value
  && !!auth.form.username.trim()
  && isEmailValid(auth.form.email)
  && !!form.value.qualifica_id
)

// Computed: form modifica completo
const canSaveEdit = computed(() =>
  isEmailValid(form.value.email)
  && (!scopeFoto.modificato.value || canSaveScope.value)
)

const canSave = computed(() => isEdit.value ? canSaveEdit.value : canSaveCreate.value)

// Scopo: Invia o reinvia invito operatore con conferma.
function onInvita() {
  const isReinvio = hasBeenInvited.value
  confirmAction({
    header: t('amministrazione.invito_confirm_title'),
    message: isReinvio ? t('amministrazione.reinvio_confirm_msg') : t('amministrazione.invito_confirm_msg'),
    onAccept: async () => {
      invitaLoading.value = true
      try {
        const apiFn = isReinvio ? reinviaInvito : invitaOperatore
        const res = await apiFn(props.authUserId)
        const data = res.data?.data
        const msg = data?.email
          ? t('amministrazione.invito_inviato') + ` (${data.email})`
          : t('amministrazione.invito_inviato')
        // `inviato: false` = link creato, email non partita: avviso (F-3).
        notificaEsitoInvito(data, msg)
        // Ricarica dettaglio per aggiornare invito_inviato_at
        await store.fetchDetail(props.authUserId)
      } catch (err) {
        const errMsg = err?.response?.data?.error?.message || t('common.error')
        notify.error(errMsg)
      } finally {
        invitaLoading.value = false
      }
    }
  })
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <!-- Il footer segue la scheda: era Annulla/Salva sui Dati e «Chiudi» sui
       Permessi — sostituito il 2026-10-04: ora Annulla/Salva su tutte e due
       le schede, e sui Permessi il Salva e' quello della scheda (§7.4 del
       brief-db-permessi-tetto-area). La larghezza pure
       (`larghezzaDrawer`: XLARGE sui permessi, COMPLEX altrove). -->
  <AppDrawer
    :visible="props.visible"
    :title="t('amministrazione.operatore')"
    :icon="NAV_ICONS.OPERATORE"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="larghezzaDrawer"
    :readonly="isReadonly"
    :modificato="modificatoTutto"
    :conferma-uscita="tutto.chiudiConConferma"
    footer="form"
    :loading="suPermessi ? !!permessiTab?.salvando : (loading || creazione.loading.value)"
    :save-disabled="suPermessi ? !permessiTab?.puoSalvare : !canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="suPermessi ? permessiTab?.salva() : onSave()"
  >
    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="dati">{{ t('amministrazione.tab_dati') }}</Tab>
        <Tab v-if="isEdit" value="permessi">{{ t('amministrazione.tab_permessi') }}</Tab>
      </TabList>
      <TabPanels>
      <TabPanel value="dati">
        <!-- === Sezione Soggetto === -->
        <h4>{{ t('amministrazione.section_persona') }}</h4>

        <!-- Modifica: banner soggetto sola lettura -->
        <div v-if="isEdit && form.soggetto_id">
          <SoggettoMessageBanner
            :ragione-sociale="form.ragione_sociale || `${form.cognome} ${form.nome}`.trim()"
            :id-fiscale="form.codice_fiscale || form.partita_iva"
          />
        </div>

        <!-- Creazione: resolver soggetto -->
        <template v-if="!isEdit">
          <div v-if="soggettoSelezionato">
            <SoggettoMessageBanner
              :ragione-sociale="soggettoSelezionato.ragione_sociale"
              :id-fiscale="soggettoSelezionato.cf || soggettoSelezionato.piva"
            />
            <Button :label="t('resolver.change')" :icon="MANAGE_ICONS.EDIT"
              text size="small" class="mt-1" @click="clearSoggetto" />
          </div>
          <div v-else>
            <Button :label="`${t('resolver.open')} *`" :icon="MANAGE_ICONS.RICERCA"
              outlined @click="resolverVisible = true" />
          </div>
        </template>

        <!-- === Sezione Auth (solo creazione) === -->
        <template v-if="!isEdit">
          <h4>{{ t('amministrazione.section_accesso') }}</h4>
          <AuthUserForm
            :form="auth.form"
            :show-password="false"
          />
          <small class="app-field-hint">{{ t('amministrazione.password_da_invito') }}</small>
        </template>

        <!-- === Sezione Dati anagrafici + Collocazione === -->
        <h4 v-if="!isEdit">{{ t('amministrazione.section_collocazione') }}</h4>
        <div class="form-grid">
          <!-- Username (solo modifica, sola lettura) -->
          <div v-if="isEdit" class="form-field">
            <label>{{ t('common.username') }}</label>
            <InputText :model-value="form.username" disabled />
          </div>

          <!-- Cognome + Nome su stessa riga (solo modifica) -->
          <template v-if="isEdit">
            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('common.cognome') }}</label>
                <InputText v-model="form.cognome"
                  @blur="form.cognome = capitalizeWords(form.cognome)" />
              </div>
              <div class="form-field">
                <label>{{ t('common.nome') }}</label>
                <InputText v-model="form.nome"
                  @blur="form.nome = capitalizeWords(form.nome)" />
              </div>
            </div>
            <div class="form-field">
              <label>{{ t('common.email') }} *</label>
              <InputText v-model="form.email"
                :invalid="emailEditInvalid"
                @blur="validateEditEmail"
                @input="clearEditEmailInvalid" />
              <small v-if="emailEditInvalid" class="app-field-error">
                {{ t('validation.email_format') }}
              </small>
            </div>
          </template>

          <!-- Stato operatore (solo modifica): 2 toggle indipendenti -->
          <template v-if="isEdit">
            <div class="form-field">
              <div class="operatore-toggle-row">
                <ToggleSwitch v-model="form.is_super_admin" input-id="tg-super-admin"
                  :disabled="demoteBloccato" />
                <label for="tg-super-admin" class="operatore-toggle-label">
                  <span>{{ t('amministrazione.is_super_admin.label') }}</span>
                  <small class="operatore-toggle-help">{{ t('amministrazione.is_super_admin.help') }}</small>
                </label>
              </div>
              <small v-if="demoteReason" class="app-field-hint">{{ demoteReason }}</small>
            </div>
            <div class="form-field">
              <div class="operatore-toggle-row">
                <ToggleSwitch v-model="form.attivo" input-id="tg-attivo"
                  :disabled="disableBloccato || vesteSpenta"
                  :invalid="campiErrati.includes('attivo')"
                />
                <label for="tg-attivo" class="operatore-toggle-label">
                  <span>{{ t('amministrazione.accesso_attivo.label') }}</span>
                  <small class="operatore-toggle-help">{{ t('amministrazione.accesso_attivo.help') }}</small>
                </label>
              </div>
              <small v-if="disableReason" class="app-field-hint">{{ disableReason }}</small>
              <small v-else-if="vesteSpenta" class="app-field-hint">{{ t('amministrazione.accesso_attivo.da_invito') }}</small>
            </div>
          </template>

          <!-- Creazione: toggle SUPER_ADMIN (attivo implicito=true) -->
          <div v-if="!isEdit" class="form-field">
            <div class="operatore-toggle-row">
              <ToggleSwitch v-model="form.is_super_admin" input-id="tg-super-admin-new" />
              <label for="tg-super-admin-new" class="operatore-toggle-label">
                <span>{{ t('amministrazione.is_super_admin.label') }}</span>
                <small class="operatore-toggle-help">{{ t('amministrazione.is_super_admin.help') }}</small>
              </label>
            </div>
          </div>

          <!-- Qualifica: solo creazione -->
          <div v-if="!isEdit" class="form-field">
            <label>{{ t('amministrazione.field_qualifica') }} *</label>
            <LookupSelect v-model="form.qualifica_id"
              rel="config.qualifiche"
              :placeholder="t('amministrazione.select_qualifica')" />
          </div>

          <div class="form-field">
            <label>{{ t('amministrazione.field_reparto') }}</label>
            <Select v-model="form.unita_organizzativa_id"
              :options="unitaOrg.items.value"
              :loading="unitaOrg.loading.value"
              option-label="descrizione" option-value="id"
              :placeholder="t('amministrazione.select_reparto')" />
          </div>

          <!-- Scope emittenti fiscali (solo modifica): GLOBAL/SINGLE. `MULTI`
               non e' in allowed_scope_modes (architetturalmente chiuso). -->
          <div v-if="isEdit" class="form-field">
            <label>{{ t('amministrazione.emittenti_scope_title') }}</label>
            <div
              class="scope-radio-group"
              v-tooltip.bottom="!canChangeScope ? changeScopeReason : null"
            >
              <div v-for="opt in scopeModeOptions" :key="opt.value" class="scope-radio-row">
                <RadioButton
                  v-model="scopeMode"
                  :value="opt.value"
                  :input-id="'scope-mode-' + opt.value"
                  :disabled="isReadonly || !canChangeScope || opt.disabled"
                />
                <label :for="'scope-mode-' + opt.value" class="scope-radio-label">{{ opt.label }}</label>
              </div>
            </div>
            <Select
              v-if="scopeMode === 'SINGLE'"
              v-model="scopeEmittenteId"
              :options="emittentiFiscali.items.value"
              :loading="emittentiFiscali.loading.value"
              option-label="ragione_sociale"
              option-value="id"
              :placeholder="t('amministrazione.select_emittenti')"
              show-clear
              :disabled="isReadonly || !canChangeScope"
            />
            <small class="app-field-hint">{{ t('amministrazione.emittenti_scope_hint') }}</small>
          </div>

          <!-- Validita' e ultimo accesso (solo modifica). Si modifica solo la
               fine del rapporto: l'inizio e l'ultimo accesso sono informativi. -->
          <template v-if="isEdit">
            <div class="form-field">
              <label>{{ t('amministrazione.field_ultimo_accesso') }}</label>
              <InputText :model-value="form.last_login ? displayTimestamp(form.last_login) : t('amministrazione.mai_entrato')" disabled />
            </div>
            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('amministrazione.field_valido_dal') }}</label>
                <InputText :model-value="form.valido_dal ? displayDate(form.valido_dal) : '—'" disabled />
              </div>
              <div class="form-field">
                <label for="dp-valido-al">{{ t('amministrazione.field_valido_al') }}</label>
                <DatePicker v-model="form.valido_al" input-id="dp-valido-al"
                  :date-format="DATE_FORMAT"
                  :min-date="validoAlMin"
                  :placeholder="t('amministrazione.valido_al_illimitato')"
                  show-icon
                  show-button-bar
                  :disabled="validoAlBloccato"
                  :invalid="campiErrati.includes('valido_al')" />
              </div>
            </div>
            <small v-if="validoAlReason" class="app-field-hint">{{ validoAlReason }}</small>
            <small v-else class="app-field-hint">{{ t('amministrazione.valido_al_hint') }}</small>
            <!-- Le azioni della CREDENZIALE — blocco e secondo fattore — valgono
                 per tutte le vesti della persona (A-5: le stesse del tab «Altri
                 accessi»). Immediate, non passano dal Salva. -->
            <CredenzialeAzioni :auth-user-id="props.authUserId" :readonly="isReadonly" />
          </template>
        </div>

        <!-- Invito operatore (solo modifica, quando il DB lo ammette) -->
        <small v-if="inviteReason" class="app-field-hint">{{ inviteReason }}</small>
        <div v-if="canInvite">
          <Button
            :label="hasBeenInvited ? t('amministrazione.reinvia_invito') : t('amministrazione.invita_operatore')"
            :icon="MANAGE_ICONS.INVITA"
            :loading="invitaLoading"
            outlined size="small"
            @click="onInvita" />
        </div>
      </TabPanel>

      <!-- Tab Permessi: solo modifica -->
      <TabPanel v-if="isEdit" value="permessi">
        <OperatorePermessiTab ref="permessiTab" :auth-user-id="props.authUserId" :readonly="isReadonly" :visible="props.visible" />
      </TabPanel>
      </TabPanels>
    </Tabs>

    <!-- Il consenso al riuso della credenziale (F-4): la domanda del DB, e cio'
         che l'admin sta per collegare. Conferma = si dichiara l'id letto. -->
    <AppDialog
      v-if="!isEdit"
      :visible="dialogRiusoVisibile"
      :header="t('amministrazione.riuso_titolo')"
      width="md"
      :loading="creazione.loading.value"
      :save-label="t('amministrazione.riuso_conferma')"
      @save="onConfermaRiuso"
      @cancel="onAnnullaRiuso"
    >
      <template v-if="credenzialeDaConfermare">
        <!-- La frase del DB: nomina gia' email e username, e' multilingua. -->
        <Message severity="warn" :closable="false">{{ richiestaConferma?.messaggio }}</Message>
        <div class="form-field mt-1">
          <label>{{ t('amministrazione.riuso_username') }}</label>
          <strong>{{ credenzialeDaConfermare.username }}</strong>
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.riuso_vesti') }}</label>
          <ul v-if="credenzialeDaConfermare.vesti.length" class="riuso-vesti">
            <li v-for="(veste, i) in credenzialeDaConfermare.vesti" :key="i">
              {{ etichettaRuoloApplicativo(t, te, veste.ruolo_applicativo) }}<template v-if="veste.soggetto"> — {{ veste.soggetto }}</template>
              <span class="app-text-muted">
                ({{ veste.attivo ? t('amministrazione.riuso_veste_attiva') : t('amministrazione.riuso_veste_spenta') }})
              </span>
            </li>
          </ul>
          <span v-else class="app-text-muted">{{ t('amministrazione.riuso_nessuna_veste') }}</span>
        </div>
        <small class="app-field-hint">{{ t('amministrazione.riuso_spiegazione') }}</small>
      </template>
    </AppDialog>

    <!-- Sotto-drawer: SoggettoResolver (solo creazione) -->
    <SoggettoResolver
      v-if="!isEdit"
      :visible="resolverVisible"
      :tipo-ruolo-codice="TIPO_RUOLO.RISORSA_UMANA"
      @update:visible="v => resolverVisible = v"
      @soggetto-selezionato="onSoggettoSelezionato"
      @soggetto-creato="onSoggettoCreato"
      @annullato="resolverVisible = false"
    />
  </AppDrawer>
</template>

<style scoped>
/* Toggle stato operatore: switch + label con riga helper */
.operatore-toggle-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.operatore-toggle-label {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  cursor: pointer;
}
.scope-radio-group {
  display: flex;
  gap: 1.25rem;
  flex-wrap: wrap;
}
.scope-radio-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.scope-radio-label {
  cursor: pointer;
}
.riuso-vesti {
  margin: 0;
  padding-left: 1.2rem;
}
.operatore-toggle-help {
  font-size: 0.78rem;
  color: var(--app-text-muted);
}
</style>

<!-- Stili .form-grid e .form-field definiti in main.css -->
