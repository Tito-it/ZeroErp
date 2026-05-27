<script setup>
// Scopo: Drawer crea/modifica tipologia UoM.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUomTipiStore } from '../stores/uomTipi'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()
const store = useUomTipiStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  tipoId: { type: Number, default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({ codice: '', codice_interno: '', descrizione: '', attivo: true })

function resetForm() {
  form.value = { codice: '', codice_interno: '', descrizione: '', attivo: true }
}

async function loadDetail() {
  if (!props.tipoId) return
  const data = await store.fetchDetail(props.tipoId)
  if (!data) return
  form.value = {
    codice: data.codice || '',
    codice_interno: data.codice_interno || '',
    descrizione: data.descrizione || '',
    attivo: data.attivo ?? true
  }
}

watch(
  [() => props.visible, () => props.mode, () => props.tipoId],
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
  if (isReadonly.value) return false
  return Boolean(
    form.value.codice?.trim() &&
    form.value.codice_interno?.trim() &&
    form.value.descrizione?.trim()
  )
})

async function handleSave() {
  if (isEdit.value) {
    const payload = {
      descrizione: form.value.descrizione?.trim(),
      attivo: form.value.attivo,
    }
    const result = await execute(() => store.update(props.tipoId, payload), { successMessage: t('catalogo.uom_tipo_salvato') })
    if (result !== null) emit('saved', result)
  } else {
    const payload = {
      codice: form.value.codice?.trim(),
      codice_interno: form.value.codice_interno?.trim(),
      descrizione: form.value.descrizione?.trim(),
    }
    const result = await execute(() => store.create(payload), { successMessage: t('catalogo.uom_tipo_creato') })
    if (result !== null) emit('saved', result)
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
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('catalogo.uom_tipo')" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('catalogo.field_codice') }}</label>
          <InputText v-model="form.codice" :disabled="isEdit || isReadonly" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.col_codice_interno') }}</label>
          <InputText v-model="form.codice_interno" :disabled="isEdit || isReadonly" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_descrizione') }}</label>
          <InputText v-model="form.descrizione" :disabled="isReadonly" />
        </div>
        <div v-if="isEdit" class="form-field">
          <label>{{ t('indirizzi.campo_attivo') }}</label>
          <ToggleSwitch v-model="form.attivo" :disabled="isReadonly" />
        </div>
      </div>

      <FormFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
