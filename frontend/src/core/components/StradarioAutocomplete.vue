<script setup>
// Scopo: Autocomplete stradario con ricerca server-side filtrata per comune.
// Mostra indirizzo_normalizzato, emette l'oggetto selezionato via v-model.
// Espone noResults per segnalare che la via digitata non esiste nello stradario.

import { computed } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import { searchStradario } from '../apiCore'
import { useServerAutocomplete } from '../composables/useServerAutocomplete'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Object, default: null },
  comuneId: { type: Number, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])

const { suggestions, loading, noResults, clearNoResults, onSearch } = useServerAutocomplete(
  (query) => searchStradario(props.comuneId, query),
  { minLength: 2, debounceMs: 300 }
)

const placeholder = computed(() => t('common.select_via'))

function formatLabel(item) {
  if (!item) return ''
  return item.indirizzo_normalizzato || ''
}

function onSelect(event) {
  clearNoResults()
  emit('update:modelValue', event.value ?? null)
}

function onClear() {
  clearNoResults()
  emit('update:modelValue', null)
}

defineExpose({ noResults })
</script>

<template>
  <AutoComplete
    :modelValue="modelValue"
    :suggestions="suggestions"
    :optionLabel="formatLabel"
    :placeholder="placeholder"
    :disabled="disabled || !comuneId"
    :loading="loading"
    forceSelection
    fluid
    @complete="onSearch"
    @item-select="onSelect"
    @clear="onClear"
  />
</template>
