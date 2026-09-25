<script setup>
// Scopo: Select standard per filtro stato email log (Fase 5).
// Sostituisce EMAIL_LOG_STATO + buildEmailLogStatoOptions hardcoded.
// I 5 codici (SENT, PENDING, RETRY, FAILED, SIMULATA) sono enum gestiti dal log writer
// EmailDispatchService. Single source of truth: BE
// `email_constants.STATI_EMAIL_LOG_DESCRIZIONI`, servito da /core/email/log/stati/.
// ⭐ In `core` dal 2026-09-26: lo usano il log dell'admin e quello
//    dell'operatore. Prima leggeva un lookup `/amm-software/`, che per un
//    operatore sarebbe stato un 403 dentro una schermata aperta.
//
// Thin wrapper su LookupSelect (B5 2026-06-05, regola del 2). Filtro tri-state:
// include sempre la voce 'Tutti' (modelValue=null) via `include-all-option`.
// Niente `show-code`: in lista si mostra solo la descrizione.
//
// Uso:
//   <EmailLogStatoSelect v-model="filtroStato" />
import { useI18n } from 'vue-i18n'
import LookupSelect from './LookupSelect.vue'
import { lookupEmailLogStati } from '../api/email'

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
    lookup-key="core.email_log_stati"
    value-field="codice"
    :filter="false"
    :include-all-option="includeAllOption"
    :all-label="t('core.email_log.stato_tutti')"
    :placeholder="placeholder || t('core.email_log.stato_tutti')"
    :disabled="disabled"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @change="(v) => emit('change', v)"
  />
</template>
