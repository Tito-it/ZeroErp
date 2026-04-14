<script setup>
// Scopo: Select standard per IVA. Wrapper su LookupSelect con show-code
// attivato per mostrare sia descrizione che codice aliquota.
// Usa l'endpoint generico /core/lookup/codici/?rel=config.iva.
// Da usare ovunque servano combo IVA per garantire display uniforme.
//
// Uso:
//   <IvaSelect v-model="form.iva_id" />
//   <IvaSelect v-model="form.iva_id" :placeholder="t('custom.placeholder')" />
import { useI18n } from 'vue-i18n'
import LookupSelect from './LookupSelect.vue'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  showClear: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'change'])

const { t } = useI18n()
</script>

<template>
  <LookupSelect
    :modelValue="modelValue"
    rel="config.iva"
    :placeholder="placeholder || t('common.select_iva')"
    :disabled="disabled"
    :show-clear="showClear"
    show-code
    @update:modelValue="v => emit('update:modelValue', v)"
    @change="v => emit('change', v)"
  />
</template>
