<script setup>
// Scopo: drawer CRUD stati (nazioni).
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useStatiStore } from '../../anagrafiche/stores/stati'
import { useApiHandler } from '../composables/useApiHandler'
import { DRAWER_WIDTH } from '../constants'
import { NAV_ICONS } from '../navigation'
import DrawerFooter from './DrawerFooter.vue'
import DrawerTitle from './DrawerTitle.vue'
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
const store = useStatiStore()
const { execute, loading } = useApiHandler()

const form = ref({
  descrizione: '', codice_iso2: '', codice_iso3: '',
  sigla_stato: '', codice_telefonico: '', continente: ''
})

watch(() => props.visible, (val) => {
  if (val) {
    if (props.mode === 'edit' && props.item) {
      form.value = {
        descrizione: props.item.descrizione || '',
        codice_iso2: props.item.codice_iso2 || '',
        codice_iso3: props.item.codice_iso3 || '',
        sigla_stato: props.item.sigla_stato || '',
        codice_telefonico: props.item.codice_telefonico || '',
        continente: props.item.continente || ''
      }
    } else {
      form.value = { descrizione: '', codice_iso2: '', codice_iso3: '', sigla_stato: '', codice_telefonico: '', continente: '' }
    }
  }
})

async function handleSave() {
  if (!form.value.descrizione.trim()) return
  const msg = props.mode === 'create' ? t('geo.stato_creato') : t('geo.stato_salvato')
  const payload = {
    descrizione: form.value.descrizione.trim(),
    codice_iso2: form.value.codice_iso2.trim() || null,
    codice_iso3: form.value.codice_iso3.trim() || null,
    sigla_stato: form.value.sigla_stato.trim() || null,
    codice_telefonico: form.value.codice_telefonico.trim() || null,
    continente: form.value.continente.trim() || null
  }
  const result = await execute(
    () => props.mode === 'create' ? store.create(payload) : store.update(props.item.id, payload),
    { successMessage: msg }
  )
  if (result !== null) { emit('saved'); emit('update:visible', false); store.fetchList() }
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="emit('update:visible', $event)" position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }">
    <template #header>
      <DrawerTitle :action="mode === 'create' ? t('common.new') : t('common.edit')" :title="t('geo.stato')" :icon="NAV_ICONS.STATO" />
    </template>
    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('geo.col_descrizione') }} *</label>
          <InputText v-model="form.descrizione" />
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('geo.col_iso2') }}</label>
            <InputText v-model="form.codice_iso2" maxlength="2" />
          </div>
          <div class="form-field">
            <label>{{ t('geo.col_iso3') }}</label>
            <InputText v-model="form.codice_iso3" maxlength="3" />
          </div>
          <div class="form-field">
            <label>{{ t('geo.col_sigla') }}</label>
            <InputText v-model="form.sigla_stato" maxlength="10" />
          </div>
          <div class="form-field">
            <label>{{ t('geo.col_telefono') }}</label>
            <InputText v-model="form.codice_telefonico" maxlength="10" />
          </div>
        </div>
        <div class="form-field">
          <label>{{ t('geo.col_continente') }}</label>
          <InputText v-model="form.continente" />
        </div>
      </div>
      <DrawerFooter :loading="loading" :disabled="!form.descrizione.trim()"
        @save="handleSave" @cancel="emit('update:visible', false)" />
    </div>
  </Drawer>
</template>
