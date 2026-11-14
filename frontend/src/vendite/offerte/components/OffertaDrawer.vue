<script setup>
// Scopo: Drawer offerta commerciale — testata + sezione utility inline +
//        sub-drawer eccezioni + tab revisioni. Azioni di stato + speciali
//        (push_contratto, genera_ordine) interamente data-driven da
//        `available_actions` (script.fn_available_actions_offerta), come per
//        contratti/preventivi.
//
// Pattern speculare a ContrattoDrawer (utility 1:1 inline in testata,
// listino + variazione globale PERCENTUALE, validita range). Drawer 3 tab
// (testata, eccezioni, revisioni) come da piano BE+FE rev. f §FE-3.
import { computed, nextTick, provide, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import AppDialog from '../../../core/components/AppDialog.vue'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tab from 'primevue/tab'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tag from 'primevue/tag'

import BillingAccountLookup from '../../../core/components/BillingAccountLookup.vue'
import { ripristinaBillingAccount } from '../../../core/utils/ripristinaLookup'
import { useCambioClienteDocumento } from '../../_shared/cliente/useCambioClienteDocumento'
import DrawerActionsBar from '../../../core/components/DrawerActionsBar.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import DocumentoIndirizziSection from '../../_shared/indirizzi/DocumentoIndirizziSection.vue'
import DocumentoCollegamentiBar from '../../_shared/lineage/DocumentoCollegamentiBar.vue'
import AppDrawer from '../../../core/components/AppDrawer.vue'
import EmittenteFiscaleField from '../../../core/components/EmittenteFiscaleField.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useContatoreNote } from '../../../core/composables/useContatoreNote'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useForzaturaConfermata } from '../../../core/composables/useForzaturaConfermata'
import { mapAvailableActionsToDrawerActions } from '../../../core/composables/useDrawerActions'
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerFormPreserve } from '../../../core/composables/useDrawerFormPreserve'
import { useDrawerDetailLoad } from '../../../core/composables/useDrawerDetailLoad'
import { useEmittenteFiscaleField } from '../../../core/composables/useEmittenteFiscaleField'
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { useFetchVersion } from '../../../core/composables/useFetchVersion'
import { useNotify } from '../../../core/composables/useNotify'
import { useUtilityDefaultId } from '../../../core/composables/useUtilityDefaultId'
import { useFooterDocumento } from '../../../core/composables/useFooterDocumento'
import { useTestataDocumento } from '../../../core/composables/useTestataDocumento'
import {
  READONLY_KEY,
  useInjectReadonly,
} from '../../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS, TIPO_RUOLO, DATE_FORMAT } from '../../../core/constants'
import { NAV_ICONS } from '../../../core/navigation'
import { extractApiError, extractApiErrorCode } from '../../../core/utils/apiError'
import { displayDate, parseIsoDate, toDateString, oggiAziendaleString } from '../../../core/utils/date'
import { statoOffertaSeverity } from '../../../core/utils/severity'
import { getOffertaFormDefaults } from '../../api/formDefaults'
import { useBaFormDefaults } from '../../_shared/baDefaults/useBaFormDefaults'
import {
  applicaFornituraDaDefaults, schedaDaForm, schedaDaFornitura, schedaVuota,
} from '../../_shared/fornitura/schedaFornitura'
import ListinoDocumentoSelect from '../../components/ListinoDocumentoSelect.vue'
import TipoVariazioneSelect from '../../components/TipoVariazioneSelect.vue'
import CampiCanoneTestata from '../../_shared/canoni/CampiCanoneTestata.vue'
import {
  campiCanoneDaDettaglio, campiCanoneDaForm, campiCanoneVuoti,
} from '../../_shared/canoni/campiCanone'
import {
  CAMPI_FORM_TESTATA_OFFERTA,
  STATO_OFFERTA,
} from '../constants'
import { useOfferteStore } from '../stores/offerte'
import { useOffertaRevisioniStore } from '../stores/offertaRevisioni'
import RevisioniTab from '../../_shared/revisioni/RevisioniTab.vue'
import OffertaRigheDrawer from './OffertaRigheDrawer.vue'
import VenditeNoteDrawer from '../../_shared/note/VenditeNoteDrawer.vue'
import OffertaEmissioneDialog from './dialogs/OffertaEmissioneDialog.vue'
import OffertaEsitoDialog from './dialogs/OffertaEsitoDialog.vue'
import OffertaPushDialog from './dialogs/OffertaPushDialog.vue'
import OffertaSuccessioneDialog from './dialogs/OffertaSuccessioneDialog.vue'
import DocumentoAnnulloLegamiDialog from '../../_shared/annullo/DocumentoAnnulloLegamiDialog.vue'
// Riuso read-only del drawer contratti per ispezionare il contratto sovrapposto
// dal dialog di successione (righe comprese). Read-only forzato via prop.
import ContrattoDrawer from '../../components/ContrattoDrawer.vue'
import EntityPdfButton from '../../../documenti/components/EntityPdfButton.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'

