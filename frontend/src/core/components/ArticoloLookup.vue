<script setup>
// Scopo: Autocomplete articolo server-side riutilizzabile cross-dominio.
// Usato da: righe ordine, righe preventivo, righe listino, righe fattura.
import { useI18n } from 'vue-i18n'
import { useServerAutocomplete } from '../composables/useServerAutocomplete'
import { lookupArticoli } from '../../catalogo/api/catalogo'
import AutoComplete from 'primevue/autocomplete'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Object, default: null },
  voceUtility: { type: Boolean, default: undefined },
  soloAttivi: { type: Boolean, default: true },
  placeholder: { type: String, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'select'])

const ac = useServerAutocomplete(async (query) => {
  const params = { search: query, attivo: props.soloAttivi, limit: 20 }
  if (props.voceUtility !== undefined) params.voce_utility = props.voceUtility
  const res = await lookupArticoli(params)
  return (res.data.data.results ?? res.data.data ?? []).map(r => ({
    ...r,
    _display: `${r.codice} — ${r.descrizione}`
  }))
})

function onSelect(event) {
  emit('update:modelValue', event.value)
  emit('select', event.value)
}

function onClear() {
  emit('update:modelValue', null)
}
</script>

<template>
  <AutoComplete
    :modelValue="modelValue"
    :suggestions="ac.suggestions.value"
    @complete="ac.search"
    @item-select="onSelect"
    @clear="onClear"
    field="_display"
    :placeholder="placeholder || t('catalogo.search_placeholder')"
    :disabled="disabled"
    dropdown
  />
</template>
