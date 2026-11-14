<script setup>
// Scopo: Drawer crea/modifica ordine di vendita.
// CREATE: form testata con auto-save BOZZA al primo set di campi minimi
//   (cliente) → "edit-evolved" interno (createdId + hasDetail), poi righe inline.
// EDIT: testata + righe + componenti BoM + azioni stato (conferma, push commessa).
// Niente revisioni ne' listino in testata (a differenza di preventivi/offerte):
// state machine semplice DRAFT → CONFERMATO + push singolo a commessa.
import { ref, watch, computed, nextTick, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOrdiniStore } from '../stores/ordini'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useContatoreNote } from '../../../core/composables/useContatoreNote'
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
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { useTestataDocumento } from '../../../core/composables/useTestataDocumento'
import { mapAvailableActionsToDrawerActions } from '../../../core/composables/useDrawerActions'
import { statoOrdineSeverity } from '../../../core/utils/severity'
import { labelOrCode } from '../../../core/utils/i18nLabel'
import {
  CAMPI_FORM_TESTATA_ORDINE,
  STATO_ORDINE,
  STATI_ORDINE_EVADIBILI,
} from '../constants'
import { AZIONE_PUSH_COMMESSA } from '../../constants'
import EntityPdfButton from '../../../documenti/components/EntityPdfButton.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { displayDate, toDateString, oggiAziendale, parseIsoDate } from '../../../core/utils/date'
import { getOrdineFormDefaults } from '../../api/formDefaults'
import { createOrdine } from '../api/ordiniApi'
import { useDrawerAutosaveBozza } from '../../../core/composables/useDrawerAutosaveBozza'
import { useRigheDocumento } from '../../../core/composables/useRigheDocumento'
import { ripristinaBillingAccount } from '../../../core/utils/ripristinaLookup'
import { DRAWER_WIDTH, TAB_ENTITIES } from '../../../core/constants'
import { NAV_ICONS } from '../../../core/navigation'
import AppDrawer from '../../../core/components/AppDrawer.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../../core/components/DrawerActionsBar.vue'
import RiepilogoIvaTable from '../../../core/components/RiepilogoIvaTable.vue'
import DocumentoIndirizziSection from '../../_shared/indirizzi/DocumentoIndirizziSection.vue'
import DocumentoCollegamentiBar from '../../_shared/lineage/DocumentoCollegamentiBar.vue'
import SituazioneMerceBar from '../../_shared/situazioneMerce/SituazioneMerceBar.vue'
import OrdiniForm from './OrdiniForm.vue'
import OrdiniRigheTable from './OrdiniRigheTable.vue'
import VenditeNoteDrawer from '../../_shared/note/VenditeNoteDrawer.vue'
import OrdineEvasioneDialog from './dialogs/OrdineEvasioneDialog.vue'
import DocumentoAnnulloLegamiDialog from '../../_shared/annullo/DocumentoAnnulloLegamiDialog.vue'
import OrdineEmissioneDialog from './dialogs/OrdineEmissioneDialog.vue'
import DateConsegnaRigheDialog from '../../_shared/dateConsegna/DateConsegnaRigheDialog.vue'
import { useDateConsegnaRighe } from '../../_shared/dateConsegna/useDateConsegnaRighe'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'

const { t, te } = useI18n()
const store = useOrdiniStore()
const { execute, loading, campiErrati } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  ordineId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'saved', 'changed', 'cancelled'])
const onClose = useDrawerClose(emit, 'cancelled')
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
// Preserva le modifiche non salvate quando `loadDetail` sostituisce il form:
// senza, compilare la testata e poi salvare una RIGA (`@changed` → loadDetail)
// la riportava com'era sul server, in silenzio. BB condiviso coi drawer
// gemelli (difetto trovato sul DDT, 2026-08-17, identico qui).
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
const noteDrawerVisible = ref(false)
// Il pulsante «Gestisci note» standard, col numero delle note del documento
// (BB `useContatoreNote`: dal dettaglio, poi dal sotto-drawer dopo un salvataggio).
const contatoreNote = useContatoreNote(() => detail.value)
// Riepilogo IVA aggregato per aliquota (lettura da `vw_ordini_riepilogo_iva_dettaglio`).
// Auto-popolato a ogni loadDetail e ogni `@changed` delle righe: la vista DB
// e' la single source dei totali documento (regola fiscale DPR 633/72 art. 21).
const riepilogoIva = ref([])
// Pannello visibile quando c'e' almeno una riga aggregata. Il footer della
// RiepilogoIvaTable mostra gia' totale imponibile + imposta + totale documento.
const showRiepilogoIva = computed(
  () => Array.isArray(riepilogoIva.value) && riepilogoIva.value.length > 0,
)