const { t, te } = useI18n()
const store = useOfferteStore()
const { execute, loading, campiErrati } = useApiHandler()
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
// Modifiche non salvate: fotografia a form popolato (apertura, ricarica,
// salvataggio), chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { preserva, fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })
// Tab "Testata | Revisioni". Il tab attivo torna a "Testata" a ogni apertura
// (`loadOrReset`). La catena delle revisioni e' la lista a catalogo
// `vendite.offerta_revisioni`, montata da `RevisioniTab` (BB condiviso con
// PreventiviDrawer, che dal 2026-09-27 ritira `useRevisioniTab`): store SUO,
// padre = offerta + emittente, ricarica al cambio offerta e reset a drawer
// chiuso — lo fa `useDrawerTabLista`, col guard anti-race della lista.
const activeTab = ref('testata')
const revisioniStore = useOffertaRevisioniStore()

// State machine data-driven dal BE (Step 9b 2026-05-26:
// script.fn_available_actions_offerta + arricchimento `get_offerta`).
// Le capability `canEdit`, `availableActions`, `isLocked(field)` arrivano
// dal blob `detail.capabilities`. Il drawer NON ricalcola stato lato
// client: legge la verita' BE. Pattern allineato a Contratto/Preventivo.
const stato = computed(() => detail.value?.stato_codice_interno || null)
// `useEntityCapabilities` espone anche `isLocked(field)` per granularita'
// campo-per-campo da `non_editable_fields`. Oggi non lo usiamo (il BE
// blocca tutta la testata fuori BOZZA, equivalente a `!canEdit`), ma resta
// pronto per future estensioni (es. "modificabile solo meta in EMESSA").
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })

const capabilities = caps.capabilities
const availableActions = caps.availableActions

// Push contratto / genera ordine: fuori da un'offerta trasformabile le due
// azioni NON arrivano in `available_actions` (non accettata, o gia' trasformata),
// quindi da sole spariscono senza spiegare perche'. La capability espone anche il
// motivo: banner informativo, mirror di PreventiviDrawer/OrdiniDrawer.
// ⭐ Dal 2026-10-21 (brief-db-offerta-emissione-ed-erogazione H-R2, I-D2) da
//    ACCETTATA senza documenti vivi le due azioni arrivano PROPOSTE anche spente,
//    col motivo delle righe (`RIGA_NON_AMMESSA`): lo dice il tooltip del
//    pulsante, il canale unico del perche' di un pulsante spento. Il banner
//    parla solo per le azioni che non ci sono: ripetere qui il motivo lo
//    mostrerebbe due volte, e senza i valori della frase (`{0}`, `{1}`).
// ⚠️ Un motivo si mostra UNA volta: le due azioni sono mutuamente esclusive con
//    la stessa abilitazione (fn_available_actions_offerta), quindi i due motivi
//    coincidono quasi sempre («Disponibile dopo l'accettazione» compariva due
//    volte, 2026-10-07) — e due `:key` uguali nel `v-for`.
const pushReasons = computed(() => {
  const proposte = new Set((availableActions.value || []).map((a) => a.key))
  const motivi = [
    { azione: 'push_contratto', ok: caps.flag('can_push_contratto'), key: capabilities.value.can_push_contratto_reason_key },
    { azione: 'genera_ordine', ok: caps.flag('can_genera_ordine'), key: capabilities.value.can_genera_ordine_reason_key },
  ].filter((r) => !r.ok && !proposte.has(r.azione) && r.key && te(r.key))
  return motivi.filter((r, i) => motivi.findIndex((m) => m.key === r.key) === i)
})

// isReadonly cumulativo: OR tra permessi area e workflow lock (offerta fuori
// BOZZA). In create l'offerta nasce in BOZZA, l'utente puo' compilare.
// ⚠️ Fino al 2026-10-10 il lock era `!canEditTestata`. Da quel giorno
//    `can_edit_testata` dice «in questo stato almeno una colonna della testata
//    si cambia» (brief-db-testata-dopo-emissione, fase 2): vero anche su
//    EMESSA/ACCETTATA per le note, che il form non porta. Leggerlo qui
//    avrebbe sbloccato tutto il drawer — form, utility, indirizzi — su
//    un'offerta emessa. Il lock di corpo resta quindi sullo stato, come nei
//    cinque drawer gemelli (righe, utility, indirizzi); i campi della testata
//    aperti fuori bozza (R-FE-3 del brief) si accendono uno per uno da
//    `non_editable_fields` (`useTestataDocumento`, sotto), e il blocco della
//    testata esce dal corpo protetto quando ne resta aperto qualcuno.
const isWorkflowLocked = computed(
  () => isEdit.value && detail.value !== null && stato.value !== STATO_OFFERTA.BOZZA,
)
const isReadonly = computed(
  () => parentReadonly.value || isWorkflowLocked.value,
)
provide(READONLY_KEY, isReadonly)
// La testata dopo la bozza: quali campi del form si cambiano, dalla capability
// (brief-db-testata-dopo-emissione, R-FE-3).
const testata = useTestataDocumento({
  caps,
  campi: CAMPI_FORM_TESTATA_OFFERTA,
  readonlyPuro: () => parentReadonly.value,
  // Il documento esiste: in EDIT anche prima che arrivi il dettaglio, cosi'
  // la capability ancora vuota tiene il form fermo (fail-closed).
  presente: () => isEdit.value || detail.value !== null,
  corpoProtetto: () => isReadonly.value,
})

