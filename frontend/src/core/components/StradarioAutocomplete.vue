<script setup>
// Scopo: Autocomplete stradario con ricerca server-side filtrata per comune.
// Mostra indirizzo_normalizzato, emette l'oggetto selezionato via v-model.

import { ref, computed } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import { searchStradario } from '../apiCore'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Object, default: null },
  comuneId: { type: Number, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])

const suggestions = ref([])
const loading = ref(false)

const placeholder = computed(() => t('common.select_via'))

async function onSearch({ query }) {
  if (!query || query.length < 2 || !props.comuneId) {
    suggestions.value = []
    return
  }
  loading.value = true
  try {
    const res = await searchStradario(props.comuneId, query)
    suggestions.value = res.data.data.results
  } finally {
    loading.value = false
  }
}

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
    @complete="onSearch"
    @item-select="onSelect"
    @clear="onClear"
  />
</template>