// Auto-save bozza: in CREATE, appena il cliente (BA) e' valorizzato, il drawer
// crea l'ordine in BOZZA e si comporta da "edit-evolved" (righe + azioni stato).
const createdId = ref(null)
const effectiveOrdineId = computed(() => createdId.value ?? props.ordineId)
const hasDetail = computed(() => detail.value !== null)

// Readonly cumulativo: prop esplicita OR readonly area iniettato dal parent OR
// stato post-DRAFT (modifiche libere solo in bozza). Il gate di stato e' su
// `hasDetail` (NON su `props.mode === 'edit'`): in CREATE "edit-evolved" (bozza
// auto-salvata) un'eventuale transizione che porti fuori DRAFT deve bloccare
// subito il form, anche se il drawer e' tecnicamente in mode='create'. Le
// azioni di stato (conferma/push) restano cliccabili in readonly grazie a
// `app-escape` applicato da DrawerActionsBar. Provide ai sub-componenti (righe).
const parentReadonly = useInjectReadonly()
const isReadonly = computed(
  () => props.readonly
    || parentReadonly.value
    || (detail.value !== null
        && detail.value.stato_codice_interno !== STATO_ORDINE.DRAFT),
)
provide(READONLY_KEY, isReadonly)

// Capability data-driven dal detail BE (script.fn_available_actions_ordine):
// availableActions + can_edit_testata + non_editable_fields. Composable
// centralizzato, uniforme a Preventivi/Contratti (Fase 4.F2).
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })

const capabilities = caps.capabilities
const availableActions = caps.availableActions
const canEditRighe = computed(() => caps.flag('can_edit_righe'))
// Push a commessa: la capability include l'azione in `available_actions` solo
// quando e' eseguibile; quando non lo e', espone il motivo nei campi
// can_push_commessa_reason/_key. Presentazione = tooltip su pulsante
// DISABILITATO, non banner (Decisione D del brief catch-all DDT, applicata qui
// per simmetria XOR: `fattura_da_ddt` e' la causa permanente speculare di
// `fattura_da_ordine` — un banner sempre visibile sarebbe rumore perpetuo su
// ogni ordine a trigger SPEDITO/CONSEGNATO). L'entry disabled la sintetizza il
// BB (`azioneNegata`), condivisa con DdtDrawer.
const pushCommessaDisabledAction = computed(() => caps.azioneNegata('can_push_commessa', {
  ...AZIONE_PUSH_COMMESSA,
  label_key: 'vendite.ordini.azione_push_commessa',
}))

// La testata dopo la bozza: quali campi del form si cambiano, dalla capability
// (brief-db-testata-dopo-emissione, R-FE-3). Fuori bozza il form esce dal
// corpo protetto se ha un campo aperto.
const testata = useTestataDocumento({
  caps,
  campi: CAMPI_FORM_TESTATA_ORDINE,
  readonlyPuro: () => isReadonlyPuro.value,
  // Il documento esiste: in EDIT anche prima che arrivi il dettaglio, cosi'
  // la capability ancora vuota tiene il form fermo (fail-closed).
  presente: () => isEdit.value || hasDetail.value,
  corpoProtetto: () => isReadonly.value,
})

// Campi bloccati: quelli della capability. Il cliente lo e' sempre, una volta
// che l'ordine esiste (lock di colonna, E_ORD_CLIENTE_IMMUTABILE): cambiare
// cliente = nuovo ordine. Fino al 2026-10-10 la lista era scritta qui a mano.
// ⚠️ La utility e' una copia del cliente (la scrive il DB): si spegne con lui,
//    ed e' la sola aggiunta di interfaccia.
const nonEditableFields = computed(() => {
  const fermi = testata.campiBloccati.value
  return fermi.includes('billing_account_id') ? [...fermi, 'utility_id'] : fermi
})

// Readonly PURO (permesso LETTURA / split / readonly forzato) — SENZA il
// lock-di-stato post-DRAFT: l'evasione e' un'azione di processo legittima su un
// ordine CONFERMATO (stato post-DRAFT), come lo smistamento sui preventivi
// ACCETTATI. Serve alla dialog di evasione per restare operativa sotto il
// lock-di-stato (prop `readonly` esplicita su AppDialog, che altrimenti
// erediterebbe il lock e nasconderebbe il pulsante), consuntiva solo in
// readonly puro.
const isReadonlyPuro = computed(() => props.readonly || parentReadonly.value)