// Stato terminale: il banner `warn` «sola lettura» contro quello `info` degli
// stati intermedi (EMESSA/ACCETTATA), dove `can_edit_testata` e' false lo
// stesso. Lo dice la capability (`stato_terminale`, la colonna `terminale` del
// vocabolario: brief-db-stati-documento-dal-vocabolario §6.7), non un elenco
// di codici copiato qui. Assente (capability vuota) = non terminale.
const isStatoTerminale = computed(() => caps.flag('stato_terminale'))

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
// Il pulsante «Gestisci note» standard, col numero delle note del documento
// (BB `useContatoreNote`: dal dettaglio, poi dal sotto-drawer dopo un salvataggio).
const contatoreNote = useContatoreNote(() => detail.value)
const emissioneDialogVisible = ref(false)
const esitoDialogVisible = ref(false)
const esitoDialogModalita = ref(STATO_OFFERTA.ACCETTATA) // ACCETTATA | RIFIUTATA | ANNULLATA
// L'obbligo della motivazione dalla riga del passaggio (`requires_motivazione`).
const esitoDialogMotivazioneObbligatoria = ref(false)
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
// chiudere il drawer). Le revisioni hanno il loro guard, dentro lo store-lista
// di `RevisioniTab`.
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
    validita_dal: oggiAziendaleString(),
    validita_al: null,
    // I canoni (F-2, F-7): vuoti in CREATE = il default del DB (anticipati,
    // da gennaio), che il dettaglio poi mostra. Il form non ricopia il default.
    ...campiCanoneVuoti(),
    // Scheda di fornitura inline (BB `schedaFornitura`, come il contratto)
    ...schedaVuota(),
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
  activeTab.value = 'testata'
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
    listino_id: d.listino_id,
    listino_versione_id: d.listino_versione_id,
    valuta_id: d.valuta_id,
    tipo_variazione_globale: d.tipo_variazione_globale,
    valore_variazione_globale: d.valore_variazione_globale,
    validita_dal: d.validita_dal,
    validita_al: d.validita_al,
    ...campiCanoneDaDettaglio(d),
    ...schedaDaFornitura(d.utility),
  }
  if (!stessoCliente) ripristinaBillingAccount(form.value, d.billing_account_id)
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

// ⛔ In modifica la utility dell'offerta non si cambia (E-3 di Tid, lock del DB
//    «ferma sempre»): il cliente si cambia DENTRO la stessa utility, che filtra
//    il lookup. Fino al 2026-10-19 qui si riscriveva sempre: pulito il cliente,
//    il filtro passava alla utility di default e si poteva scegliere un cliente
//    che il backend rifiuta. Come il ContrattoDrawer.
function onBaSelected(item) {
  if (!item) {
    form.value.billing_account_id = null
    form.value.billing_account_obj = null
    form.value.istanza_utility_id = null
    // Ripristina il default utility quando si pulisce il BA: l'operatore
    // mantiene il filtro lookup BA sull'utility tipica del proprio EF
    // invece di tornare a "vedo tutti i BA". Coerente col `defaultForm()`
    // che pre-popola `utility_id` da `utilityDefaultId.value` in CREATE.
    if (!isEdit.value) form.value.utility_id = utilityDefaultId.value
    return
  }
  form.value.billing_account_id = item.id
  form.value.billing_account_obj = item
  form.value.istanza_utility_id = item.istanza_utility_id || null
  if (!isEdit.value) form.value.utility_id = item.utility_id || null
}

// Auto-fill valuta dal form-defaults BE (BB resolve_valuta_default), al cambio
// BA in CREATE: la valuta del BA vince (regola di coerenza dominio). Watcher
// condiviso `useBaFormDefaults` con guard latest-wins inclusa.
// ⭐ In creazione la scheda di fornitura segue il cliente scelto: quella che
//    l'anagrafica gli da', che l'operatore vede e corregge (R-FE-3 di
//    brief-db-indirizzi-documento-seguono-il-cliente, D-7 di Tid).
const { inCorso: defaultsClienteInCorso } = useBaFormDefaults({
  form, isEdit, fetchDefaults: getOffertaFormDefaults, apply: applicaFornituraDaDefaults,
})

// Carica/resetta su apertura/chiusura/cambio-id.
// Watch composito [visible, offertaId]: scatena ricaricamento sia quando il
// drawer si apre, sia quando il padre cambia offertaId con drawer ancora
// aperto (rev N+1 dopo crea_revisione e' lo scenario tipico). Senza il
// secondo elemento, editRow al volo non innescherebbe il fetch del nuovo
// detail e il drawer mostrerebbe la rev vecchia con i bottoni della nuova.
async function loadOrReset() {
  if (!props.visible) {
    fv.invalidate()
    activeTab.value = 'testata'
    // ⚠️ A mano, e non da `RevisioniTab`: il Drawer smonta il contenuto nello
    //    stesso giro in cui si chiude, e il `documentoId` null non arriva mai
    //    al tab. Senza, il contatore «Revisioni (N)» della prossima apertura
    //    parte dal documento precedente.
    revisioniStore.reset()
    return
  }
  const t = fv.tag()

  // Reset tab attivo sempre, su qualunque apertura (EDIT e CREATE): senza
  // questo, riaprendo il drawer su un'altra offerta il tab restava quello
  // dell'apertura precedente (es. chiudo su "Revisioni", riapro su una nuova
  // offerta → si vede "Revisioni" invece di "Testata"). `resetForm` lo fa
  // solo nel ramo CREATE, quindi qui copre anche EDIT/cambio-offertaId.
  // (Le revisioni le rilegge `RevisioniTab` al cambio di offerta: il BB
  // riparte da capo a ogni padre nuovo.)
  activeTab.value = 'testata'

  if (isEdit.value && props.offertaId) {
    const d = await loadDetailOrClose(() => store.fetchDetail(props.offertaId))
    if (!fv.isCurrent(t)) return
    if (d == null) return  // dettaglio non accessibile → drawer già chiuso
    detail.value = d
    populateFromDetail(d)
    fissa()
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
    fissa()
  }
}
watch(() => [props.visible, props.offertaId], loadOrReset)

