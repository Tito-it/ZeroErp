<script setup>
// Scopo: Drawer crea/modifica unita' di misura.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUnitaMisuraStore } from '../stores/unitaMisura'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()
const store = useUnitaMisuraStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  uomId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({ codice: '', descrizione: '', descrizione_fattura: '', attivo: true })

function resetForm() {
  form.value = { codice: '', descrizione: '', descrizione_fattura: '', attivo: true }
}

async function loadDetail() {
  if (!props.uomId) return
  const data = await store.fetchDetail(props.uomId)
  if (!data) return
  form.value = {
    codice: data.codice || '',
    descrizione: data.descrizione || '',
    descrizione_fattura: data.descrizione_fattura || '',
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

const canSave = computed(() => form.value.codice?.trim() && form.value.descrizione?.trim())

async function handleSave() {
  if (isEdit.value) {
    const payload = {
      descrizione: form.value.descrizione?.trim(),
      descrizione_fattura: form.value.descrizione_fattura?.trim() || null,
      attivo: form.value.attivo,
    }
    const result = await execute(() => store.update(props.uomId, payload), { successMessage: t('catalogo.uom_salvata') })
    if (result !== null) { emit('saved', result); close() }
  } else {
    const payload = {
      codice: form.value.codice?.trim(),
      descrizione: form.value.descrizione?.trim(),
      descrizione_fattura: form.value.descrizione_fattura?.trim() || null
    }
    const result = await execute(() => store.create(payload), { successMessage: t('catalogo.uom_creata') })
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
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('catalogo.unita_misura')" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('catalogo.field_codice') }}</label>
          <InputText v-model="form.codice" :disabled="isEdit" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_descrizione') }}</label>
          <InputText v-model="form.descrizione" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_desc_fattura') }}</label>
          <InputText v-model="form.descrizione_fattura" />
        </div>
        <div v-if="isEdit" class="form-field">
          <label>{{ t('indirizzi.campo_attivo') }}</label>
          <ToggleSwitch v-model="form.attivo" />
        </div>
      </div>

      <DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