// Azione evasione (genera DDT) disponibile quando l'ordine ha residuo da
// evadere (CONFERMATO o PARZIALMENTE_EVASO). Trigger fatturazione differita
// (SPEDITO/CONSEGNATO) resta lato DB; qui la vista e' data-driven sullo stato.
const showEvasione = computed(
  () => hasDetail.value
    && STATI_ORDINE_EVADIBILI.includes(detail.value?.stato_codice_interno),
)
// Dialog "Genera DDT": aperta dal pulsante in barra azioni (2026-07-25). Era un
// pannello in coda al contenuto del drawer — le azioni di processo stanno in
// alto, come per il «Genera reso» del DDT.
const evasioneDialogVisible = ref(false)
// ⭐ Il cambio di stato e' un gesto CONFERMABILE (brief-db-annullo-documento-
//    con-legami): l'annullo di un ordine con legami (righe di preventivo,
//    offerta d'origine, righe di commessa da emettere) il DB lo rifiuta
//    (`confirm_and_retry`) finche' chi conferma non dichiara quanti legami ha
//    visto. La domanda la porta a video `DocumentoAnnulloLegamiDialog`; un
//    ordine senza legami passa al primo colpo.
const cambioStato = useForzaturaConfermata()
const { richiestaConferma: domandaAnnullo } = cambioStato

// «Aggiorna date di consegna» (brief-db-date-consegna-righe-in-blocco): le
// due date della riga d'ordine. La richiesta si scrive in bozza; la confermata
// in bozza e dopo la conferma (D-3). Le colonne sono l'unica cosa che
// l'utility sa del documento (D-4).
const dateConsegna = useDateConsegnaRighe({
  colonne: [
    {
      colonna: 'data_consegna_richiesta_cliente',
      labelKey: 'vendite.ordini.riga_data_consegna_richiesta_cliente',
      attiva: () => caps.flag('can_edit_righe'),
    },
    {
      colonna: 'data_consegna_confermata',
      labelKey: 'vendite.ordini.riga_data_consegna_confermata',
      attiva: () => caps.flag('can_edit_righe') || caps.flag('can_edit_data_consegna_confermata'),
      motivo: () => labelOrCode(
        t, te,
        capabilities.value.can_edit_data_consegna_confermata_reason_key,
        capabilities.value.can_edit_data_consegna_confermata_reason,
      ),
    },
  ],
  readonlyPuro: () => isReadonlyPuro.value,
  presente: () => hasDetail.value,
  righe: () => detail.value?.righe_count ?? 0,
})
const dateConsegnaAzione = dateConsegna.azione
const dateConsegnaVisible = dateConsegna.dialogVisible
const dateConsegnaColonne = dateConsegna.colonneAttive

// Scopo: le date sono cambiate sulle righe: si rileggono le righe e la
//        testata, come dopo il verbo per riga (`@changed` della tabella righe).
function onDateConsegnaAggiornate() {
  righeTableRef.value?.loadRighe()
  loadDetail()
}

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

// Scopo: callback @evaso della dialog — generato un DDT dall'ordine: ricarica il
// detail (lo stato ordine viene proiettato dal BE: CONFERMATO/PARZIALMENTE_EVASO/
// EVASO) e le capability. Il tab DDT lo ha gia' avvisato il verbo `generaDdt` dello store.
async function onEvaso() {
  // L'evasione crea un DDT (nuovo arco ordine->DDT) e sposta merce: chip e
  // situazione merce li rileggono le barre, agganciate al dettaglio.
  await loadDetail()
  // ⭐ E la LISTA dietro: l'ordine e' passato a PARZIALMENTE_EVASO e mostra un
  // transito nuovo. `changed` e non `saved` perche' il lavoro continua — il DDT
  // nasce DRAFT e si rifinisce dal tab DDT, quindi il drawer deve restare
  // aperto. 🔴 Senza questa riga la lista restava ferma e il transito compariva
  // solo ricaricando a mano (collaudo di Tid, 2026-09-01).
  emit('changed')
}

// Default emittente fiscale: operatore → id profilo; admin globale → null
// (sceglie via EmittenteFiscaleField in modalita' Select).
const { defaultEmittenteId } = useEmittenteFiscaleField()

// Default utility globale: il parametro DEFAULT_UTILITY stocca un codice_interno
// (framework FK-surrogata); il composable lo risolve all'id locale. Stesso
// pattern di PreventiviDrawer — proposto in CREATE all'apertura del drawer.
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

// Deferimento contenuto: i LookupSelect/AutoComplete montano dopo l'animazione
// di apertura (pattern feedback_content_ready_after_show).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