// Validazione FE create: campi obbligatori secondo whitelist BE.
// Finche' arrivano i dati del cliente (BB `useBaFormDefaults`) il Salva
// aspetta: partirebbe un form senza quei dati, presi per scelte dell'operatore.
const canSave = computed(() => {
  if (!testata.modificabile.value) return false
  if (defaultsClienteInCorso.value) return false
  const f = form.value
  const hasTipo = !!f.tipo_variazione_globale
  const hasValore = f.valore_variazione_globale != null && f.valore_variazione_globale !== ''
  if (hasTipo !== hasValore) return false
  // In bozza il cliente si cambia ma non si toglie (come il contratto): col BA
  // svuotato il backend rifiuterebbe su `istanza_utility_id`, un campo che il
  // form non mostra.
  if (isEdit.value) return !!f.billing_account_id
  return !!(f.emittente_fiscale_id
    && f.billing_account_id
    && f.istanza_utility_id
    && f.utility_id
    && f.listino_id
    && f.validita_dal)
})

function buildPayload() {
  const f = form.value
  // Guard difensivo: in EDIT solo se un campo della testata si cambia ancora
  // (`useTestataDocumento`). Il footer Salva segue la stessa regola, quindi
  // questo branch non dovrebbe essere mai raggiunto in pratica; ritorniamo
  // dict vuoto per safety, evitando PATCH inutili.
  if (isEdit.value && !testata.modificabile.value) return {}
  return {
    // Emittente e utility SOLO in CREATE: si scelgono alla nascita e non si
    // cambiano, nemmeno in bozza (lock del DB «ferma sempre»); in EDIT il BE
    // le rifiuta sul campo (R-BE-9, brief-db-indirizzi-documento-seguono-il-
    // cliente §8.7.3). Come il ContrattoDrawer.
    ...(isEdit.value ? {} : {
      emittente_fiscale_id: f.emittente_fiscale_id,
      utility_id: f.utility_id,
    }),
    billing_account_id: f.billing_account_id,
    istanza_utility_id: f.istanza_utility_id,
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
    // NOT NULL a DB col default: si mandano solo valorizzati, mai `null`.
    ...campiCanoneDaForm(f),
  }
}

// Il sotto-oggetto `utility` della richiesta (BB `schedaDaForm`): null finche'
// il cliente non e' scelto, perche' la scheda e' della sua coppia (istanza,
// utility), che il backend prende dalla testata.
function buildUtilityInline() {
  const f = form.value
  if (!f.istanza_utility_id || !f.utility_id) return null
  return schedaDaForm(f)
}

async function handleSave() {
  // CREATE e UPDATE seguono lo stesso pattern atomico: testata + utility
  // 1:1 in un singolo round-trip con `utility: {...}` inline. Il BE fa
  // l'upsert dentro la stessa transaction.atomic() (mirror del pattern
  // ContrattoDrawer). Niente piu' fallimento parziale ne' .catch() silenziosi.
  const payload = buildPayload()
  const utilityInline = buildUtilityInline()
  // I dati della fornitura viaggiano solo se si cambiano ancora
  // (`can_edit_utility` della capability: il lock dei satelliti del DB).
  // Un cambio di cliente qui non arriva: si e' gia' salvato alla scelta, con la
  // conferma (BB `useCambioClienteDocumento`, 2026-10-19), e la scheda del form
  // e' gia' quella del cliente nuovo.
  if (utilityInline && (!isEdit.value || caps.flag('can_edit_utility'))) {
    payload.utility = utilityInline
  }

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
    // Salvato: la fotografia e' il form com'e' ora, PRIMA della ricarica —
    // o `preserva` di refreshDetail prenderebbe i valori appena salvati per
    // «non salvati» e li rimetterebbe sopra quelli del server. In creazione
    // il parent riapre/chiude.
    fissa()
    if (!isCreate) await refreshDetail()
    emit('saved', result)
  }
}

async function refreshDetail() {
  if (!props.offertaId) return
  // `preserva`: salvare una riga o cambiare stato ricarica la testata, e senza
  // la modifica di testata non ancora salvata tornava com'era, in silenzio
  // (stesso difetto gia' corretto su ordini/DDT/preventivi, 2026-09-26).
  const applica = preserva()
  // Guard `fv` (useFetchVersion): protegge contro l'apply di un detail stantio
  // se l'operatore chiude/cambia offerta mentre il fetch e' in volo. Stesso
  // pattern del watcher loadOrReset.
  const t = fv.tag()
  const d = await store.fetchDetail(props.offertaId)
  if (!fv.isCurrent(t)) return
  detail.value = d
  populateFromDetail(d)
  applica()
  // I chip dei collegamenti si riallineano da soli su questo `detail` nuovo
  // (`:versione` della barra): push contratto e genera ordine creano archi e
  // passano TUTTI da qui — e cosi' anche le azioni future.
}

