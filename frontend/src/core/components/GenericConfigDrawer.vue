<script setup>
// Scopo: drawer CRUD generico per tabelle config.
// Renderizza i campi dinamicamente dai metadata backend (information_schema).
// Gestisce: text, number, boolean, json. Esclude id e colonne audit.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useApiHandler } from '../composables/useApiHandler'
import { DRAWER_WIDTH } from '../constants'
import { NAV_ICONS } from '../navigation'
import DrawerFooter from './DrawerFooter.vue'
import DrawerTitle from './DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Textarea from 'primevue/textarea'
import api from '../api'

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  rel: { type: String, required: true },
  label: { type: String, default: '' },
  recordId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()

const columns = ref([])
const form = ref({})
const originalForm = ref({}) // Per calcolare delta in edit mode

// Colonne editabili (esclude id)
const editableColumns = computed(() => columns.value.filter(c => !c.is_pk))

// Carica metadata + dati al primo open
watch(() => props.visible, async (val) => {
  if (!val) return

  // Carica metadata se non gia' presenti per questa rel
  if (columns.value.length === 0) {
    try {
      const res = await api.get(`/core/config/tables/${props.rel}/metadata/`)
      columns.value = res.data.data.columns
    } catch {
      emit('update:visible', false)
      return
    }
  }

  // Reset form
  const newForm = {}
  for (const col of editableColumns.value) {
    if (col.type === 'boolean') newForm[col.name] = true
    else if (col.type === 'number') newForm[col.name] = null
    else newForm[col.name] = ''
  }

  // Se edit, carica dati esistenti
  if (props.mode === 'edit' && props.recordId) {
    try {
      const res = await api.get(`/core/config/tables/${props.rel}/${props.recordId}/`)
      const data = res.data.data
      for (const col of editableColumns.value) {
        if (data[col.name] !== undefined) {
          newForm[col.name] = col.type === 'json'
            ? JSON.stringify(data[col.name], null, 2)
            : data[col.name]
        }
      }
    } catch {
      emit('update:visible', false)
      return
    }
  }

  form.value = newForm
  originalForm.value = { ...newForm }
})

// Validazione minima: almeno descrizione non vuota (se presente)
const canSave = computed(() => {
  const desc = form.value.descrizione
  if (desc !== undefined && typeof desc === 'string') return desc.trim().length > 0
  return true
})

async function handleSave() {
  const payload = {}
  const isCreate = props.mode === 'create'

  for (const col of editableColumns.value) {
    let val = form.value[col.name]
    if (col.type === 'json' && typeof val === 'string') {
      try { val = JSON.parse(val) } catch { val = {} }
    }

    if (isCreate) {
      // Create: manda tutti i campi con valore
      if (val !== undefined && val !== '') payload[col.name] = val
      else if (col.type === 'boolean') payload[col.name] = val
    } else {
      // Edit: manda SOLO i campi modificati (delta)
      const orig = originalForm.value[col.name]
      if (col.type === 'json') {
        // Confronta come stringa JSON
        if (JSON.stringify(val) !== JSON.stringify(orig)) payload[col.name] = val
      } else if (val !== orig) {
        payload[col.name] = val
      }
    }
  }

  const msg = isCreate ? t('config_panel.record_creato') : t('config_panel.record_salvato')

  const result = await execute(
    () => isCreate
      ? api.post(`/core/config/tables/${props.rel}/`, payload)
      : api.patch(`/core/config/tables/${props.rel}/${props.recordId}/`, payload),
    { successMessage: msg }
  )

  if (result !== null) {
    emit('saved')
    emit('update:visible', false)
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
      <DrawerTitle :action="mode === 'create' ? t('common.new') : t('common.edit')" :title="label" :icon="NAV_ICONS.TABELLE" />
    </template>
    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <template v-for="col in editableColumns" :key="col.name">
          <!-- Text -->
          <div v-if="col.type === 'text'" class="form-field">
            <label>{{ col.name }} {{ !col.nullable ? '*' : '' }}</label>
            <InputText v-model="form[col.name]" />
          </div>

          <!-- Number -->
          <div v-else-if="col.type === 'number'" class="form-field">
            <label>{{ col.name }} {{ !col.nullable ? '*' : '' }}</label>
            <InputNumber v-model="form[col.name]" :use-grouping="false" />
          </div>

          <!-- Boolean -->
          <div v-else-if="col.type === 'boolean'" class="form-field">
            <label>{{ col.name }}</label>
            <ToggleSwitch v-model="form[col.name]" />
          </div>

          <!-- JSON -->
          <div v-else-if="col.type === 'json'" class="form-field">
            <label>{{ col.name }}</label>
            <Textarea v-model="form[col.name]" rows="4" auto-resize />
          </div>

          <!-- Date / other → text fallback -->
          <div v-else class="form-field">
            <label>{{ col.name }}</label>
            <InputText v-model="form[col.name]" />
          </div>
        </template>
      </div>

      <DrawerFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="emit('update:visible', false)"
      />
    </div>
  </Drawer>
</template>
