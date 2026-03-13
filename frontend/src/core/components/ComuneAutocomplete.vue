<script setup>
// Scopo: Autocomplete comuni con ricerca server-side.
// Mostra descrizione + sigla provincia, emette l'id via v-model.

import { ref, computed } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import { searchComuni } from '../apiCore'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Number, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])

const suggestions = ref([])
const selected = ref(null)
const loading = ref(false)

const placeholder = computed(() => t('common.select_comune'))

function formatLabel(item) {
  if (!item) return ''
  return item.provincia_sigla
    ? `${item.descrizione} (${item.provincia_sigla})`
    : item.descrizione
}

async function onSearch({ query }) {
  if (!query || query.length < 2) {
    suggestions.value = []
    return
  }
  loading.value = true
  try {
    const res = await searchComuni(query)
    suggestions.value = res.data.data.results
  } finally {
    loading.value = false
  }
}

function onSelect(event) {
  selected.value = event.value
  emit('update:modelValue', event.value?.id ?? null)
}

function onClear() {
  selected.value = null
  emit('update:modelValue', null)
}
</script>

<template>
  <AutoComplete
    :modelValue="selected"
    :suggestions="suggestions"
    :optionLabel="formatLabel"
    :placeholder="placeholder"
    :disabled="disabled"
    :loading="loading"
    forceSelection
    @complete="onSearch"
    @item-select="onSelect"
    @clear="onClear"
  />
</template>