// ⭐ Il cambio di cliente in modifica si salva subito, con conferma (BB
//    `useCambioClienteDocumento`, decisione di Tid 2026-10-19): il DB rifa'
//    indirizzi e scheda, e pannello e «Indirizzi» mostrano subito quelli del
//    cliente nuovo. La scheda non salvata del cliente vecchio si scarta.
useCambioClienteDocumento({
  form,
  detail,
  attivo: () => isEdit.value && detail.value != null && !testata.bloccato('billing_account_id'),
  salva: (corpo) => execute(
    () => store.update(props.offertaId, corpo),
    { successMessage: t('vendite.offerte.salvata') },
  ),
  ricarica: refreshDetail,
  scartaDipendenti: () => Object.assign(form.value, schedaDaFornitura(detail.value?.utility)),
  messaggio: 'vendite.cliente.cambio_messaggio_con_fornitura',
})

// Reload revisioni dopo un'azione che cambia lo stato di una riga della
// catena (emissione, esito, annullo): solo se il tab e' gia' agganciato a
// QUESTA offerta (il perche' sta su `rileggiSeAgganciato`).
function reloadRevisioni() {
  if (!props.offertaId) return
  return revisioniStore.rileggiSeAgganciato(props.offertaId)
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
//   - genera_ordine         -> confirmAction + store.generaOrdine (conversione
//     §7.4; dal 2026-10-21 la genera il verbo DB `fn_genera_ordine_da_offerta`)
// Un'azione spenta (`enabled:false`, es. «Genera ordine» con una riga che non
// va in un ordine) arriva come pulsante disabilitato col tooltip del motivo
// (`mapAvailableActionsToDrawerActions`): il click non arriva qui.
// `requires_motivazione` arriva dalla fn DB (la riga del passaggio) e va al
// dialog esito, che segna il campo obbligatorio; a farla rispettare e' il verbo
// DB (E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA, brief-modello-documento-vendita §13).
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
      esitoDialogMotivazioneObbligatoria.value = action.requires_motivazione === true
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
    case 'genera_ordine':
      // Conversione §7.4: la fn DB non ritorna l'azione se un ordine e' gia'
      // nato da questa offerta (idempotenza 1:1). requires_confirm=true →
      // confermiamo prima di generare; la race concorrente la ferma il verbo
      // DB (offerta FOR UPDATE, E_ORD_OFFERTA_GIA_CONVERTITA).
      confirmAction({
        header: t('vendite.offerte.genera_ordine_titolo'),
        message: t('vendite.offerte.genera_ordine_messaggio'),
        acceptLabel: t('vendite.offerte.genera_ordine_conferma'),
        onAccept: onGeneraOrdine,
      })
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

// ⭐ L'annullo e' un gesto CONFERMABILE (O-4, brief-modello-documento-vendita
//    §13): annullare l'ultima revisione viva fa tornare emessa la precedente,
//    e il DB lo rifiuta (`confirm_and_retry`) finche' chi conferma non dichiara
//    quanti legami ha visto; la domanda la porta a video
//    `DocumentoAnnulloLegamiDialog`. La motivazione resta nella chiamata da
//    ripetere. Accetta e rifiuta restano su `execute`.
const annullo = useForzaturaConfermata()
const { richiestaConferma: domandaAnnullo } = annullo

async function dopoEsito() {
  esitoDialogVisible.value = false
  await refreshDetail()
  await reloadRevisioni()
}

async function handleEsitoConferma({ esito, motivazione }) {
  const opts = { successMessage: t('vendite.offerte.esito_salvato') }
  if (esito === STATO_OFFERTA.ANNULLATA) {
    // Primo tentativo SEMPRE senza dichiarazione.
    const result = await annullo.esegui(
      (dichiarazione) => store.annulla(props.offertaId, { motivazione, dichiarazione }),
      opts,
    )
    if (result !== null) await dopoEsito()
    // La domanda del DB: la finestra dei legami prende il posto del dialog.
    else if (domandaAnnullo.value !== null) esitoDialogVisible.value = false
    return
  }
  const result = await execute(
    () => store.registraEsito(props.offertaId, { esito, motivazione }), opts,
  )
  if (result !== null) await dopoEsito()
}

// Scopo: l'operatore ha visto i legami e conferma l'annullo: si ripete la
//        chiamata DICHIARANDO quanti erano.
async function onConfermaAnnullo(dichiarazione) {
  const result = await annullo.conferma(dichiarazione)
  if (result !== null) await dopoEsito()
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

// Conversione upstream (§7.4): genera un ordine DRAFT dall'offerta ACCETTATA
// (BE espande listino+eccezioni via fn DB, preserva i prezzi negoziati). Chiamata
// store diretta (azione gia'-unwrappata, memoria feedback_useapihandler_solo_axios)
// con gestione errore manuale; lo store emette l'evento tab ordini.
async function onGeneraOrdine() {
  try {
    const result = await store.generaOrdine(props.offertaId)
    notify.success(
      t('vendite.offerte.ordine_generato', { numero: result.numero }),
    )
    // Ricarica le capability: ora `can_genera_ordine` è false (ordine 1:1
    // generato) → l'azione sparisce dalla barra, come per push_contratto.
    await refreshDetail()
  } catch (err) {
    notify.error(extractApiError(err, t('vendite.offerte.errore_generico')))
  }
}

// Barra azioni del drawer: composizione di
//   1) Transizioni di stato + azioni speciali data-driven dal BE
//      (script.fn_available_actions_offerta, mapped 1:1 in azioni
//      `kind:'state'` con label/icona/severity dal jsonb). Include
//      `genera_ordine` (conversione §7.4), che la fn propone da ACCETTATA
//      senza documenti vivi (spenta col motivo se una riga non va in un
//      ordine): il bottone sparisce a conversione avvenuta come per
//      `push_contratto`.
//   2) Manage action `manage-eccezioni` per il sub-drawer delle righe
//      (master-detail inline, `OffertaRigheDrawer`). Allineato al pattern
//      ContrattoDrawer: le righe vivono in un sub-drawer dedicato, non in una
//      tab del drawer principale (UX UI 2026-05-26). Il badge conta le
//      eccezioni scritte, come il contratto conta le sue righe.
//   3) Manage action `manage-note` per il sub-drawer note partizionate.
const drawerActions = computed(() => {
  if (!isEdit.value || !detail.value) return []
  const eccCount = detail.value.eccezioni?.length ?? 0
  return [
    // Read-only puro (permesso LETTURA / pannello split): niente azioni di
    // stato (emetti/accetta/rifiuta/push/genera_ordine/revisione). Restano i
    // pannelli gestisci-eccezioni/note (sub-drawer in sola lettura).
    ...mapAvailableActionsToDrawerActions({
      availableActions,
      t,
      te,
      onAction: onActionDispatch,
      readonly: parentReadonly.value,
    }),
    {
      key: 'manage-eccezioni',
      kind: 'manage',
      label: t('vendite.offerte.gestisci_righe'),
      icon: MANAGE_ICONS.RIGHE,
      badge: eccCount,
      command: () => { eccezioniDrawerVisible.value = true },
    },
    contatoreNote.azione({
      label: t('vendite.offerte.gestisci_note'),
      command: () => { noteDrawerVisible.value = true },
    }),
  ]
})

const onClose = useDrawerClose(emit, 'cancelled')
// Detail fuori scope (RLS) / inesistente → toast + chiusura, niente drawer vuoto.
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

// Il footer del drawer segue lo stato del documento (BB useFooterDocumento,
// D-11 di work-done/analisi-fe-chrome-drawer.md).
// «Modificabile» e' la testata (`useTestataDocumento`): Salva in CREATE, in
// BOZZA, e dopo solo se un campo del form resta aperto.
// Le eccezioni hanno un drawer loro: nessun form di riga qui.
const footerDrawer = useFooterDocumento({
  modificabile: () => testata.modificabile.value,
  presente: () => isEdit.value,
})
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="props.visible"
    :title="t('vendite.offerte.titolo_drawer')"
    :icon="NAV_ICONS.OFFERTE"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.COMPLEX"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer-readonly="testata.footerReadonly.value"
    :footer="footerDrawer"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >

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
          v-if="detail.is_scaduta"
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

      <DrawerActionsBar :actions="drawerActions" :info-key="capabilities.stato_info_key || ''">
        <template #suffix>
          <EntityPdfButton
            :sorgente-code="SORGENTE_CODES.OFFERTA_COMMERCIALE"
            :entity-id="props.offertaId"
            :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
            :pdf="capabilities.pdf"
            i18n-prefix="vendite.offerte.pdf"
            :dialog-title="detail.codice
              ? t('vendite.offerte.pdf.dialog_title', { codice: detail.codice })
              : ''"
          />
        </template>
      </DrawerActionsBar>

      <!-- Collegamenti diretti (pratica + origine + destinazioni di livello
           1): segnalazione a colpo d'occhio sotto i pulsanti — «Ordine»,
           «Contratto». Il grafo completo si apre dai chip in dialog.
           Solo in EDIT: in CREATE non c'e' ancora un documento. -->
      <DocumentoCollegamentiBar
        v-if="isEdit && offertaId"
        base-path="/vendite/offerte"
        :versione="detail"
        :doc-id="offertaId"
        @documento-chiuso="refreshDetail"
        :readonly="parentReadonly" />

      <!-- Motivo per cui push contratto / genera ordine non sono offerti
           (gia' generato, offerta non accettata): senza questo i pulsanti
           spariscono e basta. -->
      <Message
        v-for="r in pushReasons"
        :key="r.key"
        severity="info"
        :closable="false"
        class="mt-1"
      >
        {{ t(r.key) }}
      </Message>

      <Message
        v-if="isStatoTerminale"
        severity="warn"
        :closable="false"
        size="small"
      >
        {{ t('vendite.offerte.banner_stato_terminale', { stato: detail.stato_descrizione }) }}
      </Message>
      <Message
        v-else-if="isWorkflowLocked"
        severity="info"
        :closable="false"
        size="small"
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
          <span v-if="isEdit && revisioniStore.totalRecords">({{ revisioniStore.totalRecords }})</span>
        </Tab>
      </TabList>

      <TabPanels>
        <!-- ====================== TAB TESTATA ====================== -->
        <TabPanel value="testata">

          <!-- La testata: i campi si spengono uno per uno dalla capability
               (`useTestataDocumento`); quando ne resta aperto qualcuno fuori
               bozza il blocco esce dal corpo protetto. -->
          <div :class="{ 'app-escape': testata.sopraCorpoProtetto.value }">
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
                  :disabled="testata.bloccato('emittente_fiscale_id')"
                />
              </div>
              <div class="form-field">
                <label>{{ t('vendite.offerte.field_utility') }} <span v-if="!isEdit">*</span></label>
                <!-- Building block standard utility-per-ruolo-EF
                     (`UtilityPerRuoloSelect`). Le utility ammesse per il ruolo EF
                     e per il ruolo CLIENTE (`utilities_tipi_ruolo`). Pre-popolata dal `defaultForm()`
                     via `utilityDefaultId` (parametro `DEFAULT_UTILITY`,
                     codice_interno -> id locale). Quando l'operatore sceglie
                     il BA, `onBaSelected` sovrascrive con la utility canonical
                     del BA (coerenza FK garantita); se l'operatore pulisce
                     il BA, ripristiniamo il default per mantenere il filtro
                     lookup BA sull'utility tipica.
                     ⭐ Col cliente scelto la utility E' la sua (FK composta
                     `fk_offerte_commerciali_ba_coppia`): il campo si spegne e
                     la mostra, come nella bolla. Senza cliente filtra solo la
                     ricerca del cliente. Fino al 2026-10-13 restava aperta col
                     cliente fermo, e ogni cambio era rifiutato dal DB. -->
                <UtilityPerRuoloSelect
                  v-model="form.utility_id"
                  :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
                  :placeholder="t('vendite.offerte.field_utility')"
                  :disabled="testata.bloccato('billing_account_id') || form.billing_account_id != null"
                />
              </div>
            </div>

            <h4>{{ t('vendite.offerte.section_cliente') }}</h4>
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_billing_account') }} <span v-if="!isEdit">*</span></label>
              <!-- `utility-id` (da utilityDefaultId in CREATE) pre-filtra
                   il lookup BA sull'utility dell'operatore. Lookup ricco
                   (3 righe: ragione sociale + codice + PDP) — sta a tutta
                   larghezza in una propria riga.
                   ⭐ Il cliente si cambia anche in modifica, finche' l'offerta
                   e' in bozza (decisione di Tid del 2026-10-12, come nel
                   preventivo): fuori bozza lo ferma il lock di testata del DB
                   (`E_DOC_CLIENTE_FUORI_BOZZA`) e lo spegne la capability.
                   Indirizzi e scheda di fornitura seguono il cliente nuovo:
                   li rifa' il DB. -->
              <BillingAccountLookup
                :model-value="form.billing_account_obj"
                :utility-id="form.utility_id"
                :placeholder="t('vendite.offerte.select_billing_account')"
                :disabled="testata.bloccato('billing_account_id')"
                @update:model-value="onBaSelected"
              />
            </div>

            <h4>{{ t('vendite.offerte.section_listino') }}</h4>
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_listino') }} <span v-if="!isEdit">*</span></label>
              <!-- I listini della utility e dell'emittente del form, dal DB: la
                   tendina non propone cio' che il salvataggio rifiuterebbe (F-2).
                   Niente piu' filtro «almeno una versione ATTIVA»: un'offerta
                   senza versione in vigore la rifiuta l'emissione (A-D1). -->
              <ListinoDocumentoSelect
                v-model="form.listino_id"
                :utility-id="form.utility_id"
                :emittente-fiscale-id="form.emittente_fiscale_id"
                :record="detail"
                :placeholder="t('vendite.offerte.select_listino')"
                :disabled="testata.bloccato('listino_id')"
                @update:model-value="onListinoChange"
                :invalid="campiErrati.includes('listino_id')"
              />
              <small v-if="isEdit && detail?.listino_versione_codice"
                class="app-text-muted">
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
                  :disabled="testata.bloccato('tipo_variazione_globale')"
                />
              </div>
              <div class="form-field">
                <label>{{ t('vendite.offerte.field_valore_variazione') }}</label>
                <InputNumber
                  v-model="form.valore_variazione_globale"
                  :min-fraction-digits="0"
                  :max-fraction-digits="4"
                  show-buttons
                  :disabled="testata.bloccato('valore_variazione_globale')"
                  :suffix="form.tipo_variazione_globale === 'PERCENTUALE' ? ' %' : ''"
                  @update:model-value="onValoreVariazioneChange"
                  :invalid="campiErrati.includes('valore_variazione_globale')"
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
                  :placeholder="t('vendite.offerte.field_valuta')"
                  :disabled="testata.bloccato('valuta_id') || isEdit"
                  show-clear
                />
              </div>
            </div>

            <h4>{{ t('vendite.offerte.section_validita') }}</h4>
            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('vendite.offerte.field_validita_dal') }} <span v-if="!isEdit">*</span></label>
                <DatePicker
                  :model-value="parseIsoDate(form.validita_dal)"
                  :disabled="testata.bloccato('validita_dal')"
                  :date-format="DATE_FORMAT"
                  show-icon
                  @update:model-value="form.validita_dal = toIsoDate($event)"
                />
              </div>
              <div class="form-field">
                <label>{{ t('vendite.offerte.field_validita_al') }}</label>
                <DatePicker
                  :model-value="parseIsoDate(form.validita_al)"
                  :disabled="testata.bloccato('validita_al')"
                  :date-format="DATE_FORMAT"
                  show-icon
                  show-button-bar
                  @update:model-value="form.validita_al = toIsoDate($event)"
                />
              </div>
            </div>

            <!-- Come si addebitano i canoni (F-2, F-7): la riga a canone senza
                 generazione segue la testata; il passaggio a contratto le copia. -->
            <CampiCanoneTestata
              v-model:generazione="form.generazione_canone"
              v-model:mese="form.mese_partenza_canone"
              :bloccato-generazione="testata.bloccato('generazione_canone')"
              :bloccato-mese="testata.bloccato('mese_partenza_canone')"
              :campi-errati="campiErrati"
            />
          </div>

          <!-- === Utility inline (mirror ContrattoDrawer) === -->
          <h4>{{ t('vendite.offerte.section_utenza') }}</h4>
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_tipo_utenza') }}</label>
              <LookupSelect
                v-model="form.utility_tipo_utenza_id"
                rel="config.tipi_utenze"
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
                :min-fraction-digits="0"
                :max-fraction-digits="6"
                :disabled="isReadonly"
              />
            </div>
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_param_2_txt') }}</label>
              <InputText
                v-model="form.utility_param_2_txt"
                :disabled="isReadonly"
              />
            </div>
          </div>

          <!-- Sezione indirizzi (UX v2, BB condiviso): solo il default,
               contatore "+N altri", pulsante "Indirizzi" che apre il
               drawer di gestione. Solo in EDIT (documento persistito). -->
          <DocumentoIndirizziSection
            v-if="isEdit && detail"
            dominio="offerte"
            :doc-id="offertaId"
            :soggetto-ruolo-id="detail?.soggetto_ruolo_id ?? null"
            :istanza-utility-id="detail?.istanza_utility_id ?? null"
            :readonly="parentReadonly"
            :capabilities="capabilities" />

          <!-- Motivazione (sola lettura, valorizzata su RIFIUTATA/ANNULLATA) -->
          <template v-if="isEdit && detail?.motivazione_rifiuto">
            <h4>{{ t('vendite.offerte.section_motivazione') }}</h4>
            <Message severity="warn" :closable="false" size="small">
              {{ detail.motivazione_rifiuto }}
            </Message>
          </template>


        </TabPanel>

        <!-- ====================== TAB REVISIONI ====================== -->
        <TabPanel value="revisioni">
          <!-- Lista a catalogo `vendite.offerta_revisioni` (colonne
               gemelle di quelle del preventivo). Montata solo in EDIT: in
               CREATE il tab e' spento e non c'e' una catena da leggere. -->
          <RevisioniTab
            v-if="isEdit"
            codice="vendite.offerta_revisioni"
            :store="revisioniStore"
            :documento-id="visible ? offertaId : null"
            :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
            :severity="statoOffertaSeverity"
            :intro="t('vendite.offerte.revisioni_intro')"
            :vuoto="t('vendite.offerte.revisioni_empty')" />
        </TabPanel>
      </TabPanels>
    </Tabs>

    <!-- Sub-drawer righe (master-detail inline): la lista `vendite.offerta_righe`
         coi verbi del DB, gemella di quella del contratto. -->
    <OffertaRigheDrawer
      v-if="isEdit && detail"
      v-model:visible="eccezioniDrawerVisible"
      :offerta-id="props.offertaId"
      :emittente-fiscale-id="detail.emittente_fiscale_id ?? null"
      :offerta-codice="detail.codice"
      :offerta-stato-codice="stato"
      :righe-modificabili="caps.flag('can_edit_eccezioni')"
      :offerta-stato-descrizione="detail.stato_descrizione"
      :offerta-cliente="detail.billing_account_display"
      :offerta-validita-dal="detail.validita_dal"
      :offerta-validita-al="detail.validita_al"
      @changed="refreshDetail"
    />

    <!-- Sub-drawer note partizionate. Le eccezioni vengono passate per
         popolare il select RIGA nel form note (anchor RIGA). -->
    <VenditeNoteDrawer
      v-if="isEdit && detail"
      v-model:visible="noteDrawerVisible"
      @saved="contatoreNote.aggiorna"
      dominio="offerte"
      :id="props.offertaId"
      :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
      :righe="detail.eccezioni || []"
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
      :motivazione-obbligatoria="esitoDialogMotivazioneObbligatoria"
      :loading="loading || annullo.loading.value"
      @confirm="handleEsitoConferma"
    />
    <!-- La conferma dell'annullo di una revisione (la precedente torna
         emessa): aperta dalla domanda del DB, chiusa dalla conferma o dalla
         rinuncia. -->
    <DocumentoAnnulloLegamiDialog
      v-if="offertaId"
      :visible="domandaAnnullo !== null"
      base-path="/vendite/offerte"
      :doc-id="offertaId"
      :header="t('vendite.offerte.esito_annullata_titolo')"
      :domanda="domandaAnnullo"
      :loading="annullo.loading.value"
      :readonly="parentReadonly"
      @conferma="onConfermaAnnullo"
      @cancel="annullo.annulla()"
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
          :icon="MANAGE_ICONS.CONTRATTI"
          severity="primary"
          :disabled="!detail?.contratto_id"
          @click="onApriContrattoEsistente"
        />
      </template>
    </AppDialog>
  </AppDrawer>
</template>
