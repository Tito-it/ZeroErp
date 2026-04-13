<script setup>
// Scopo: Drawer crea/modifica listino.
//        In edit: pulsanti per aprire drawer autonomi versioni e associazioni (eventi al parent).
//        Contenuto deferito a dopo l'animazione per evitare rimbalzi visivi.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useListiniStore } from '../stores/listini'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'

const { t } = useI18n()
const store = useListiniStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()


const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  listinoId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled', 'open-associazioni'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)

// Deferimento contenuto
const contentReady = ref(false)
function onAfterShow() { contentReady.value = true }

function defaultForm() {
  return { codice: '', descrizione: '', utility_id: null, attivo: true }
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
    utility_id: data.utility_id ?? null,
    attivo: data.attivo ?? true
  }
}

watch(() => props.visible, (v) => {
  if (!v) { contentReady.value = false; return }
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
  }
})

const canSave = computed(() => form.value.codice?.trim() && form.value.descrizione?.trim())

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {
      descrizione: f.descrizione?.trim() || '',
      utility_id: f.utility_id,
      attivo: f.attivo,
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
      utility_id: f.utility_id,
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
    position="right" :style="{ width: DRAWER_WIDTH.STANDARD }" :dismissable="true"
    @after-show="onAfterShow">
    <template #header>
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('listini.listino')" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_codice') }} *</label>
            <InputText v-model="form.codice" :disabled="isEdit" />
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_utility') }}</label>
            <UtilityPerRuoloSelect v-model="form.utility_id"
              :placeholder="t('listini.commercio')" :show-clear="true" />
          </div>
        </div>

        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('listini.field_descrizione') }} *</label>
            <InputText v-model="form.descrizione" />
          </div>
        </div>

        <div v-if="isEdit" class="form-grid">
          <div class="form-field">
            <label>{{ t('indirizzi.campo_attivo') }}</label>
            <ToggleSwitch v-model="form.attivo" />
          </div>
        </div>

        <!-- Pulsante associazioni (edit mode). Le versioni si gestiscono dall'expansion in lista. -->
        <template v-if="isEdit && detail">
          <div class="app-drawer-section"><h4>{{ t('listini.section_gestione') }}</h4></div>
          <div class="flex gap-2 mt-05">
            <Button :icon="MANAGE_ICONS.ASSOCIAZIONI" :label="t('listini.tab_associazioni')"
              text size="small" class="app-manage-btn"
              @click="emit('open-associazioni', detail)" />
          </div>
        </template>
      </template>

      <div v-else class="app-loading">
        <i class="pi pi-spin pi-spinner"></i>
      </div>

      <DrawerFooter v-if="contentReady" :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