function defaultForm() {
  return {
    emittente_fiscale_id: defaultEmittenteId.value ?? null,
    // Utility default dal parameter DEFAULT_UTILITY (come preventivi/contratti).
    utility_id: utilityDefaultId.value ?? null,
    billing_account_id: null,
    // _obj per BillingAccountLookup (pattern restore lookup ricco,
    // memoria feedback_autocomplete_restore).
    billing_account_obj: null,
    valuta_id: null,
    modalita_pagamento_id: null,
    termine_pagamento_id: null,
    fatturazione_trigger: null,
    // Corsia di instradamento: default differita (il DB ha DEFAULT false).
    fatturazione_immediata: false,
    data: oggiAziendale(),
  }
}

function resetForm() {
  form.value = defaultForm()
  resetFormPreserve()
  detail.value = null
  createdId.value = null
  riepilogoIva.value = []
}

// Scopo: Carica il riepilogo IVA aggregato dell'ordine. Best-effort: in caso
//        di errore il pannello resta vuoto, i totali in testata restano
//        comunque visibili (il trigger DB li mantiene coerenti).
async function loadRiepilogoIva(targetId = null) {
  const id = targetId ?? effectiveOrdineId.value
  if (!id) return
  try {
    riepilogoIva.value = await store.loadRiepilogoIva(id)
  } catch {
    riepilogoIva.value = []
  }
}

async function loadDetail(id = null) {
  const targetId = id ?? effectiveOrdineId.value
  if (!targetId) return
  const applicaModifiche = preservaForm()
  const data = await loadDetailOrClose(() => store.fetchDetail(targetId))
  if (!data) return
  detail.value = data
  form.value = {
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    utility_id: data.utility_id ?? null,
    billing_account_id: data.billing_account_id ?? null,
    billing_account_obj: null,  // popolato sotto da ripristinaBillingAccount
    valuta_id: data.valuta_id ?? null,
    modalita_pagamento_id: data.modalita_pagamento_id ?? null,
    termine_pagamento_id: data.termine_pagamento_id ?? null,
    fatturazione_trigger: data.fatturazione_trigger ?? null,
    fatturazione_immediata: data.fatturazione_immediata ?? false,
    data: parseIsoDate(data.data),
  }
  // Fissa la baseline e ripristina il non-salvato che la sostituzione
  // avrebbe cancellato (BB useDrawerFormPreserve).
  applicaModifiche()
  await nextTick()
  // Il cliente per l'etichetta del lookup (BB `ripristinaBillingAccount`).
  await ripristinaBillingAccount(form.value, data.billing_account_id)
  // Riepilogo IVA: il trigger DB mantiene i totali in sync con le righe a ogni
  // mutazione; qui leggiamo lo stato corrente (best-effort).
  await loadRiepilogoIva(targetId)
}

watch(() => props.visible, async (v) => {
  if (!v) return
  if (isEdit.value) {
    loadDetail()
  } else {
    // CREATE: risolve la utility di default (parameter DEFAULT_UTILITY) PRIMA di
    // resetForm, così defaultForm() la legge. Poi pre-popola la valuta dalla
    // catena EF (resolve_valuta_default lato BE), come preventivi/offerte.
    await loadUtilityDefault()
    resetForm()
    try {
      const res = await getOrdineFormDefaults(null)
      const data = res?.data?.data
      if (data && form.value.valuta_id == null && data.valuta_id != null) {
        form.value.valuta_id = data.valuta_id
      }
    } catch {
      // Best-effort: se l'API e' giu' il drawer si apre comunque (valuta vuota).
    }
  }
})

// Scopo: applica al form i default derivati dall'anagrafica del cliente (BA):
//        valuta (BA-wins, override), modalita/termine pagamento (solo se vuoti,
//        non si calpesta una scelta dell'operatore). Best-effort. Stessa catena
//        dei preventivi (vendite_form_defaults_service + get_cliente_defaults).
async function applyBaDefaults(baId) {
  if (!baId) return
  try {
    const res = await getOrdineFormDefaults(baId)
    const d = res?.data?.data
    if (!d) return
    const f = form.value
    if (d.valuta_id != null) f.valuta_id = d.valuta_id
    if (f.modalita_pagamento_id == null && d.modalita_pagamento_id != null) {
      f.modalita_pagamento_id = d.modalita_pagamento_id
    }
    if (f.termine_pagamento_id == null && d.termine_pagamento_id != null) {
      f.termine_pagamento_id = d.termine_pagamento_id
    }
  } catch {
    // Best-effort: se l'API e' giu' la bozza si crea senza i default cliente.
  }
}

