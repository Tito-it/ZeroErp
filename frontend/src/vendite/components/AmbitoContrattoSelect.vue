<script setup>
// Scopo: Select standard per ambito contratto (COMMODITY / COMMERCIO).
// Sostituisce `ambitoOptions` cablato in ContrattoDrawer.
// Single source of truth: BE vendite_lookups_service._AMBITI_CONTRATTO.
//
// Thin wrapper su LookupSelect (B5 2026-06-05, regola del 2).
//
// Uso:
//   <AmbitoContrattoSelect v-model="form.ambito" :disabled="..." />
import LookupSelect from '../../core/components/LookupSelect.vue'
import { lookupAmbitiContratto } from '../api/lookup'

defineProps({
  modelValue: { type: [String, null], default: null },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  showClear: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])
</script>

<template>
  <LookupSelect
    :model-value="modelValue"
    :fetcher="lookupAmbitiContratto"
    lookup-key="vendite.ambiti_contratto"
    :transform="(r) => r.data.data"
    value-field="codice"
    show-code
    :filter="false"
    :placeholder="placeholder"
    :disabled="disabled"
    :show-clear="showClear"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @change="(v) => emit('change', v)"
  />
</template>
