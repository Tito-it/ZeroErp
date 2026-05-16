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
import { useInjectReadonly, READONLY_KEY } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useEntityCapabilities } from '../../core/composables/useEntityCapabilities'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { addDaysToToday, toDateString, parseIsoDate } from '../../core/utils/date'
import { paramInt, paramString } from '../../core/utils/parameterCast'
import { statoContrattoSeverity } from '../../core/utils/severity'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import DocumentiGeneratiSorgenteList from '../../documenti/components/DocumentiGeneratiSorgenteList.vue'
import ContrattoRigheDrawer from './ContrattoRigheDrawer.vue'
import ContrattoPdfButton from './ContrattoPdfButton.vue'
import TipoVariazioneSelect from './TipoVariazioneSelect.vue'
import AmbitoContrattoSelect from './AmbitoContrattoSelect.vue'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { useUtilityDefaultId } from '../../core/composables/useUtilityDefaultId'
import Drawer from 'primevue/drawer'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'

const { t } = useI18n()
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
const canEditTestata = caps.canEdit
const canEditRighe = computed(() => caps.flag('can_edit_righe'))
const canChangeState = computed(() => caps.flag('can_change_state'))
const nonEditableFields = caps.nonEditableFields
const isLocked = caps.isLocked
const righeCount = computed(() => detail.value?.righe_count ?? detail.value?.righe?.length ?? 0)

// isContractLocked deriva ora da !canEditTestata (mantenuto per leggibilita'
// del template "banner contratto bloccato"). In create non c'e' detail, quindi
// non e' "locked".
const isContractLocked = computed(() => isEdit.value && !canEditTestata.value)

// isReadonly effettivo del drawer: OR tra permessi area e !canEditTestata.
// Tutti i campi/azioni del drawer principale e dei sub-drawer (righe, utility)
// devono basarsi su questo computed. Propagato via provide ai figli.
const isReadonly = computed(() => parentReadonly.value || isContractLocked.value)
provide(READONLY_KEY, isReadonly)

// Deferimento contenuto: i LookupSelect montano solo dopo l'animazione del drawer.
const contentReady = ref(false)
function onAfterShow() { contentReady.value = true }

// Sub-drawer
const righeVisible = ref(false)

// fgVersion: invalida fetch stantii su apertura/chiusura rapide.
let fgVersion = 0

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

