<script setup>
// Scopo: Autocomplete su stradario_generale (senza comune/CAP) per via nuova.
// L'utente cerca una via in tutta Italia, poi sceglie comune e CAP separatamente.
// Emette l'oggetto selezionato via v-model: { stradario_generale_id, toponomastica_id, toponimo, denominazione, indirizzo_normalizzato }

import { computed } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import { searchStradarioGenerale } from '../apiCore'
import { useServerAutocomplete } from '../composables/useServerAutocomplete'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Object, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])

const { suggestions, loading, onSearch } = useServerAutocomplete(
  (query) => searchStradarioGenerale(query),
  { minLength: 2, debounceMs: 300 }
)

const placeholder = computed(() => t('common.select_via'))

function formatLabel(item) {
  if (!item) return ''
  // Mostra TOPONIMO + DENOMINAZIONE (es. "VIA ROMA")
  return item.toponimo && item.denominazione
    ? `${item.toponimo} ${item.denominazione}`
    : item.indirizzo_normalizzato || ''
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
    :disabled="disabled"
    :loading="loading"
    forceSelection
    fluid
    @complete="onSearch"
    @item-select="onSelect"
    @clear="onClear"
  />
</template>
