<script setup>
// Scopo: Drawer crea/modifica vendite.promo_articoli.
//        - In create: codice, articolo, uom, tipo, valore, valido_dal/al obbligatori.
//          valido_dal default = domani; minDate = domani (no promo retroattive).
//        - In edit:   codice, articolo, uom immutabili (identita' della promo).
//          Stato data-driven Profilo A (vedi PromoArticoliService backend):
//            * SCADUTA  (oggi > valido_al)        -> readonly hard
//            * INIZIATA (valido_dal <= oggi <= valido_al) -> solo descrizione
//              + valido_al (>= oggi) modificabili; tipo/valore/valido_dal/attivo
//              bloccati (BE rifiuta E_PROMO_INIZIATA_CAMPI_RISTRETTI)
//            * FUTURA   -> tutti i campi modificabili, date solo verso il futuro
//        - Sola lettura: prop `readonly` cumulativa con useInjectReadonly.
//        Convenzione valore firmato (negativo = sconto) allineata al resolver
//        DB: ammessi valori negativi, rifiutato 0 per PERCENTUALE/VALORE_FISSO.
//        PREZZO_FISSO accetta solo >= 0 (prezzo assoluto sostitutivo).
import { ref, watch, computed, provide, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePromoArticoliStore } from '../stores/promoArticoli'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useInjectReadonly, READONLY_KEY } from '../../core/composables/useReadonlyMode'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import { addDaysToToday, parseIsoDate, toDateString } from '../../core/utils/date'
import { paramBool, paramInt } from '../../core/utils/parameterCast'
import { useArticoloUomOptions } from '../../catalogo/composables/useArticoloUomOptions'
import { useEntityCapabilities } from '../../core/composables/useEntityCapabilities'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import AppDrawer from '../../core/components/AppDrawer.vue'
import ArticoloLookup from '../../catalogo/components/ArticoloLookup.vue'
import TipoVariazioneSelect from './TipoVariazioneSelect.vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'

const { t } = useI18n()
const store = usePromoArticoliStore()
const { execute, loading, campiErrati } = useApiHandler()
const notify = useNotify()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  recordId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

// Capability dal detail backend (Fase 1.B3: script.fn_capability_promo_articolo),
// lette da `detail.capabilities` via il BB:
//   - stato_temporale: FUTURA | INIZIATA | SCADUTA (data-driven puro)
//   - can_update + can_update_reason: editabilita' globale
//   - min_valido_dal / min_valido_al: vincoli minDate (Date | null)
//   - non_editable_fields: whitelist BE per campo (Set lookup O(1))
const detail = ref(null)
// Composable centralizzato (Fase 4.F2): editFlag custom can_update; in create
// il drawer usa default true (no detail) — wrappato in canUpdate computed sotto.
const caps = useEntityCapabilities(detail, { editFlag: 'can_update' })
const capabilities = caps.capabilities
const statoTemporale = computed(() => capabilities.value.stato_temporale || null)
// In create detail=null -> can_update non e' valutato dal BE; lasciamo true.
const canUpdate = computed(() => !isEdit.value || caps.canEdit.value)
const canUpdateReason = computed(() => capabilities.value.can_update_reason || null)
const minValidoDalDetail = computed(() => parseIsoDate(capabilities.value.min_valido_dal))
const minValidoAlDetail = computed(() => parseIsoDate(capabilities.value.min_valido_al))

// Helper: campo bloccato. In create niente locked (detail assente, l'utente
// puo' valorizzare tutto); in edit applica isLocked del composable.
function isLocked(field) {
  if (!isEdit.value) return false
  return caps.isLocked(field)
}

// In create il backend non espone capability ne' min_valido_*; il vincolo
// "no promo retroattive (preavviso N gg)" e' UX defense-in-depth, configurato
// via VENDITE_PROMO_DEFAULT_VALIDO_DAL_LEAD_GG (default 1 = domani).
const { defaults: paramDefaults, load: loadParamDefaults } = useParameterDefaults([
  'VENDITE_PROMO_DEFAULT_VALIDO_DAL_LEAD_GG',
  'VENDITE_PROMO_DEFAULT_ATTIVO',
])

// Lead-time in giorni per valido_dal in create (parameter, default 1).
const promoValidoDalLeadGg = computed(
  () => paramInt(paramDefaults.value.VENDITE_PROMO_DEFAULT_VALIDO_DAL_LEAD_GG, 1),
)

