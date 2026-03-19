<script setup>
// Scopo: drawer CRUD codici postali (CAP).
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useCodiciPostaliStore } from '../../anagrafiche/stores/codiciPostali'
import { useApiHandler } from '../composables/useApiHandler'
import ComuneAutocomplete from './ComuneAutocomplete.vue'
import DrawerFooter from './DrawerFooter.vue'
import DrawerTitle from './DrawerTitle.vue'
import { DRAWER_WIDTH } from '../constants'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  item: { type: Object, default: null }
})
const emit = defineEmits(['update:visible', 'saved'])
const { t } = useI18n()
const isReadonly = useInjectReadonly()
const store = useCodiciPostaliStore()
const { execute, loading } = useApiHandler()

const form = ref({ codice: '', comune_id: null })

watch(() => props.visible, (val) => {
  if (val) {
    if (props.mode === 'edit' && props.item) {
      form.value = { codice: props.item.codice || '', comune_id: props.item.comune_id }
    } else {
      form.value = { codice: '', comune_id: null }
    }
  }
})

async function handleSave() {
  if (!form.value.codice.trim() || !form.value.comune_id) return
  const msg = props.mode === 'create' ? t('indirizzi.cap_creato') : t('indirizzi.cap_salvato')
  const result = await execute(
    () => props.mode === 'create'
      ? store.create({ codice: form.value.codice.trim(), comune_id: form.value.comune_id })
      : store.update(props.item.id, { codice: form.value.codice.trim(), comune_id: form.value.comune_id }),
    { successMessage: msg }
  )
  if (result !== null) { emit('saved'); emit('update:visible', false) }
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="emit('update:visible', $event)" position="right"
    :style="{ width: DRAWER_WIDTH.SIMPLE }">
    <template #header>
      <DrawerTitle :action="mode === 'create' ? t('common.new') : t('common.edit')" :title="t('indirizzi.cap')" icon="pi pi-inbox" />
    </template>
    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('indirizzi.col_cap') }} *</label>
          <InputText v-model="form.codice" maxlength="5" />
        </div>
        <div class="form-field">
          <label>{{ t('indirizzi.campo_comune') }} *</label>
          <ComuneAutocomplete v-model="form.comune_id" :disabled="mode === 'edit'" />
        </div>
      </div>
      <DrawerFooter :loading="loading" :disabled="!form.codice.trim() || !form.comune_id"
        @save="handleSave" @cancel="emit('update:visible', false)" />
    </div>
  </Drawer>
</template>