function defaultForm() {
  const p = paramDefaults.value
  const dataLeadGg = paramInt(p.VENDITE_CONTRATTO_DEFAULT_DATA_LEAD_GG, 0)
  const validoDalLeadGg = paramInt(p.VENDITE_CONTRATTO_DEFAULT_VALIDO_DAL_LEAD_GG, 0)
  return {
    billing_account_id: null,
    billing_account_obj: null,
    istanza_utility_id: null,
    utility_id: utilityDefaultId.value,
    ambito: paramString(p.VENDITE_CONTRATTO_DEFAULT_AMBITO, 'COMMODITY'),
    valido_dal: toDateString(addDaysToToday(validoDalLeadGg)),
    valido_al: null,
    data: toDateString(addDaysToToday(dataLeadGg)),
    parent_contratto_id: null,
    meta_note: '',
    // Categoria cliente snapshot
    categoria_cliente_id_snapshot: null,
    // Pricing — refactor modalita 2026-05-15: niente piu' SelectButton A/B/C.
    // Listino e variazione globale sono campi opzionali liberi; la "forma"
    // (con/senza listino) e' derivata e mostrata come badge readonly post-save.
    listino_id: null,
    tipo_variazione_globale: null,
    valore_variazione_globale: null,
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
    meta_note: d.meta?.note || '',
    categoria_cliente_id_snapshot: d.categoria_cliente_id_snapshot || null,
    listino_id: d.listino_id,
    tipo_variazione_globale: d.tipo_variazione_globale,
    valore_variazione_globale: d.valore_variazione_globale,
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
  } else if (!form.value.tipo_variazione_globale) {
    // Pre-fill tipo da parameter; valore resta vuoto = nessuna variazione.
    form.value.tipo_variazione_globale = paramString(
      paramDefaults.value.VENDITE_CONTRATTO_DEFAULT_TIPO_VARIAZIONE_GLOBALE,
      'PERCENTUALE',
    )
  }
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

// Carica dati all'apertura
watch(() => props.visible, async (val) => {
  if (!val) { fgVersion++; contentReady.value = false; return }
  const v = ++fgVersion

  // loadParamDefaults serve sia in EDIT (onModalitaChange usa
  // VENDITE_CONTRATTO_DEFAULT_TIPO_VARIAZIONE_GLOBALE) sia in CREATE.
  // loadUtilityDefault serve solo in CREATE (in EDIT utility_id arriva
  // dal detail BE). In CREATE le carichiamo in parallelo.
  if (isEdit.value && props.contrattoId) {
    await loadParamDefaults()
    if (v !== fgVersion) return
    const d = await store.fetchDetail(props.contrattoId)
    if (v !== fgVersion) return
    detail.value = d
    populateFromDetail(d)
  } else {
    await Promise.all([loadParamDefaults(), loadUtilityDefault()])
    if (v !== fgVersion) return
    resetForm()
    // Prefill BA se aperto da contesto cliente.
    if (props.initialBillingAccount?.id) {
      onBaSelected(props.initialBillingAccount)
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
    form.value.utility_id = null
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

// Validazione FE (refactor modalita 2026-05-15: niente piu' check su modalita).
// Vincolo strutturale unico sulla coppia variazione globale: tipo e valore
// devono essere entrambi presenti o entrambi null (vincolo BE
// _validate_variazione_globale_coppia_coerente). Listino e variazione sono
// indipendenti: contratto senza listino e' valido (forma "senza_listino"),
// contratto con listino senza variazione e' valido (forma "con_listino"
// listino tal quale), contratto con listino + variazione e' valido.
const canSave = computed(() => {
  if (isReadonly.value) return false
  if (isEdit.value) return true
  const f = form.value
  if (!f.billing_account_id) return false
  if (!f.valido_dal || !f.data) return false
  if (!f.ambito) return false
  // Coppia variazione coerente: tipo presente <=> valore presente.
  const hasTipo = !!f.tipo_variazione_globale
  const hasValore = f.valore_variazione_globale != null && f.valore_variazione_globale !== ''
  if (hasTipo !== hasValore) return false
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
  const stato = isEdit.value ? (detail.value?.stato_codice || null) : 'DRAFT'
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
  }
  if (f.meta_note) payload.meta = { note: f.meta_note }
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
      { successMessage: t('contratti.contratto_salvato') }
    )
    if (result !== null) emit('saved', result)
  } else {
    const f = form.value
    const payload = {
      billing_account_id: f.billing_account_id,
      istanza_utility_id: f.istanza_utility_id,
      utility_id: f.utility_id,
      ...buildPayload(),
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
      { successMessage: t('contratti.contratto_creato') }
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
// con `default_date` e `min_date` arrivati direttamente dal BE
// (script.fn_available_actions_contratto). Niente regole locali sul default
// data ne' sui vincoli minimi: vivono in DB.
//
// Comportamento data-driven (allineato col backend e col guard DB):
// - data <  oggi  -> cessazione immediata: stato passa a CESSATO
// - data >= oggi  -> cessazione PROGRAMMATA: stato resta ATTIVO,
//                    job notturno DB allinea quando la data scade
const cessaDialogVisible = ref(false)
const cessaDialogData = ref(null)
const cessaDialogAction = ref(null)
const cessaDialogMinDate = computed(
  () => parseIsoDate(cessaDialogAction.value?.min_date) || null,
)

const cessazioneProgrammata = computed(() => {
  if (!cessaDialogData.value) return false
  const oggi = new Date()
  oggi.setHours(0, 0, 0, 0)
  const scelta = new Date(cessaDialogData.value)
  scelta.setHours(0, 0, 0, 0)
  return scelta >= oggi
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
        ? t('contratti.cessa_dialog_success_programmata', { data: validoAl })
        : t('contratti.cessa_dialog_success_immediata'),
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
  if (action.requires_date) {
    openCessaDialog(action)
    return
  }
  if (action.requires_confirm) {
    confirmAction({
      title: t('contratti.conferma_titolo'),
      message: t('contratti.conferma_cambio_stato', { stato: t(action.label_key) }),
      onAccept: () => eseguiCambioStato(action.target_state),
    })
    return
  }
  eseguiCambioStato(action.target_state)
}

async function eseguiCambioStato(targetState) {
  const result = await execute(
    () => store.cambiaStato(props.contrattoId, targetState),
    { successMessage: t('contratti.stato_cambiato') },
  )
  if (result !== null) await refreshDetail()
}

const onClose = useDrawerClose(emit, 'cancelled')
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
        :title="t('contratti.contratto')"
        icon="pi pi-file-edit"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">

      <!-- === Intestazione edit: numero + stato + azione affiancata === -->
      <template v-if="isEdit && detail">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('contratti.field_numero') }}</label>
            <InputText :model-value="detail.numero" disabled class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('contratti.field_stato') }}</label>
            <div class="flex align-items-center gap-2">
              <Tag :value="detail.stato_descrizione" :severity="statoContrattoSeverity(detail.stato_codice)" />
              <Button v-for="action in availableActions" :key="action.key"
                :label="t(action.label_key)"
                :icon="action.icon"
                :severity="action.severity"
                size="small" outlined
                class="app-escape"
                @click="onCambiaStato(action)" />
              <ContrattoPdfButton
                :contratto-id="props.contrattoId"
                :stato-codice="detail.stato_codice"
                :numero="detail.numero"
              />
            </div>
          </div>
        </div>

        <!-- Banner contratto bloccato: in stati post-DRAFT ammessa solo
             modifica valido_al (programma cessazione) + cambio stato.
             Coerente con Profilo A whitelist BE. -->
        <Message v-if="isContractLocked && detail.stato_codice !== 'CESSATO'"
          severity="info" :closable="false" size="small" class="mt-2">
          {{ t('contratti.banner_locked_attivo', { stato: detail.stato_descrizione }) }}
        </Message>
        <Message v-else-if="isContractLocked && detail.stato_codice === 'CESSATO'"
          severity="warn" :closable="false" size="small" class="mt-2">
          {{ t('contratti.banner_locked_cessato') }}
        </Message>
      </template>

      <!-- === Cliente (BA) + badge utility/PDP === -->
      <h4 class="mt-3">
        {{ t('contratti.section_cliente') }}
        <Tag v-if="baBadgeLabel" :value="baBadgeLabel" severity="info" class="ml-2" />
      </h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('contratti.field_billing_account') }} <span v-if="!isEdit">*</span></label>
          <BillingAccountLookup
            v-if="!isEdit"
            :model-value="form.billing_account_obj"
            @update:model-value="onBaSelected"
            :placeholder="t('contratti.select_billing_account')"
          />
          <InputText v-else :model-value="detail?.ba_ragione_sociale" disabled class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('contratti.field_ambito') }} <span v-if="!isEdit">*</span></label>
          <AmbitoContrattoSelect v-model="form.ambito"
            class="w-full" :disabled="isEdit && isLocked('ambito')" />
        </div>
      </div>
      <!-- Categoria cliente snapshot: editabile in create e in DRAFT,
           bloccata dopo attivazione (BE/non_editable_fields + trigger DB) -->
      <div class="form-grid-2col mt-1">
        <div class="form-field">
          <label>{{ t('contratti.field_categoria_cliente_snapshot') }}</label>
          <LookupSelect
            v-model="form.categoria_cliente_id_snapshot"
            rel="anagrafiche.categorie_clienti"
            class="w-full"
            :placeholder="t('contratti.select_categoria_cliente')"
            show-clear
            :disabled="isEdit && isLocked('categoria_cliente_id_snapshot')"
          />
        </div>
      </div>

      <!-- === Validità === -->
      <h4 class="mt-3">{{ t('contratti.section_validita') }}</h4>
      <div class="form-grid-3col">
        <div class="form-field">
          <label>{{ t('contratti.field_data') }} *</label>
          <DatePicker :model-value="parseIsoDate(form.data)"
            @update:model-value="form.data = toIsoDate($event)"
            :disabled="isEdit && isLocked('data')"
            date-format="dd/mm/yy" show-icon class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('contratti.field_valido_dal') }} *</label>
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
            || detail?.stato_codice === 'DRAFT'
            || detail?.stato_codice === 'CESSATO'
            || (form.valido_al && detail?.stato_codice === 'ATTIVO')">
          <label>
            {{ detail?.stato_codice === 'CESSATO'
              ? t('contratti.field_data_cessazione')
              : detail?.stato_codice === 'ATTIVO' && form.valido_al
                ? t('contratti.field_cessazione_programmata')
                : t('contratti.field_valido_al') }}
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
      <h4 class="mt-3">{{ t('contratti.section_pricing') }}</h4>

      <!-- Badge forma derivata: visibile in EDIT come audit visivo del path. -->
      <Message
        v-if="isEdit && detail"
        :severity="formaDerivata === 'senza_listino' ? 'warn' : 'info'"
        :closable="false" size="small"
      >
        {{ t(`contratti.forma_${formaDerivata}_descrizione`) }}
      </Message>

      <div class="form-field">
        <label>{{ t('contratti.field_listino') }}</label>
        <LookupSelect v-model="form.listino_id" rel="vendite.listini" class="w-full"
          :placeholder="t('contratti.select_listino_opzionale')"
          show-clear
          @update:model-value="onListinoChange"
          :disabled="isEdit && isLocked('listino_id')" />
        <small class="text-color-secondary">
          {{ t('contratti.hint_listino_opzionale') }}
        </small>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('contratti.field_tipo_variazione') }}</label>
          <TipoVariazioneSelect v-model="form.tipo_variazione_globale"
            scope="contratto"
            show-clear
            class="w-full"
            :disabled="isEdit && isLocked('tipo_variazione_globale')" />
        </div>
        <div class="form-field">
          <label>{{ t('contratti.field_valore_variazione') }}</label>
          <InputNumber v-model="form.valore_variazione_globale" class="w-full"
            :min-fraction-digits="0" :max-fraction-digits="4" showButtons
            @update:model-value="onValoreVariazioneChange"
            :disabled="isEdit && isLocked('valore_variazione_globale')"
            :suffix="form.tipo_variazione_globale === 'PERCENTUALE' ? ' %' : ''" />
          <small class="text-color-secondary">{{ t('contratti.hint_valore_variazione') }}</small>
        </div>
      </div>

      <!-- === Tipo/Classe utenza (editabile in BOZZA, readonly dopo) === -->
      <h4 class="mt-3">{{ t('contratti.section_utenza') }}</h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('contratti.field_tipo_utenza') }}</label>
          <LookupSelect v-model="form.utility_tipo_utenza_id" rel="config.tipi_utenze" class="w-full"
            :placeholder="t('contratti.select_tipo_utenza')" show-clear
            :disabled="isEdit && detail?.stato_codice !== 'DRAFT'" />
        </div>
        <div class="form-field">
          <label>{{ t('contratti.field_classe_utenza') }}</label>
          <LookupSelect v-model="form.utility_classe_utenza_id" rel="config.classi_utenze" class="w-full"
            :placeholder="t('contratti.select_classe_utenza')" show-clear
            :disabled="isEdit && detail?.stato_codice !== 'DRAFT'" />
        </div>
      </div>

      <!-- === Note === -->
      <h4 class="mt-3">{{ t('contratti.section_note') }}</h4>
      <div class="form-field">
        <Textarea v-model="form.meta_note" rows="2" autoResize class="w-full"
          :disabled="isEdit && isLocked('meta')" />
      </div>

      <!-- === Gestione righe (solo edit) === -->
      <template v-if="isEdit && detail">
        <h4 class="mt-3">{{ t('contratti.section_gestione') }}</h4>
        <div class="form-row-inline">
          <Button :icon="MANAGE_ICONS.LIST" :label="t('contratti.gestisci_righe')"
            outlined class="app-manage-btn"
            @click="righeVisible = true" />
          <span class="text-color-secondary">{{ righeCount }} {{ t('contratti.righe_count_label') }}</span>
        </div>
      </template>

      <template v-if="isEdit && detail && detail.stato_codice !== 'DRAFT'">
        <h4 class="mt-3">{{ t('contratti.pdf.section_documenti') }}</h4>
        <div class="app-escape">
          <DocumentiGeneratiSorgenteList
            sorgente-code="CONTRATTO"
            :sorgente-id="props.contrattoId"
            hide-header-when-empty
          />
        </div>
      </template>

      <DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="onClose" />
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
      :contratto-stato-codice="detail.stato_codice"
      :contratto-stato-descrizione="detail.stato_descrizione"
      @changed="refreshDetail"
    />

    <!-- Dialog cessazione contratto: chiede la data di cessazione (default
         oggi) e fa POST cambia-stato {CESSATO, valido_al} in transazione BE.
         Comportamento data-driven:
         - data < oggi  -> cessazione immediata, stato CESSATO
         - data >= oggi -> cessazione programmata, stato resta ATTIVO -->
    <Dialog v-model:visible="cessaDialogVisible" modal
      :header="cessazioneProgrammata
        ? t('contratti.cessa_dialog_titolo_programma')
        : t('contratti.cessa_dialog_titolo_immediata')"
      :style="{ width: '460px' }">
      <div class="form-field">
        <label>{{ t('contratti.cessa_dialog_data') }}</label>
        <DatePicker v-model="cessaDialogData" date-format="dd/mm/yy"
          show-icon show-button-bar :min-date="cessaDialogMinDate" />
      </div>
      <Message :severity="cessazioneProgrammata ? 'info' : 'warn'"
        :closable="false" class="mt-1" size="small">
        {{ cessazioneProgrammata
          ? t('contratti.cessa_dialog_warning_programmata')
          : t('contratti.cessa_dialog_warning_immediata') }}
      </Message>
      <template #footer>
        <Button :label="t('common.cancel')" text severity="secondary"
          @click="cessaDialogVisible = false" />
        <Button :label="cessazioneProgrammata
            ? t('contratti.cessa_dialog_conferma_programma')
            : t('contratti.cessa_dialog_conferma_immediata')"
          :icon="cessazioneProgrammata ? 'pi pi-calendar' : 'pi pi-times'"
          :severity="cessazioneProgrammata ? 'warn' : 'danger'"
          :disabled="!cessaDialogData || loading" :loading="loading"
          @click="onConfermaCessazione" />
      </template>
    </Dialog>

  </Drawer>
</template>