// minDate effettivo del DatePicker valido_dal:
//   - create   -> oggi + LEAD_GG (UX, niente retroattive)
//   - edit     -> dal backend (null = nessun vincolo)
const validoDalMinDate = computed(() =>
  isEdit.value ? minValidoDalDetail.value : addDaysToToday(promoValidoDalLeadGg.value),
)
// minDate del DatePicker valido_al:
//   - create   -> oggi + LEAD_GG (>= valido_dal di default)
//   - edit     -> dal backend
const validoAlMinDate = computed(() =>
  isEdit.value ? minValidoAlDetail.value : addDaysToToday(promoValidoDalLeadGg.value),
)

// Alias retrocompat con il template (mostra banner per stato).
const isPromoIniziata = computed(() => statoTemporale.value === 'INIZIATA')

// Readonly cumulativo del drawer parent (pattern frontend-standards.md
// "Drawer di entita' con sub-drawer (catena readonly)"):
//   1. permessi area/oggetto via inject
//   2. props.readonly (split-view)
//   3. capability BE `can_update` (SCADUTA -> false)
//   4. flag `attivo=false` (= promo "annullata" / disattivata): coerente con
//      pattern soft-delete contratti.ANNULLATO -> immutabile. Una promo
//      disattivata e' cristallizzata; per riproporla si crea una nuova promo.
// Il computed e' propagato via `provide(READONLY_KEY)` cosi' eventuali
// sub-drawer futuri (note promo, ecc.) ereditano correttamente senza
// logica locale.
const isReadOnlyEffective = computed(
  () => props.readonly
    || isReadonly.value
    || (isEdit.value && !canUpdate.value)
    || (isEdit.value && detail.value?.attivo === false),
)
provide(READONLY_KEY, isReadOnlyEffective)

const form = ref({
  codice: '',
  descrizione: '',
  articolo_obj: null,       // oggetto completo {id, codice, descrizione, _display}
  uom_id: null,
  tipo_variazione: null,
  valore_variazione: null,
  valido_dal: null,
  valido_al: null,
  attivo: true
})
// Modifiche non salvate: fotografia a form popolato (creazione o modifica),
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

function resetForm() {
  form.value = {
    codice: '',
    descrizione: '',
    articolo_obj: null,
    uom_id: null,
    tipo_variazione: null,
    valore_variazione: null,
    // Default da parameters: valido_dal = oggi + LEAD_GG (default 1 = domani),
    // attivo = true. Le promo non possono partire nel passato e di norma
    // nemmeno nel giorno corrente (preavviso operativo).
    valido_dal: addDaysToToday(promoValidoDalLeadGg.value),
    valido_al: null,
    attivo: paramBool(paramDefaults.value.VENDITE_PROMO_DEFAULT_ATTIVO, true)
  }
  detail.value = null
  resetUomOptions()
}

// UoM operative dell'articolo selezionato (pattern VersioneDrawer/ContrattoRigheDrawer):
// l'articolo definisce quali UoM sono ammesse per le sue righe/promo; una combo
// globale su catalogo.unita_misura porterebbe FK invalide.
// Composable centralizzato (Fase 4.F1): fetch + helper pickBase. Il drawer
// applica il pre-pick solo in create, quando il form non ha gia' un valore.
const {
  uomOptions, uomLoading, loadUomPerArticolo, pickBaseUomId, resetUomOptions,
} = useArticoloUomOptions()

