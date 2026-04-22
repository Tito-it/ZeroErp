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
  soloComponenti: { type: Boolean, default: undefined },
  soloAttivi: { type: Boolean, default: true },
  placeholder: { type: String, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'select'])

const ac = useServerAutocomplete(async (query) => {
  const params = { search: query, attivo: props.soloAttivi, limit: 20 }
  if (props.soloComponenti !== undefined) params.is_solo_componente = props.soloComponenti
  return await lookupArticoli(params)
}, {
  minLength: 3,
  transform: (res) => (res.data.data.results ?? res.data.data ?? []).map(r => ({
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
    @complete="ac.onSearch"
    @item-select="onSelect"
    @clear="onClear"
    optionLabel="_display"
    :placeholder="placeholder || t('catalogo.search_placeholder')"
    :disabled="disabled"
    dropdown
  />
</template>
