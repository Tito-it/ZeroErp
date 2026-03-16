<script setup>
// Scopo: drawer CRUD regioni.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRegioniStore } from '../../anagrafiche/stores/regioni'
import { useApiHandler } from '../composables/useApiHandler'
import { useLookup } from '../composables/useLookup'
import { lookupStati } from '../../anagrafiche/api/anagrafiche'
import { DRAWER_WIDTH } from '../constants'
import DrawerFooter from './DrawerFooter.vue'
import DrawerTitle from './DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  item: { type: Object, default: null }
})
const emit = defineEmits(['update:visible', 'saved'])
const { t } = useI18n()
const store = useRegioniStore()
const { execute, loading } = useApiHandler()
const statiLookup = useLookup(() => lookupStati())

const form = ref({ descrizione: '', stato_id: null })

watch(() => props.visible, (val) => {
  if (val) {
    if (!statiLookup.loaded.value) statiLookup.load()
    if (props.mode === 'edit' && props.item) {
      form.value = { descrizione: props.item.descrizione || '', stato_id: props.item.stato_id }
    } else {
      form.value = { descrizione: '', stato_id: null }
    }
  }
})

async function handleSave() {
  if (!form.value.descrizione.trim()) return
  const msg = props.mode === 'create' ? t('geo.regione_creata') : t('geo.regione_salvata')
  const result = await execute(
    () => props.mode === 'create'
      ? store.create({ descrizione: form.value.descrizione.trim(), stato_id: form.value.stato_id })
      : store.update(props.item.id, { descrizione: form.value.descrizione.trim(), stato_id: form.value.stato_id }),
    { successMessage: msg }
  )
  if (result !== null) { emit('saved'); emit('update:visible', false); store.fetchList() }
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="emit('update:visible', $event)" position="right"
    :style="{ width: DRAWER_WIDTH.SIMPLE }">
    <template #header>
      <DrawerTitle :action="mode === 'create' ? t('common.new') : t('common.edit')" :title="t('geo.regione')" icon="pi pi-globe" />
    </template>
    <div class="app-drawer-content">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('geo.col_descrizione') }} *</label>
          <InputText v-model="form.descrizione" />
        </div>
        <div class="form-field">
          <label>{{ t('geo.col_stato') }}</label>
          <Select v-model="form.stato_id" :options="statiLookup.items.value"
            option-label="descrizione" option-value="id"
            :placeholder="t('geo.select_stato')" :loading="statiLookup.loading.value" filter />
        </div>
      </div>
      <DrawerFooter :loading="loading" :disabled="!form.descrizione.trim()"
        @save="handleSave" @cancel="emit('update:visible', false)" />
    </div>
  </Drawer>
</template>
