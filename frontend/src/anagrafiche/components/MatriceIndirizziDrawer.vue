<script setup>
// Scopo: Drawer creazione/modifica regola matrice indirizzi per ruolo.
// In creazione: tipo_ruolo e tipo_indirizzo selezionabili.
// In edit: tipo_ruolo e tipo_indirizzo readonly (chiavi non modificabili).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookup } from '../../core/composables/useLookup'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { lookupCodici } from '../../core/apiCore'
import { createMatriceIndirizzo, updateMatriceIndirizzo } from '../api/anagrafiche'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { DRAWER_WIDTH } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()
const { emitDataChanged } = useTabEvents()

// Lookup
const tipiRuoli = useLookup(() => lookupCodici('config.tipi_ruoli'), { immediate: true })
const tipiIndirizzi = useLookup(() => lookupCodici('config.tipi_indirizzi'), { immediate: true })

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  regolaId: { type: Number, default: null },
  item: { type: Object, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)

function defaultForm() {
  return {
    tipo_ruolo_id: null,
    tipo_indirizzo_id: null,
    obbligatorio: false,
    fallback_tipo_indirizzo_id: null,
  }
}

function resetForm() {
  detail.value = null
  form.value = defaultForm()
}

function populateFromDetail(d) {
  form.value = {
    tipo_ruolo_id: d.tipo_ruolo_id,
    tipo_indirizzo_id: d.tipo_indirizzo_id,
    obbligatorio: d.obbligatorio ?? false,
    fallback_tipo_indirizzo_id: d.fallback_tipo_indirizzo_id,
  }
}

// Scopo: Opzioni fallback (tutti i tipi indirizzo tranne il tipo selezionato).
const fallbackOptions = computed(() => {
  const tipoId = form.value.tipo_indirizzo_id
  if (!tipoId) return tipiIndirizzi.items.value
  return tipiIndirizzi.items.value.filter(ti => ti.id !== tipoId)
})

watch(() => props.visible, (val) => {
  if (!val) return
  if (isEdit.value && props.item) {
    detail.value = props.item
    populateFromDetail(props.item)
  } else {
    resetForm()
  }
})

// Scopo: Reset fallback se diventa uguale al tipo indirizzo.
watch(() => form.value.tipo_indirizzo_id, (newVal) => {
  if (form.value.fallback_tipo_indirizzo_id === newVal) {
    form.value.fallback_tipo_indirizzo_id = null
  }
})

async function onSave() {
  if (isEdit.value) {
    const result = await execute(
      () => updateMatriceIndirizzo(props.regolaId, {
        obbligatorio: form.value.obbligatorio,
        fallback_tipo_indirizzo_id: form.value.fallback_tipo_indirizzo_id,
      }),
      { successMessage: t('matrice_indirizzi.regola_salvata') }
    )
    if (result !== null) {
      emitDataChanged('matrice-indirizzi', props.regolaId)
      emit('saved', result)
    }
  } else {
    const payload = {
      tipo_ruolo_id: form.value.tipo_ruolo_id,
      tipo_indirizzo_id: form.value.tipo_indirizzo_id,
      obbligatorio: form.value.obbligatorio,
      fallback_tipo_indirizzo_id: form.value.fallback_tipo_indirizzo_id,
    }
    const result = await execute(
      () => createMatriceIndirizzo(payload),
      { successMessage: t('matrice_indirizzi.regola_creata') }
    )
    if (result !== null) {
      emitDataChanged('matrice-indirizzi', result.id)
      emit('saved', result)
    }
  }
}

const canSave = computed(() => {
  if (isEdit.value) return true
  return !!form.value.tipo_ruolo_id && !!form.value.tipo_indirizzo_id
})

function onClose() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.SIMPLE }"
    @update:visible="val => emit('update:visible', val)"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('matrice_indirizzi.regola')"
        icon="pi pi-th-large"
      />
    </template>

    <div :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">

        <!-- Tipo Ruolo -->
        <div class="form-field">
          <label>{{ t('matrice_indirizzi.field_tipo_ruolo') }} <span v-if="!isEdit">*</span></label>
          <Select v-if="!isEdit"
            v-model="form.tipo_ruolo_id"
            :options="tipiRuoli.items.value"
            :loading="tipiRuoli.loading.value"
            option-label="descrizione"
            option-value="id"
            class="w-full"
            :placeholder="t('matrice_indirizzi.select_ruolo')"
          />
          <InputText v-else :model-value="detail?.tipo_ruolo_descrizione" disabled class="w-full" />
        </div>

        <!-- Tipo Indirizzo -->
        <div class="form-field">
          <label>{{ t('matrice_indirizzi.field_tipo_indirizzo') }} <span v-if="!isEdit">*</span></label>
          <Select v-if="!isEdit"
            v-model="form.tipo_indirizzo_id"
            :options="tipiIndirizzi.items.value"
            :loading="tipiIndirizzi.loading.value"
            option-label="descrizione"
            option-value="id"
            class="w-full"
            :placeholder="t('matrice_indirizzi.select_tipo_indirizzo')"
          />
          <InputText v-else :model-value="detail?.tipo_indirizzo_descrizione" disabled class="w-full" />
        </div>

        <!-- Obbligatorio -->
        <div class="form-field">
          <Checkbox v-model="form.obbligatorio" :binary="true" input-id="obbligatorio" />
          <label for="obbligatorio" class="ml-2">{{ t('matrice_indirizzi.field_obbligatorio') }}</label>
        </div>

        <!-- Fallback -->
        <div class="form-field">
          <label>{{ t('matrice_indirizzi.field_fallback') }}</label>
          <Select
            v-model="form.fallback_tipo_indirizzo_id"
            :options="fallbackOptions"
            option-label="descrizione"
            option-value="id"
            class="w-full"
            :placeholder="t('matrice_indirizzi.nessun_fallback')"
            show-clear
          />
        </div>

        <!-- Info audit (solo edit) -->
        <template v-if="isEdit && detail">
          <div class="form-field mt-3">
            <label>{{ t('matrice_indirizzi.col_attivo') }}</label>
            <Tag :value="detail.attivo ? t('common.yes') : t('common.no')"
              :severity="detail.attivo ? 'success' : 'secondary'" />
          </div>
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('matrice_indirizzi.col_valido_dal') }}</label>
              <InputText :model-value="displayDate(detail.valido_dal)" disabled class="w-full" />
            </div>
            <div class="form-field">
              <label>{{ t('matrice_indirizzi.col_valido_al') }}</label>
              <InputText :model-value="displayDate(detail.valido_al) || '—'" disabled class="w-full" />
            </div>
          </div>
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('common.data_insert') }}</label>
              <InputText :model-value="displayDate(detail.data_insert)" disabled class="w-full" />
            </div>
            <div class="form-field">
              <label>{{ t('common.data_update') }}</label>
              <InputText :model-value="displayDate(detail.data_update)" disabled class="w-full" />
            </div>
          </div>
        </template>

      </div>

      <div class="flex justify-end mt-4">
        <DrawerFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="onClose" />
      </div>
    </div>
  </Drawer>
</template>