// Auto-save bozza + abbandono bozza orfana via BB condiviso (B13, regola del 2).
// Trigger: cliente (BA) valorizzato in CREATE. Prima di creare applica i default
// da anagrafica cliente (valuta/modalita/termine). `close` e'
// l'uscita del drawer (`conferma-uscita` di AppDrawer); createdId resta ref del drawer.
const { close } = useDrawerAutosaveBozza({
  emit,
  execute,
  loading,
  createdId,
  visible: () => props.visible,
  isEdit: () => isEdit.value,
  contentReady: () => contentReady.value,
  triggerSources: () => form.value.billing_account_id,
  isReady: (baId) => baId != null,
  createDraftApi: createOrdine,
  buildDraftPayload: async () => {
    await applyBaDefaults(form.value.billing_account_id)
    const f = form.value
    return {
      billing_account_id: f.billing_account_id || null,
      // Opzionale per BE: se omesso (operatore) il trigger DB lo deriva da GUC.
      emittente_fiscale_id: f.emittente_fiscale_id || null,
      valuta_id: f.valuta_id || null,
      modalita_pagamento_id: f.modalita_pagamento_id || null,
      termine_pagamento_id: f.termine_pagamento_id || null,
      fatturazione_trigger: f.fatturazione_trigger || null,
      fatturazione_immediata: !!f.fatturazione_immediata,
      data: f.data ? toDateString(f.data) : null,
    }
  },
  tabEntity: TAB_ENTITIES.ORDINE,
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
    bozzaCreata: t('vendite.ordini.bozza_creata'),
    abbandonoTitolo: t('vendite.ordini.abbandono_bozza_titolo'),
    abbandonoMessage: t('vendite.ordini.conferma_abbandono_bozza'),
    abbandonoConferma: t('vendite.ordini.abbandono_bozza_conferma'),
    bozzaEliminata: t('vendite.ordini.bozza_eliminata'),
  },
})

const canSave = computed(() => {
  if (!testata.modificabile.value) return false
  return form.value.billing_account_id != null
})

async function handleSave() {
  const f = form.value
  if (isEdit.value || createdId.value !== null) {
    // UPDATE testata: in bozza tutto, dopo i soli campi aperti (decide il DB;
    // i bloccati viaggiano invariati e il lock li lascia passare).
    // emittente_fiscale_id NON e' aggiornabile (whitelist BE _UPDATE_KEYS_ORDINE). Inviamo la whitelist: il BE normalizza empty→NULL.
    // ⛔ La utility non si manda: e' una copia del cliente, la scrive il DB
    // (brief-db-esecutivi-ba-coppia). Il cliente invariato passa il lock.
    const payload = {
      billing_account_id: f.billing_account_id ?? null,
      valuta_id: f.valuta_id ?? null,
      modalita_pagamento_id: f.modalita_pagamento_id ?? null,
      termine_pagamento_id: f.termine_pagamento_id ?? null,
      fatturazione_trigger: f.fatturazione_trigger ?? null,
      fatturazione_immediata: !!f.fatturazione_immediata,
      data: f.data ? toDateString(f.data) : null,
    }
    const result = await execute(
      () => store.update(effectiveOrdineId.value, payload),
      { successMessage: t('vendite.ordini.ordine_salvato') }
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
    const payload = {
      billing_account_id: f.billing_account_id || null,
      emittente_fiscale_id: f.emittente_fiscale_id || null,
      valuta_id: f.valuta_id || null,
      modalita_pagamento_id: f.modalita_pagamento_id || null,
      termine_pagamento_id: f.termine_pagamento_id || null,
      fatturazione_trigger: f.fatturazione_trigger || null,
      fatturazione_immediata: !!f.fatturazione_immediata,
      data: f.data ? toDateString(f.data) : null,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('vendite.ordini.ordine_creato') }
    )
    if (result !== null) emit('saved', result)
  }
}

// --- Azioni stato ---

// Dialog emissione ordine: aperto quando l'azione di stato 'conferma' porta a
// CONFERMATO. Sostituisce il confirmAction generico perche' la conferma
// orchestra atomic state + genera documento + allegati lato BE (/emetti/,
// ApiOrdineEmetti, §6 brief-ordini-stampa.md). Mirror del flusso preventivo.
const emissioneDialogVisible = ref(false)
const emissioneLoading = ref(false)

function onConferma() {
  emissioneDialogVisible.value = true
}

