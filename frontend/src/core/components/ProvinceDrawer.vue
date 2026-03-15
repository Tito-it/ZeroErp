<script setup>
// Scopo: drawer CRUD province.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useProvinceStore } from '../../anagrafiche/stores/province'
import { useApiHandler } from '../composables/useApiHandler'
import { useLookup } from '../composables/useLookup'
import { lookupRegioni } from '../../anagrafiche/api/anagrafiche'
import { DRAWER_WIDTH } from '../constants'
import DrawerFooter from './DrawerFooter.vue'
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
const store = useProvinceStore()
const { execute, loading } = useApiHandler()
const regioniLookup = useLookup(() => lookupRegioni())

const form = ref({ descrizione: '', sigla: '', regione_id: null })

watch(() => props.visible, (val) => {
  if (val) {
    if (!regioniLookup.loaded.value) regioniLookup.load()
    if (props.mode === 'edit' && props.item) {
      form.value = {
        descrizione: (props.item.descrizione || '').trim(),
        sigla: (props.item.sigla || '').trim(),
        regione_id: props.item.regione_id
      }
    } else {
      form.value = { descrizione: '', sigla: '', regione_id: null }
    }
  }
})

async function handleSave() {
  if (!form.value.descrizione.trim() || !form.value.sigla.trim()) return
  const msg = props.mode === 'create' ? t('geo.provincia_creata') : t('geo.provincia_salvata')
  const result = await execute(
    () => props.mode === 'create'
      ? store.create({ descrizione: form.value.descrizione.trim(), sigla: form.value.sigla.trim(), regione_id: form.value.regione_id })
      : store.update(props.item.id, { descrizione: form.value.descrizione.trim(), sigla: form.value.sigla.trim(), regione_id: form.value.regione_id }),
    { successMessage: msg }
  )
  if (result !== null) { emit('saved'); emit('update:visible', false); store.fetchList() }
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="emit('update:visible', $event)" position="right"
    :style="{ width: DRAWER_WIDTH.SIMPLE }"
    :header="mode === 'create' ? t('geo.nuova_provincia') : t('geo.modifica_provincia')">
    <div class="app-drawer-content">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('geo.col_descrizione') }} *</label>
          <InputText v-model="form.descrizione" />
        </div>
        <div class="form-field">
          <label>{{ t('geo.col_sigla') }} *</label>
          <InputText v-model="form.sigla" maxlength="10" />
        </div>
        <div class="form-field">
          <label>{{ t('geo.col_regione') }}</label>
          <Select v-model="form.regione_id" :options="regioniLookup.items.value"
            option-label="descrizione" option-value="id"
            :placeholder="t('geo.select_regione')" :loading="regioniLookup.loading.value" filter />
        </div>
      </div>
      <DrawerFooter :loading="loading" :disabled="!form.descrizione.trim() || !form.sigla.trim()"
        @save="handleSave" @cancel="emit('update:visible', false)" />
    </div>
  </Drawer>
</template>
