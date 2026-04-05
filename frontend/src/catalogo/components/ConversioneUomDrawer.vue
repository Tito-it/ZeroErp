<script setup>
// Scopo: Drawer crea/modifica conversione UoM.
//        In create: seleziona UoM Da, UoM A, fattore, date validita'.
//        In edit: UoM Da/A immutabili, modifica fattore, date, attivo.
//        Contenuto deferito a dopo l'animazione per evitare rimbalzi visivi.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConversioniUomStore } from '../stores/conversioniUom'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()
const store = useConversioniUomStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  convId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({
  uom_from_id: null, uom_to_id: null, fattore: null,
  valido_dal: null, valido_al: null, attivo: true
})

// Deferimento contenuto: i LookupSelect montano solo dopo l'animazione del drawer
const contentReady = ref(false)

function onAfterShow() {
  contentReady.value = true
}

function resetForm() {
  form.value = {
    uom_from_id: null, uom_to_id: null, fattore: null,
    valido_dal: new Date(), valido_al: null, attivo: true
  }
}

function toIso(d) {
  if (!d) return null
  const dt = new Date(d)
  return dt.toISOString().substring(0, 10)
}

async function loadDetail() {
  if (!props.convId) return
  const data = await store.fetchDetail(props.convId)
  if (!data) return
  form.value = {
    uom_from_id: data.uom_from_id,
    uom_to_id: data.uom_to_id,
    fattore: Number(data.fattore),
    valido_dal: data.valido_dal ? new Date(data.valido_dal + 'T00:00:00') : null,
    valido_al: data.valido_al ? new Date(data.valido_al + 'T00:00:00') : null,
    attivo: data.attivo ?? true
  }
}

watch(() => props.visible, (v) => {
  if (!v) {
    contentReady.value = false
    return
  }
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
  }
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
      valido_dal: toIso(f.valido_dal),
      valido_al: toIso(f.valido_al),
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
      valido_dal: toIso(f.valido_dal),
      valido_al: toIso(f.valido_al),
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
              :placeholder="t('catalogo.select_uom')" :disabled="isEdit" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_uom_a') }} *</label>
            <LookupSelect v-model="form.uom_to_id" rel="catalogo.unita_misura"
              :placeholder="t('catalogo.select_uom')" :disabled="isEdit" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_fattore') }} *</label>
            <InputNumber v-model="form.fattore" :min-fraction-digits="2" :max-fraction-digits="6" :min="0" mode="decimal" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('common.data_da') }}</label>
            <DatePicker v-model="form.valido_dal" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
          </div>
          <div class="form-field">
            <label>{{ t('common.data_a') }}</label>
            <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
          </div>
        </div>

        <div v-if="isEdit" class="form-grid">
          <div class="form-field">
            <label>{{ t('indirizzi.campo_attivo') }}</label>
            <ToggleSwitch v-model="form.attivo" />
          </div>
        </div>
      </template>

      <div v-else class="app-loading">
        <i class="pi pi-spin pi-spinner" style="font-size: 1.5rem;"></i>
      </div>

      <DrawerFooter v-if="contentReady" :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
