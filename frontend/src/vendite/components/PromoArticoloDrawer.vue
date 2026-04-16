<script setup>
// Scopo: Drawer crea/modifica vendite.promo_articoli.
//        - In create: codice, articolo, uom, tipo, valore, valido_dal/al obbligatori.
//        - In edit:   codice, articolo, uom immutabili (identita' della promo).
//        - Sola lettura: prop `readonly` cumulativa con useInjectReadonly.
//        Convenzione valore firmato (negativo = sconto) allineata al resolver
//        DB: ammessi valori negativi, rifiutato 0 per PERCENTUALE/VALORE_FISSO.
//        PREZZO_FISSO accetta solo >= 0 (prezzo assoluto sostitutivo).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePromoArticoliStore } from '../stores/promoArticoli'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import { isoToLocalDate, localDateToIso } from '../../core/utils/dateHelpers'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'

const { t } = useI18n()
const store = usePromoArticoliStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  recordId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const isReadOnlyEffective = computed(() => props.readonly || isReadonly.value)

const tipoVariazioneOptions = [
  { value: 'PERCENTUALE', label: 'PERCENTUALE' },
  { value: 'VALORE_FISSO', label: 'VALORE_FISSO' },
  { value: 'PREZZO_FISSO', label: 'PREZZO_FISSO' }
]

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

function resetForm() {
  form.value = {
    codice: '',
    descrizione: '',
    articolo_obj: null,
    uom_id: null,
    tipo_variazione: null,
    valore_variazione: null,
    valido_dal: null,
    valido_al: null,
    attivo: true
  }
}

async function loadDetail() {
  if (!props.recordId) return
  const data = await store.fetchDetail(props.recordId)
  if (!data) return
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
    valido_dal: isoToLocalDate(data.valido_dal),
    valido_al: isoToLocalDate(data.valido_al),
    attivo: data.attivo ?? true
  }
}

watch(
  [() => props.visible, () => props.recordId],
  ([visible]) => {
    if (!visible) return
    if (isEdit.value) {
      loadDetail()
    } else {
      resetForm()
    }
  }
)

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
    valido_dal: localDateToIso(form.value.valido_dal),
    valido_al: localDateToIso(form.value.valido_al),
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
  if (result !== null) emit('saved', result)
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('vendite.promo_articoli.drawer_title')"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadOnlyEffective }">
      <div class="form-grid">
        <!-- === Identita' (immutabile in edit) === -->
        <div class="form-field">
          <label>{{ t('vendite.promo_articoli.field_codice') }} <span v-if="!isEdit">*</span></label>
          <InputText
            v-model="form.codice"
            :disabled="isEdit || isReadOnlyEffective"
            :placeholder="t('vendite.promo_articoli.field_codice_placeholder')"
            maxlength="64"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.promo_articoli.field_descrizione') }} *</label>
          <InputText
            v-model="form.descrizione"
            :disabled="isReadOnlyEffective"
            :placeholder="t('vendite.promo_articoli.field_descrizione_placeholder')"
            maxlength="255"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.promo_articoli.field_articolo') }} <span v-if="!isEdit">*</span></label>
          <ArticoloLookup
            v-model="form.articolo_obj"
            :disabled="isEdit || isReadOnlyEffective"
            :placeholder="t('vendite.promo_articoli.field_articolo_placeholder')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.promo_articoli.field_uom') }} <span v-if="!isEdit">*</span></label>
          <LookupSelect
            v-model="form.uom_id"
            rel="catalogo.unita_misura"
            :placeholder="t('vendite.promo_articoli.field_uom_placeholder')"
            :disabled="isEdit || isReadOnlyEffective"
          />
        </div>

        <Message v-if="isEdit" severity="info" :closable="false">
          {{ t('vendite.promo_articoli.identita_immutable_hint') }}
        </Message>

        <!-- === Variazione === -->
        <div class="form-field">
          <label>{{ t('vendite.promo_articoli.field_tipo_variazione') }} *</label>
          <Select
            v-model="form.tipo_variazione"
            :options="tipoVariazioneOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('vendite.promo_articoli.field_tipo_variazione_placeholder')"
            :disabled="isReadOnlyEffective"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.promo_articoli.field_valore_variazione') }} *</label>
          <InputNumber
            v-model="form.valore_variazione"
            :max-fraction-digits="4"
            :disabled="form.tipo_variazione == null || isReadOnlyEffective"
            showButtons
          />
          <small class="text-color-secondary">
            {{ form.tipo_variazione === 'PREZZO_FISSO'
              ? t('vendite.promo_articoli.field_valore_variazione_hint_prezzo_fisso')
              : t('vendite.promo_articoli.field_valore_variazione_hint') }}
          </small>
        </div>

        <!-- === Validita' === -->
        <div class="form-field">
          <label>{{ t('vendite.promo_articoli.field_valido_dal') }} *</label>
          <DatePicker
            v-model="form.valido_dal"
            date-format="dd/mm/yy"
            show-icon
            :disabled="isReadOnlyEffective"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.promo_articoli.field_valido_al') }} *</label>
          <DatePicker
            v-model="form.valido_al"
            date-format="dd/mm/yy"
            show-icon
            :disabled="isReadOnlyEffective"
          />
        </div>

        <div class="form-field">
          <label>{{ t('common.attivo') }}</label>
          <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective" />
        </div>
      </div>

      <DrawerFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="close"
      />
    </div>
  </Drawer>
</template>
