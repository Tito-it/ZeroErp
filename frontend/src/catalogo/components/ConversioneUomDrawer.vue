<script setup>
// Scopo: Drawer crea/modifica conversione UoM.
//        In create: seleziona UoM Da, UoM A, fattore, date validita'.
//        In edit: UoM Da/A immutabili, modifica fattore, date, attivo.
//        Contenuto deferito a dopo l'animazione per evitare rimbalzi visivi.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConversioniUomStore } from '../stores/conversioniUom'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookupCodici } from '../../core/composables/useLookupCodici'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import { parseIsoDate, toDateString } from '../../core/utils/date'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import Drawer from 'primevue/drawer'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'

const ALWAYS_VALID_FROM = '1900-01-01'

const { t } = useI18n()
const store = useConversioniUomStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()
const uomLookup = useLookupCodici('catalogo.unita_misura', { immediate: true })

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  convId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({
  uom_from_id: null, uom_to_id: null, fattore: null,
  valido_dal: parseIsoDate(ALWAYS_VALID_FROM), valido_dal_sempre: true,
  valido_al: null, attivo: true
})

// Fase 5: campi immutabili dopo create per conversioni UoM. Vengono dal
// detail (`detail.non_editable_fields`, fonte = `dbops.vw_non_editable_fields`
// + gap Python su catalogo.unita_misura_conversioni).
const nonEditableFields = ref([])
function isFieldLocked(name) {
  return isEdit.value && nonEditableFields.value.includes(name)
}

// Deferimento contenuto: i LookupSelect montano solo dopo l'animazione del drawer
// (pattern feedback_content_ready_after_show centralizzato in useDrawerContentReady).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const selectedFromTipoId = computed(() => {
  const selected = uomLookup.items.value.find(item => item.id === form.value.uom_from_id)
  return selected?.tipo_uom_id ?? null
})

function resetForm() {
  form.value = {
    uom_from_id: null, uom_to_id: null, fattore: null,
    valido_dal: parseIsoDate(ALWAYS_VALID_FROM),
    valido_dal_sempre: true,
    valido_al: null,
    attivo: true
  }
}

function todayLocalDate() {
  return parseIsoDate(toDateString(new Date()))
}

async function loadDetail() {
  if (!props.convId) return
  const data = await store.fetchDetail(props.convId)
  if (!data) return
  form.value = {
    uom_from_id: data.uom_from_id,
    uom_to_id: data.uom_to_id,
    fattore: Number(data.fattore),
    valido_dal: parseIsoDate(data.valido_dal),
    valido_dal_sempre: data.valido_dal === ALWAYS_VALID_FROM,
    valido_al: parseIsoDate(data.valido_al),
    attivo: data.attivo ?? true
  }
  nonEditableFields.value = data.non_editable_fields || []
}

watch(() => props.visible, (v) => {
  if (!v) return  // contentReady reset gestito da useDrawerContentReady
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
  }
})

watch(selectedFromTipoId, (tipoId) => {
  if (tipoId == null || form.value.uom_to_id == null) return
  const selectedTo = uomLookup.items.value.find(item => item.id === form.value.uom_to_id)
  if (selectedTo && selectedTo.tipo_uom_id !== tipoId) {
    form.value.uom_to_id = null
  }
})

watch(() => form.value.valido_dal_sempre, (sempre) => {
  if (isEdit.value) return
  form.value.valido_dal = sempre ? parseIsoDate(ALWAYS_VALID_FROM) : todayLocalDate()
})

const canSave = computed(() =>
  form.value.uom_from_id != null &&
  form.value.uom_to_id != null &&
  form.value.fattore != null && form.value.fattore > 0
)

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {
      fattore: f.fattore,
      valido_dal: toDateString(f.valido_dal),
      valido_al: toDateString(f.valido_al),
      attivo: f.attivo,
    }
    const result = await execute(
      () => store.update(props.convId, payload),
      { successMessage: t('catalogo.conv_salvata') }
    )
    if (result !== null) { emit('saved', result); close() }
  } else {
    const payload = {
      uom_from_id: f.uom_from_id,
      uom_to_id: f.uom_to_id,
      fattore: f.fattore,
      valido_dal: f.valido_dal_sempre ? ALWAYS_VALID_FROM : toDateString(f.valido_dal),
      valido_al: toDateString(f.valido_al),
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('catalogo.conv_creata') }
    )
    if (result !== null) { emit('saved', result); close() }
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.STANDARD }" :dismissable="true"
    @after-show="onAfterShow">
    <template #header>
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('catalogo.conversione_uom')" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('catalogo.field_uom_da') }} *</label>
            <LookupSelect v-model="form.uom_from_id" rel="catalogo.unita_misura"
              :placeholder="t('catalogo.select_uom')" :disabled="isFieldLocked('uom_from_id')" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_uom_a') }} *</label>
            <LookupSelect v-model="form.uom_to_id" rel="catalogo.unita_misura"
              :placeholder="t('catalogo.select_uom')" filter-field="tipo_uom_id"
              :filter-value="selectedFromTipoId" :disabled="isFieldLocked('uom_to_id')" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_fattore') }} *</label>
            <InputNumber v-model="form.fattore" :min-fraction-digits="2" :max-fraction-digits="6" :min="0" mode="decimal" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('common.data_da') }}</label>
            <DatePicker
              v-model="form.valido_dal"
              :dateFormat="DATE_FORMAT"
              showIcon
              showButtonBar
              :disabled="!isEdit && form.valido_dal_sempre"
              :invalid="campiErrati.includes('valido_dal')"
            />
          </div>
          <div class="form-field">
            <label>{{ t('common.data_a') }}</label>
            <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar
              :invalid="campiErrati.includes('valido_al')"
            />
          </div>
        </div>
        <div v-if="!isEdit" class="form-grid">
          <div class="form-field">
            <label>{{ t('catalogo.validita_sempre') }}</label>
            <ToggleSwitch v-model="form.valido_dal_sempre" />
          </div>
        </div>

        <div v-if="isEdit" class="form-grid">
          <div class="form-field">
            <label>{{ t('indirizzi.campo_attivo') }}</label>
            <ToggleSwitch v-model="form.attivo"
              :invalid="campiErrati.includes('attivo')"
            />
          </div>
        </div>
      </template>

      <div v-else class="app-loading">
        <i class="pi pi-spin pi-spinner" style="font-size: 1.5rem;"></i>
      </div>

      <FormFooter v-if="contentReady" :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
