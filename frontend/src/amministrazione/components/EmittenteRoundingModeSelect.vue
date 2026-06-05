<script setup>
// Scopo: Select standard per modi di arrotondamento emittente fiscale.
// Sostituisce ROUNDING_METHODS hardcoded (Fase 3 — A6).
// I 4 codici (HALF_UP, HALF_DOWN, UP, DOWN) sono allineati al CHECK
// chk_emittenti_fiscali_rounding_policy: NIENTE HALF_EVEN (a differenza
// di catalogo UoM operativa che ne ha 5).
// Single source of truth: BE amm_software_service._ROUNDING_MODE_VALIDI_EMITTENTE.
//
// Thin wrapper su LookupSelect (B5 2026-06-05, regola del 2).
//
// Uso:
//   <EmittenteRoundingModeSelect v-model="form.rounding_policy" />
import { useI18n } from 'vue-i18n'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { lookupEmittenteRoundingModes } from '../api/amministrazione'

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
    :fetcher="lookupEmittenteRoundingModes"
    lookup-key="amm.emittenti_rounding_modes"
    :transform="(r) => r.data.data"
    value-field="codice"
    show-code
    :filter="false"
    :placeholder="placeholder || t('amm.select_rounding_policy')"
    :disabled="disabled"
    :show-clear="showClear"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @change="(v) => emit('change', v)"
  />
</template>