// Scopo: callback @confirm di OrdineEmissioneDialog. Riceve i file staged
// dall'utente e chiama store.emetti (POST multipart /emetti/). Se la
// generazione fallisce il BE annulla la conferma (stato resta DRAFT).
async function handleEmissioneConferma({ files }) {
  emissioneLoading.value = true
  const result = await execute(
    () => store.emetti(effectiveOrdineId.value, { allegati: files || [] }),
    { successMessage: t('vendite.ordini.ordine_confermato') },
  )
  emissioneLoading.value = false
  if (result !== null) {
    emissioneDialogVisible.value = false
    await loadDetail()
    emit('saved', result)
  }
}

// Push singolo a commessa. Toast differenziato per `report.stato` (l'orchestrator
// risponde 200 anche con esito PARZIALE/ERRORE per riga — gemello preventivi).
function onPush() {
  confirmAction({
    header: t('vendite.ordini.azione_push_commessa'),
    message: t('vendite.ordini.push_commessa_messaggio'),
    onAccept: async () => {
      const result = await execute(() => store.push(effectiveOrdineId.value))
      if (result === null) return  // errore HTTP gia' gestito da useApiHandler

      const stato = result?.stato
      const pushLogId = result?.push_log_id
      const righe = result?.handlers?.reduce(
        (acc, h) => acc + (h?.created ?? 0) + (h?.updated ?? 0),
        0,
      ) ?? result?.righe_pushable ?? 0

      if (stato === 'COMPLETATO') {
        notify.success(t('vendite.ordini.push_commessa_ok', { righe, push_log_id: pushLogId }))
      } else if (stato === 'PARZIALE') {
        notify.warn(t('vendite.ordini.push_commessa_parziale', { righe, push_log_id: pushLogId }))
      } else if (stato === 'ERRORE') {
        const firstError = result?.handlers?.[0]?.errors?.[0] || t('common.error_generic')
        notify.error(t('vendite.ordini.push_commessa_errore', { primo_errore: firstError }))
      } else if (stato === 'SKIPPED') {
        notify.warn(t('vendite.ordini.push_commessa_skipped'))
      } else {
        notify.success(t('vendite.ordini.push_commessa_ok_generico'))
      }

      if (stato === 'COMPLETATO' || stato === 'PARZIALE') {
        await loadDetail()
        emit('saved', result)
      }
    },
  })
}

// Smista le azioni data-driven (`available_actions`) ai relativi handler.
// conferma/push hanno flussi dedicati (dialog/toast differenziati); le altre
// transizioni (es. annulla) passano dal cambio stato generico.

// Scopo: il nome dello STATO di destinazione per la frase di conferma («Portare
//   il documento nello stato {stato}?»). La descrizione leggibile la sa solo il
//   database (`DRAFT` -> «Bozza», `PARZIALMENTE_EVASO` -> «Parzialmente evaso»: non e'
//   derivabile dal codice), quindi arriva dalla capability come
//   `target_state_descrizione`. Finche' il DB non la espone si ripiega sulla
//   label dell'azione — comportamento invariato, nessun testo mancante.
function statoDestinazione(action) {
  return action.target_state_descrizione || t(action.label_key)
}

function onAction(action) {
  if (action.key === 'conferma') { onConferma(); return }
  if (action.key === 'push_commessa') { onPush(); return }
  if (action.requires_confirm) {
    confirmAction({
      header: t('confirm.cambio_stato_title'),
      message: t('vendite.ordini.conferma_cambio_stato', { stato: statoDestinazione(action) }),
      onAccept: () => eseguiCambioStato(action),
    })
  } else {
    eseguiCambioStato(action)
  }
}

// Transizione di stato generica (es. annulla DRAFT->ANNULLATO). Il trigger DB
// valida l'ammissibilita'; qui orchestriamo chiamata + refresh detail. Il primo
// tentativo va SEMPRE senza dichiarazione (`useForzaturaConfermata`).
async function eseguiCambioStato(action) {
  const result = await cambioStato.esegui(
    (dichiarazione) => store.cambiaStato(effectiveOrdineId.value, action.target_state, dichiarazione),
    { successMessage: t('vendite.ordini.stato_cambiato') },
  )
  await dopoCambioStato(result)
}

// Scopo: l'operatore ha visto i legami e conferma l'annullo: si ripete la
//        chiamata DICHIARANDO quanti erano.
async function onConfermaAnnullo(dichiarazione) {
  await dopoCambioStato(await cambioStato.conferma(dichiarazione))
}

async function dopoCambioStato(result) {
  if (result !== null) {
    // L'annullo ritira i legami: collegamenti e merce li rileggono le barre,
    // agganciate al dettaglio (`:versione`).
    await loadDetail()
    emit('saved', result)
  }
}

