<script setup>
// Scopo: drawer CRUD per toponomastica (tipi strada).
// Riusabile da: tab Toponomastica, futuro gestione stradario.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useToponomasticaStore } from '../../anagrafiche/stores/toponomastica'
import { useApiHandler } from '../composables/useApiHandler'
import { DRAWER_WIDTH } from '../constants'
import DrawerFooter from './DrawerFooter.vue'
import DrawerTitle from './DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
  item: { type: Object, default: null }
})

const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const store = useToponomasticaStore()
const { execute, loading } = useApiHandler()

const form = ref({ descrizione: '', attivo: true })

watch(() => props.visible, (val) => {
  if (val) {
    if (props.mode === 'edit' && props.item) {
      form.value = { descrizione: props.item.descrizione || '', attivo: props.item.attivo ?? true }
    } else {
      form.value = { descrizione: '', attivo: true }
    }
  }
})

async function handleSave() {
  if (!form.value.descrizione.trim()) return

  const successMsg = props.mode === 'create'
    ? t('indirizzi.toponomastica_creata')
    : t('indirizzi.toponomastica_salvata')

  const result = await execute(
    () => props.mode === 'create'
      ? store.create({ descrizione: form.value.descrizione.trim() })
      : store.update(props.item.id, {
          descrizione: form.value.descrizione.trim(),
          attivo: form.value.attivo
        }),
    { successMessage: successMsg }
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
      <DrawerTitle :action="mode === 'create' ? t('common.new') : t('common.edit')" :title="t('indirizzi.toponomastica')" icon="pi pi-directions" />
    </template>
    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('indirizzi.campo_descrizione') }} *</label>
          <InputText v-model="form.descrizione" />
        </div>

        <div v-if="mode === 'edit'" class="form-field">
          <label>{{ t('indirizzi.campo_attivo') }}</label>
          <ToggleSwitch v-model="form.attivo" />
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
