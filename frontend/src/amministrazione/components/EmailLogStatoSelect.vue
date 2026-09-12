<script setup>
// Scopo: Select standard per filtro stato email log (Fase 5).
// Sostituisce EMAIL_LOG_STATO + buildEmailLogStatoOptions hardcoded.
// I 5 codici (SENT, PENDING, RETRY, FAILED, SIMULATA) sono enum gestiti dal log writer
// EmailDispatchService. Single source of truth: BE
// amm_software_service._EMAIL_LOG_STATI_VALIDI.
//
// Thin wrapper su LookupSelect (B5 2026-06-05, regola del 2). Filtro tri-state:
// include sempre la voce 'Tutti' (modelValue=null) via `include-all-option`.
// Niente `show-code`: in lista si mostra solo la descrizione.
//
// Uso:
//   <EmailLogStatoSelect v-model="filtroStato" />
import { useI18n } from 'vue-i18n'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { lookupEmailLogStati } from '../api/amministrazione'

defineProps({
  modelValue: { type: [String, null], default: null },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  // Se true: prepend voce 'Tutti' (value=null). Default true (uso filtro lista).
  includeAllOption: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'change'])
const { t } = useI18n()
</script>

<template>
  <LookupSelect
    :model-value="modelValue"
    :fetcher="lookupEmailLogStati"
    lookup-key="amm.email_log_stati"
    :transform="(r) => r.data.data"
    value-field="codice"
    :filter="false"
    :include-all-option="includeAllOption"
    :all-label="t('amministrazione.email_stato_tutti')"
    :placeholder="placeholder || t('amministrazione.email_stato_tutti')"
    :disabled="disabled"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @change="(v) => emit('change', v)"
  />
</template>
