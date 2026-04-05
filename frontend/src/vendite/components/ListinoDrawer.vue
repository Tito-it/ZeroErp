<script setup>
// Scopo: Drawer crea/modifica listino con tab versioni e associazioni in edit.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useListiniStore } from '../stores/listini'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import ListinoVersioniTab from './ListinoVersioniTab.vue'
import ListinoAssociazioniTab from './ListinoAssociazioniTab.vue'
import TestResolverDialog from './TestResolverDialog.vue'
import Drawer from 'primevue/drawer'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'

const { t } = useI18n()
const store = useListiniStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const dominioOptions = [
  { value: 'UTILITY', label: t('listini.dominio_utility') },
  { value: 'COMMERCIO', label: t('listini.dominio_commercio') }
]

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  listinoId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)
const resolverVisible = ref(false)

function defaultForm() {
  return { codice: '', descrizione: '', dominio: 'UTILITY' }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
}

async function loadDetail() {
  if (!props.listinoId) return
  const data = await store.fetchDetail(props.listinoId)
  if (!data) return
  detail.value = data
  form.value = {
    codice: data.codice || '',
    descrizione: data.descrizione || '',
    dominio: data.dominio || 'UTILITY'
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

const canSave = computed(() => form.value.codice?.trim() && form.value.descrizione?.trim() && form.value.dominio)

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {
      descrizione: f.descrizione?.trim() || '',
      dominio: f.dominio,
    }
    const result = await execute(
      () => store.update(props.listinoId, payload),
      { successMessage: t('listini.listino_salvato') }
    )
    if (result !== null) { emit('saved', result); close() }
  } else {
    const payload = {
      codice: f.codice?.trim(),
      descrizione: f.descrizione?.trim(),
      dominio: f.dominio,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('listini.listino_creato') }
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
    position="right" :style="{ width: DRAWER_WIDTH.COMPLEX }" :dismissable="true">
    <template #header>
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('listini.listino')" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('listini.field_codice') }}</label>
          <InputText v-model="form.codice" :disabled="isEdit" />
        </div>
        <div class="form-field">
          <label>{{ t('listini.field_dominio') }}</label>
          <Select v-model="form.dominio" :options="dominioOptions" option-label="label" option-value="value" />
        </div>
      </div>

      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('listini.field_descrizione') }}</label>
          <InputText v-model="form.descrizione" />
        </div>
      </div>

      <div v-if="isEdit && detail" style="display: flex; justify-content: flex-end; margin-top: 0.5rem;">
        <Button icon="pi pi-calculator" :label="t('listini.test_prezzo')" size="small"
          severity="info" @click="resolverVisible = true" />
      </div>

      <TabView v-if="isEdit && detail" lazy class="mt-1">
        <TabPanel :header="t('listini.tab_versioni')">
          <ListinoVersioniTab :listino-id="props.listinoId" />
        </TabPanel>
        <TabPanel :header="t('listini.tab_associazioni')">
          <ListinoAssociazioniTab :listino-id="props.listinoId" />
        </TabPanel>
      </TabView>

      <DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>

  <TestResolverDialog v-if="resolverVisible" :visible="resolverVisible"
    @update:visible="v => resolverVisible = v" />
</template>
