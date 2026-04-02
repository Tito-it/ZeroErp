<script setup>
// Scopo: Select generico per tabelle lookup whitelisted (id, codice, descrizione).
// Usa l'endpoint /api/v1/core/lookup/codici/?rel=<schema.tabella> tramite lookupCodici.
// Riusabile ovunque serva un dropdown da tabella config/catalogo/vendite.
//
// Uso:
//   <LookupSelect v-model="form.iva_id" rel="config.iva" />
//   <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura" :label-field="'codice'" />
//   <LookupSelect v-model="form.tipo_voce_id" rel="vendite.articoli_tipologie" show-clear />
import { useLookup } from '../composables/useLookup'
import { lookupCodici } from '../apiCore'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  rel: { type: String, required: true },
  placeholder: { type: String, default: '' },
  labelField: { type: String, default: 'descrizione' },
  valueField: { type: String, default: 'id' },
  showClear: { type: Boolean, default: false },
  filter: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

const lookup = useLookup(() => lookupCodici(props.rel), { immediate: true })

function onChange(event) {
  emit('update:modelValue', event.value)
  emit('change', event.value)
}
</script>

<template>
  <Select
    :modelValue="modelValue"
    @update:modelValue="v => emit('update:modelValue', v)"
    :options="lookup.items.value"
    :loading="lookup.loading.value"
    :optionLabel="labelField"
    :optionValue="valueField"
    :placeholder="placeholder"
    :showClear="showClear"
    :filter="filter"
    :disabled="disabled"
    @change="onChange"
  />
</template>
