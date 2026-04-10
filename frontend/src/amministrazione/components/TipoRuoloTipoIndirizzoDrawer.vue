<script setup>
// Scopo: Drawer crea/modifica riga matrice config.tipi_ruolo_tipi_indirizzo.
// FK immutabili in edit: tipo_ruolo_id, tipo_indirizzo_id.
// Campi modificabili in edit: attivo, obbligatorio, fallback_tipo_indirizzo_id.
// Sola lettura: prop `readonly` cumulativa con useInjectReadonly.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTipiRuoloTipiIndirizzoStore } from '../stores/tipiRuoloTipiIndirizzo'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useTipiRuoloTipiIndirizzoStore()
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

const form = ref({
  tipo_ruolo_id: null,
  tipo_indirizzo_id: null,
  obbligatorio: false,
  fallback_tipo_indirizzo_id: null,
  attivo: true
})

function resetForm() {
  form.value = {
    tipo_ruolo_id: null,
    tipo_indirizzo_id: null,
    obbligatorio: false,
    fallback_tipo_indirizzo_id: null,
    attivo: true
  }
}

async function loadDetail() {
  if (!props.recordId) return
  const data = await store.fetchDetail(props.recordId)
  if (!data) return
  form.value = {
    tipo_ruolo_id: data.tipo_ruolo_id,
    tipo_indirizzo_id: data.tipo_indirizzo_id,
    obbligatorio: data.obbligatorio ?? false,
    fallback_tipo_indirizzo_id: data.fallback_tipo_indirizzo_id,
    attivo: data.attivo ?? true
  }
}

watch(() => props.visible, (v) => {
  if (!v) return
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
  }
})

const canSave = computed(() => {
  if (isEdit.value) return true
  return form.value.tipo_ruolo_id && form.value.tipo_indirizzo_id
})

async function handleSave() {
  if (isEdit.value) {
    const payload = {
      attivo: form.value.attivo,
      obbligatorio: form.value.obbligatorio,
      fallback_tipo_indirizzo_id: form.value.fallback_tipo_indirizzo_id || null
    }
    const result = await execute(
      () => store.update(props.recordId, payload),
      { successMessage: t('amministrazione.matrice_indirizzi_ruoli.saved') }
    )
    if (result !== null) { emit('saved', result); close() }
  } else {
    const payload = {
      tipo_ruolo_id: form.value.tipo_ruolo_id,
      tipo_indirizzo_id: form.value.tipo_indirizzo_id,
      obbligatorio: form.value.obbligatorio,
      attivo: form.value.attivo
    }
    if (form.value.fallback_tipo_indirizzo_id) {
      payload.fallback_tipo_indirizzo_id = form.value.fallback_tipo_indirizzo_id
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('amministrazione.matrice_indirizzi_ruoli.created') }
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
    position="right" :style="{ width: DRAWER_WIDTH.SIMPLE }" :dismissable="true">
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('amministrazione.matrice_indirizzi_ruoli.drawer_title')"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadOnlyEffective }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_indirizzi_ruoli.field_tipo_ruolo') }}</label>
          <LookupSelect v-model="form.tipo_ruolo_id" rel="config.tipi_ruoli"
            :placeholder="t('amministrazione.matrice_indirizzi_ruoli.field_tipo_ruolo_placeholder')"
            :disabled="isEdit || isReadOnlyEffective" />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_indirizzi_ruoli.field_tipo_indirizzo') }}</label>
          <LookupSelect v-model="form.tipo_indirizzo_id" rel="config.tipi_indirizzi"
            :placeholder="t('amministrazione.matrice_indirizzi_ruoli.field_tipo_indirizzo_placeholder')"
            :disabled="isEdit || isReadOnlyEffective" />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_indirizzi_ruoli.field_obbligatorio') }}</label>
          <ToggleSwitch v-model="form.obbligatorio" :disabled="isReadOnlyEffective" />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_indirizzi_ruoli.field_fallback') }}</label>
          <LookupSelect v-model="form.fallback_tipo_indirizzo_id" rel="config.tipi_indirizzi"
            :placeholder="t('amministrazione.matrice_indirizzi_ruoli.field_fallback_placeholder')"
            :disabled="isReadOnlyEffective" show-clear />
        </div>
        <div v-if="isEdit" class="form-field">
          <label>{{ t('indirizzi.campo_attivo') }}</label>
          <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective" />
        </div>
        <Message v-if="isEdit" severity="info" :closable="false" class="mt-2">
          {{ t('amministrazione.matrice_indirizzi_ruoli.fk_immutable_hint') }}
        </Message>
      </div>

      <DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
