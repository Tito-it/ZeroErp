<script setup>
// Scopo: renderer di UN campo per EntityFormDrawer (estrazione regola del 2,
//        2026-06-05). Tipi supportati: text, select (FK via useLookup),
//        autocomplete (componente custom es. ComuneAutocomplete), toggle.
//        Tenuto separato dal drawer cosi' lo stesso renderer serve sia i campi
//        top-level sia quelli dentro un gruppo (form-grid-2col) senza duplicare
//        il template per-tipo.
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'

defineProps({
  field: { type: Object, required: true },
  modelValue: { default: null },
  mode: { type: String, default: 'create' },
  // Risultato di useLookup(field.lookupFn) per i campi 'select' (items/loading).
  lookup: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

function upd(v) {
  emit('update:modelValue', v)
}
</script>

<template>
  <div class="form-field">
    <label>{{ t(field.labelKey) }}{{ field.required ? ' *' : '' }}</label>

    <InputText
      v-if="field.type === 'text'"
      :model-value="modelValue"
      :maxlength="field.maxlength"
      @update:model-value="upd"
    />

    <Select
      v-else-if="field.type === 'select'"
      :model-value="modelValue"
      :options="lookup ? lookup.items.value : []"
      :option-label="field.optionLabel || 'descrizione'"
      :option-value="field.optionValue || 'id'"
      :placeholder="field.placeholderKey ? t(field.placeholderKey) : ''"
      :loading="lookup ? lookup.loading.value : false"
      filter
      @update:model-value="upd"
    />

    <component
      :is="field.component"
      v-else-if="field.type === 'autocomplete'"
      :model-value="modelValue"
      :disabled="field.disabledInEdit && mode === 'edit'"
      @update:model-value="upd"
    />

    <ToggleSwitch
      v-else-if="field.type === 'toggle'"
      :model-value="modelValue"
      @update:model-value="upd"
    />
  </div>
</template>