// Azioni del drawer ordine consumate da DrawerActionsBar. Le transizioni di
// stato arrivano data-driven da fn_available_actions_ordine (mapper condiviso
// con preventivi/contratti); in readonly puro (LETTURA/split) sono nascoste.
const drawerActions = computed(() => {
  if (!hasDetail.value) return []
  const readonlyPuro = isReadonlyPuro.value
  // `genera_ddt` (evasione) ha il suo pulsante header dedicato sotto, che apre
  // OrdineEvasioneDialog (selezione righe + quantita'): l'azione data-driven
  // omonima e' filtrata a monte per non avere due bottoni per lo stesso
  // percorso. Difensivo: la fn ordini non espone ancora quest'azione, ma il
  // filtro previene doppioni quando arrivera' data-driven.
  const availableActionsHeader = (availableActions.value || [])
    .filter(a => a.key !== 'genera_ddt')
  const stateActions = mapAvailableActionsToDrawerActions({
    availableActions: [...availableActionsHeader, ...pushCommessaDisabledAction.value],
    t,
    te,
    onAction,
    readonly: readonlyPuro,
  })
  return [
    ...stateActions,
    // Genera DDT: apre la dialog di evasione (righe con residuo + quantita').
    // Resta visibile anche in readonly puro — la dialog si apre in sola
    // consultazione (footer di sola chiusura).
    ...(showEvasione.value
      ? [{
          key: 'genera-ddt',
          kind: 'manage',
          label: t('vendite.ordini.evasione_titolo'),
          icon: NAV_ICONS.DDT,
          command: () => { evasioneDialogVisible.value = true },
        }]
      : []),
    ...dateConsegnaAzione.value,
    contatoreNote.azione({
      label: t('vendite.ordini.gestisci_note'),
      command: () => { noteDrawerVisible.value = true },
    }),
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
    :title="t('vendite.ordini.ordine')"
    :icon="NAV_ICONS.ORDINI"
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
        <Tag :value="detail.numero" severity="secondary" />
        <span v-if="detail.data" class="app-drawer-header-muted font-bold">
          {{ displayDate(detail.data) }}
        </span>
        <!-- La provenienza upstream (preventivo/offerta) NON e' piu' un chip
             d'header dedicato: e' assorbita dai chip di
             DocumentoCollegamentiBar sotto la barra azioni, dove sta
             l'origine di TUTTI i domini (2026-07-25). -->

        <template #status>
          <Tag
            :value="detail.stato_descrizione"
            :severity="statoOrdineSeverity(detail.stato_codice_interno)"
          />
        </template>
      </DrawerEntityHeader>

      <DrawerActionsBar :actions="drawerActions" :info-key="capabilities.stato_info_key || ''">
        <template #suffix>
          <!-- Stampa conferma d'ordine: anteprima PDF on-demand
               (ristampabile, §12.4(a)). BB EntityPdfButton riusato 1:1. -->
          <EntityPdfButton
            :sorgente-code="SORGENTE_CODES.ORDINE_VENDITA"
            :entity-id="effectiveOrdineId"
            :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
            :pdf="capabilities.pdf"
            i18n-prefix="vendite.ordini.pdf"
            :dialog-title="detail.numero
              ? t('vendite.ordini.pdf.dialog_title', { numero: detail.numero })
              : ''"
          />
        </template>
      </DrawerActionsBar>

      <!-- Collegamenti diretti (pratica + origine + destinazioni di livello 1):
           segnalazione a colpo d'occhio sotto i pulsanti — «Preventivo»,
           «2 DDT». Il grafo completo si apre dai chip stessi in dialog. -->
      <DocumentoCollegamentiBar
        base-path="/vendite/ordini"
        :versione="detail"
        :doc-id="effectiveOrdineId"
        @documento-chiuso="onDocumentoCollegatoChiuso"
        :readonly="isReadonlyPuro" />

      <!-- Situazione merce dell'ordine: il riassunto per riga ordinata —
           comprese quelle MAI SPEDITE, che il vecchio contatore non
           conteneva affatto — con il dettaglio delle spedizioni e delle due
           code a un clic. E' il rilievo in-app del 2026-08-17: cinque
           schermate per ricostruire una storia, e la riga che la riassume
           non esisteva. -->
      <SituazioneMerceBar
        base-path="/vendite/ordini"
        :versione="detail"
        :doc-id="effectiveOrdineId"
        :readonly="isReadonlyPuro" />
    </template>

    <Divider v-if="hasDetail" />

    <!-- Form testata: monta dopo l'animazione drawer per evitare rimbalzo lookup. -->
    <!-- Fuori bozza il form esce dal corpo protetto se ha un campo aperto
         (`useTestataDocumento`). -->
    <div :class="{ 'app-escape': testata.sopraCorpoProtetto.value }">
      <OrdiniForm
        :campi-errati="campiErrati"
        :form="form" :is-modificabile="testata.modificabile.value"
        :non-editable-fields="nonEditableFields"
        :is-edit="isEdit || createdId !== null"
        :record="detail" />
    </div>

    <!-- Righe: visibili appena c'e' detail (EDIT classico o CREATE post auto-save). -->
    <template v-if="hasDetail">
      <!-- Sezione indirizzi (UX v2, BB condiviso): solo il default CON,
           contatore "+N altri", pulsante "Indirizzi" che apre il drawer
           di gestione. -->
      <DocumentoIndirizziSection
        dominio="ordini"
        :doc-id="effectiveOrdineId"
        :soggetto-ruolo-id="detail?.soggetto_ruolo_id ?? null"
        :istanza-utility-id="detail?.istanza_utility_id ?? null"
        :readonly="isReadonlyPuro"
        :capabilities="capabilities"
        :bordo="false" />

      <Divider />
      <OrdiniRigheTable
        ref="righeTableRef"
        :ordine-id="effectiveOrdineId"
        :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
        :is-modificabile="canEditRighe && !isReadonly"
        :capabilities="capabilities"
        :readonly="isReadonlyPuro"
        :data-documento="detail?.data ?? null"
        @changed="loadDetail()"
        @form-aperto="onFormAperto" />

      <!-- Riepilogo IVA aggregato (regola fiscale DPR 633/72 art. 21).
           Visibile con almeno una riga. Il footer mostra gia' totale
           imponibile + imposta + totale documento. Componente riusabile
           cross-dominio condiviso con preventivi (regola del 2). -->
      <template v-if="showRiepilogoIva">
        <Divider />
        <RiepilogoIvaTable :items="riepilogoIva" :show-subtitle="true" />
      </template>
    </template>
  </AppDrawer>

  <!-- Sub-drawer note: cablato sull'id effettivo dell'ordine. -->
  <VenditeNoteDrawer
    v-if="effectiveOrdineId"
    v-model:visible="noteDrawerVisible"
    @saved="contatoreNote.aggiorna"
    dominio="ordini"
    :id="effectiveOrdineId"
    :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
  />

  <!-- Dialog emissione ordine (transizione DRAFT → CONFERMATO). Wrapper sul
       building block DocumentoEmissioneDialog: anteprima PDF + allegati,
       conferma orchestra atomic state + genera + allegati via /emetti/. -->
  <OrdineEmissioneDialog
    v-model:visible="emissioneDialogVisible"
    :ordine="detail"
    :loading="emissioneLoading"
    @confirm="handleEmissioneConferma"
  />

  <!-- Dialog "Genera DDT" (evasione): righe con residuo + quantita' da evadere,
       aperta dal pulsante in barra azioni. Il DDT nasce DRAFT e si rifinisce
       dal tab DDT; lo stato ordine (PARZIALMENTE_EVASO/EVASO) e' proiettato dal
       BE e si vede dopo il reload del detail. -->
  <!-- La conferma dell'annullo di un ordine con legami: aperta dalla domanda
       del DB, chiusa dalla conferma o dalla rinuncia. -->
  <DocumentoAnnulloLegamiDialog
    v-if="effectiveOrdineId"
    :visible="domandaAnnullo !== null"
    base-path="/vendite/ordini"
    :doc-id="effectiveOrdineId"
    :header="t('vendite.ordini.azione_annulla')"
    :domanda="domandaAnnullo"
    :loading="cambioStato.loading.value"
    :readonly="isReadonlyPuro"
    @conferma="onConfermaAnnullo"
    @cancel="cambioStato.annulla()"
  />

  <DateConsegnaRigheDialog
    v-if="effectiveOrdineId"
    v-model:visible="dateConsegnaVisible"
    :invia="(payload) => store.aggiornaDateConsegna(effectiveOrdineId, payload)"
    :colonne="dateConsegnaColonne"
    :data-documento="detail?.data ?? null"
    :readonly="isReadonlyPuro"
    @aggiornate="onDateConsegnaAggiornate"
  />

  <OrdineEvasioneDialog
    v-if="effectiveOrdineId && showEvasione"
    v-model:visible="evasioneDialogVisible"
    :ordine-id="effectiveOrdineId"
    :readonly="isReadonlyPuro"
    @evaso="onEvaso"
  />
</template>
