<script setup>
// Scopo: Autocomplete stradario con ricerca server-side filtrata per comune.
// Mostra indirizzo_normalizzato, emette l'oggetto selezionato via v-model.

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

const { suggestions, loading, onSearch } = useServerAutocomplete(
  (query) => searchStradario(props.comuneId, query),
  { minLength: 2, debounceMs: 300 }
)

const placeholder = computed(() => t('common.select_via'))

function formatLabel(item) {
  if (!item) return ''
  return item.indirizzo_normalizzato || ''
}

function onSelect(event) {
  emit('update:modelValue', event.value ?? null)
}

function onClear() {
  emit('update:modelValue', null)
}
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
