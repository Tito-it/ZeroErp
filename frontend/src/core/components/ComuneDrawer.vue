<script setup>
// Scopo: drawer per creazione comuni non censiti (esteri, frazioni).
// Riusabile da: tab Comuni, futuro gestione anagrafiche.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useComuniStore } from '../../anagrafiche/stores/comuni'
import { useApiHandler } from '../composables/useApiHandler'
import { useLookup } from '../composables/useLookup'
import { lookupProvince } from '../../anagrafiche/api/anagrafiche'
import { DRAWER_WIDTH } from '../constants'
import { NAV_ICONS } from '../navigation'
import DrawerFooter from './DrawerFooter.vue'
import DrawerTitle from './DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

const props = defineProps({
  visible: { type: Boolean, default: false }
})

const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const store = useComuniStore()
const { execute, loading } = useApiHandler()
const provinceLookup = useLookup(() => lookupProvince())

const form = ref({ descrizione: '', provincia_id: null })

watch(() => props.visible, (val) => {
  if (val) {
    form.value = { descrizione: '', provincia_id: null }
    if (!provinceLookup.loaded.value) {
      provinceLookup.load()
    }
  }
})

async function handleSave() {
  if (!form.value.descrizione.trim()) return

  const result = await execute(
    () => store.create({
      descrizione: form.value.descrizione.trim(),
      provincia_id: form.value.provincia_id
    }),
    { successMessage: t('indirizzi.comune_creato') }
  )

  if (result !== null) {
    emit('saved')
    emit('update:visible', false)
    store.fetchList()
  }
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.SIMPLE }"
  >
    <template #header>
      <DrawerTitle :action="t('common.new')" :title="t('indirizzi.comune')" :icon="NAV_ICONS.COMUNE" />
    </template>
    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('indirizzi.campo_descrizione') }} *</label>
          <InputText v-model="form.descrizione" />
        </div>

        <div class="form-field">
          <label>{{ t('indirizzi.campo_provincia') }}</label>
          <Select
            v-model="form.provincia_id"
            :options="provinceLookup.items.value"
            option-label="descrizione"
            option-value="id"
            :placeholder="t('indirizzi.select_provincia')"
            :loading="provinceLookup.loading.value"
            filter
          />
        </div>
      </div>

      <DrawerFooter
        :loading="loading"
        :disabled="!form.descrizione.trim()"
        @save="handleSave"
        @cancel="emit('update:visible', false)"
      />
    </div>
  </Drawer>
</template>