function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('vendite.listini.uom_base_suffix')}` : ''
  return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
}

// Scopo: carica le UoM dell'articolo; in create pre-seleziona la base.
async function caricaUomConPickBase(articoloId) {
  const list = await loadUomPerArticolo(articoloId)
  if (!isEdit.value && !form.value.uom_id) {
    form.value.uom_id = pickBaseUomId(list)
  }
}

async function loadDetail() {
  if (!props.recordId) return
  const data = await store.fetchDetail(props.recordId)
  if (!data) return
  // Detail completo (include il blob `capabilities`: stato_temporale,
  // can_update[+reason], min_valido_*, non_editable_fields).
  detail.value = data
  form.value = {
    codice: data.codice ?? '',
    descrizione: data.descrizione ?? '',
    // Restore articolo_obj da display fields per AutoComplete server-side.
    articolo_obj: data.articolo_id ? {
      id: data.articolo_id,
      codice: data.articolo_codice,
      descrizione: data.articolo_descrizione,
      _display: `${data.articolo_codice} — ${data.articolo_descrizione}`
    } : null,
    uom_id: data.uom_id ?? null,
    tipo_variazione: data.tipo_variazione ?? null,
    valore_variazione: data.valore_variazione != null
      ? Number(data.valore_variazione)
      : null,
    valido_dal: parseIsoDate(data.valido_dal),
    valido_al: parseIsoDate(data.valido_al),
    attivo: data.attivo ?? true
  }
  // In edit carichiamo comunque l'elenco UoM dell'articolo per mostrare label
  // coerente nel Select (anche se il campo e' disabilitato).
  if (data.articolo_id) await loadUomPerArticolo(data.articolo_id)
}

watch(
  [() => props.visible, () => props.recordId],
  async ([visible]) => {
    if (!visible) return
    // Carica parameters (cache modulo) prima di resetForm per popolare
    // valido_dal/attivo dai default seedati.
    await loadParamDefaults()
    if (isEdit.value) {
      await loadDetail()
    } else {
      resetForm()
    }
    // Dopo il nextTick: il watch su articolo_obj qui sotto puo' ancora
    // scrivere uom_id, e la fotografia deve vedere il form com'e' davvero.
    await nextTick()
    fissa()
  }
)

// In create: al cambio articolo ricarica le UoM operative + autopick base.
// Cambio articolo dopo che una UoM era gia' selezionata ⇒ azzera prima,
// altrimenti resta il valore precedente e puo' appartenere a un articolo diverso.
watch(
  () => form.value.articolo_obj?.id,
  (newId, oldId) => {
    if (isEdit.value) return
    if (newId === oldId) return
    form.value.uom_id = null
    caricaUomConPickBase(newId)
  }
)

// Scopo: Reset valore_variazione al cambio di tipo_variazione non-null.
// Motivo: la semantica del valore cambia (10% vs 10€ vs 10€ fisso); tenere
// il numero precedente e' fonte d'errore silenzioso. Toast informativo.
// Il wrapper TipoVariazioneSelect emette il valore stringa (non l'event PrimeVue).
function onTipoVariazioneChange(value) {
  const hadValue = form.value.valore_variazione != null
  if (value == null) {
    form.value.valore_variazione = null
    return
  }
  if (hadValue) {
    form.value.valore_variazione = null
    notify.warn(t('common.tipo_variazione_reset'))
  }
}

const canSave = computed(() => {
  if (isReadOnlyEffective.value) return false
  if (!form.value.descrizione || form.value.descrizione.trim() === '') return false
  if (form.value.tipo_variazione == null) return false
  if (form.value.valore_variazione == null) return false
  if (form.value.valido_dal == null || form.value.valido_al == null) return false
  if (!isEdit.value) {
    if (!form.value.codice || form.value.codice.trim() === '') return false
    if (!form.value.articolo_obj?.id) return false
    if (form.value.uom_id == null) return false
  }
  // Coerenza segno: PERCENTUALE/VALORE_FISSO != 0; PREZZO_FISSO >= 0.
  const v = form.value.valore_variazione
  if (form.value.tipo_variazione === 'PREZZO_FISSO' && v < 0) return false
  if (form.value.tipo_variazione !== 'PREZZO_FISSO' && v === 0) return false
  return true
})

async function handleSave() {
  const payload = {
    descrizione: form.value.descrizione.trim(),
    tipo_variazione: form.value.tipo_variazione,
    valore_variazione: String(form.value.valore_variazione),
    valido_dal: toDateString(form.value.valido_dal),
    valido_al: toDateString(form.value.valido_al),
    attivo: form.value.attivo
  }
  if (!isEdit.value) {
    payload.codice = form.value.codice.trim().toUpperCase()
    payload.articolo_id = form.value.articolo_obj.id
    payload.uom_id = form.value.uom_id
  }
  const result = await execute(
    () => isEdit.value
      ? store.update(props.recordId, payload)
      : store.create(payload),
    {
      successMessage: isEdit.value
        ? t('vendite.promo_articoli.saved')
        : t('vendite.promo_articoli.created')
    }
  )
  if (result !== null) {
    // Salvato: il parent chiude dopo aver ricaricato la lista, e nel
    // frattempo il drawer non deve dirsi «modificato».
    fissa()
    emit('saved', result)
  }
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.promo_articoli.drawer_title')"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
    :readonly="isReadOnlyEffective"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >
  <!-- Banner stato temporale: il backend espone stato_temporale +
       can_update_reason (i18n-ready). Quando reason esiste, la chiave
       e' direttamente la label da renderizzare. -->
  <Message
    v-if="isEdit && canUpdateReason"
    severity="info"
    :closable="false"
  >
    {{ t(`vendite.promo_articoli.update_reason.${canUpdateReason.toLowerCase()}`,
          t('vendite.promo_articoli.scaduta_readonly_hint')) }}
  </Message>
  <Message
    v-else-if="isPromoIniziata"
    severity="warn"
    :closable="false"
  >
    {{ t('vendite.promo_articoli.iniziata_warn_hint') }}
  </Message>

  <div class="form-grid">
    <!-- === Identita' (immutabile in edit via non_editable_fields) === -->
    <div class="form-field">
      <label>{{ t('vendite.promo_articoli.field_codice') }} <span v-if="!isEdit">*</span></label>
      <InputText
        v-model="form.codice"
        :disabled="isReadOnlyEffective || isLocked('codice')"
        :placeholder="t('vendite.promo_articoli.field_codice_placeholder')"
        maxlength="64"
        :invalid="campiErrati.includes('codice')"
      />
    </div>
    <div class="form-field">
      <label>{{ t('vendite.promo_articoli.field_descrizione') }} *</label>
      <InputText
        v-model="form.descrizione"
        :disabled="isReadOnlyEffective || isLocked('descrizione')"
        :placeholder="t('vendite.promo_articoli.field_descrizione_placeholder')"
        maxlength="255"
        :invalid="campiErrati.includes('descrizione')"
      />
    </div>
    <div class="form-field">
      <label>{{ t('vendite.promo_articoli.field_articolo') }} <span v-if="!isEdit">*</span></label>
      <ArticoloLookup
        v-model="form.articolo_obj"
        :disabled="isReadOnlyEffective || isLocked('articolo_id')"
        documento="PROMO_ARTICOLO"
        :placeholder="t('vendite.promo_articoli.field_articolo_placeholder')"
      />
    </div>
    <div class="form-field">
      <label>{{ t('vendite.promo_articoli.field_uom') }} <span v-if="!isEdit">*</span></label>
      <Select
        v-model="form.uom_id"
        :options="uomOptions"
        :option-label="uomLabel"
        option-value="uom_id"
        :loading="uomLoading"
        :placeholder="!form.articolo_obj?.id
          ? t('vendite.promo_articoli.field_uom_articolo_first')
          : t('vendite.promo_articoli.field_uom_placeholder')"
        :disabled="isReadOnlyEffective || isLocked('uom_id') || !form.articolo_obj?.id"
        :invalid="campiErrati.includes('uom_id')"
      />
    </div>

    <Message v-if="isEdit" severity="info" :closable="false">
      {{ t('vendite.promo_articoli.identita_immutable_hint') }}
    </Message>

    <!-- === Variazione === -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.promo_articoli.field_tipo_variazione') }} *</label>
        <TipoVariazioneSelect
          v-model="form.tipo_variazione"
          scope="promo"
          :placeholder="t('vendite.promo_articoli.field_tipo_variazione_placeholder')"
          :disabled="isReadOnlyEffective || isLocked('tipo_variazione')"
          @change="onTipoVariazioneChange"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.promo_articoli.field_valore_variazione') }} *</label>
        <InputNumber
          v-model="form.valore_variazione"
          :max-fraction-digits="4"
          :disabled="form.tipo_variazione == null || isReadOnlyEffective || isLocked('valore_variazione')"
          showButtons
          :invalid="campiErrati.includes('valore_variazione')"
        />
        <small class="app-text-muted">
          {{ form.tipo_variazione === 'PREZZO_FISSO'
            ? t('vendite.promo_articoli.field_valore_variazione_hint_prezzo_fisso')
            : t('vendite.promo_articoli.field_valore_variazione_hint') }}
        </small>
      </div>
    </div>

    <!-- === Validita' === -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.promo_articoli.field_valido_dal') }} *</label>
        <DatePicker
          v-model="form.valido_dal"
          :date-format="DATE_FORMAT"
          show-icon
          :min-date="validoDalMinDate"
          :disabled="isReadOnlyEffective || isLocked('valido_dal')"
          :invalid="campiErrati.includes('valido_dal')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.promo_articoli.field_valido_al') }} *</label>
        <DatePicker
          v-model="form.valido_al"
          :date-format="DATE_FORMAT"
          show-icon
          :min-date="validoAlMinDate"
          :disabled="isReadOnlyEffective || isLocked('valido_al')"
          :invalid="campiErrati.includes('valido_al')"
        />
      </div>
    </div>

    <div class="form-field">
      <label>{{ t('common.attivo') }}</label>
      <ToggleSwitch
        v-model="form.attivo"
        :disabled="isReadOnlyEffective || isLocked('attivo')"
        :invalid="campiErrati.includes('attivo')"
      />
    </div>
  </div>
  </AppDrawer>
</template>
