<script setup>
// Scopo: Select standard per modi di arrotondamento UoM operativa.
// Sostituisce il `roundingOptions` hardcoded nei drawer catalogo.
// I 5 codici (HALF_UP, HALF_DOWN, HALF_EVEN, UP, DOWN) sono enum tecnici fissi
// (single source of truth: BE catalogo_service._ROUNDING_MODE_VALIDI).
//
// Thin wrapper su LookupSelect (B5 2026-06-05, regola del 2).
//
// Uso:
//   <RoundingModeSelect v-model="form.rounding_mode" />
import { useI18n } from 'vue-i18n'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { lookupUomRoundingModes } from '../api/catalogo'

defineProps({
  modelValue: { type: [String, null], default: null },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  showClear: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])
const { t } = useI18n()
</script>

<template>
  <LookupSelect
    :model-value="modelValue"
    :fetcher="lookupUomRoundingModes"
    lookup-key="catalogo.uom_rounding_modes"
    :transform="(r) => r.data.data"
    value-field="codice"
    show-code
    :filter="false"
    :placeholder="placeholder || t('catalogo.select_rounding_mode')"
    :disabled="disabled"
    :show-clear="showClear"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @change="(v) => emit('change', v)"
  />
</template>
