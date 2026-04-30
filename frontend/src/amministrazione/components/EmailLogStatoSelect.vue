<script setup>
// Scopo: Select standard per filtro stato email log (Fase 5).
// Sostituisce EMAIL_LOG_STATO + buildEmailLogStatoOptions hardcoded.
// Usa l'endpoint dedicato /amm-software/lookup/email-log-stati/ con cache
// modulo-level (useGlobalLookup): primo consumer fa la fetch, i successivi
// riusano stessa lista reattiva (stesso pattern di EmittenteRoundingModeSelect).
//
// I 4 codici (SENT, PENDING, RETRY, FAILED) sono enum gestiti dal log writer
// EmailDispatchService. Single source of truth: BE
// amm_software_service._EMAIL_LOG_STATI_VALIDI.
//
// Filtro tri-state: include sempre la voce 'tutti' (modelValue=null) per
// allineamento con buildEmailLogStatoOptions legacy. Il composable
// `injectAllOption` la prepend localmente al lookup BE.
//
// Uso:
//   <EmailLogStatoSelect v-model="filtroStato" />
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { lookupEmailLogStati } from '../api/amministrazione'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [String, null], default: null },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  // Se true: prepend voce 'Tutti' (value=null). Default true (uso filtro lista).
  includeAllOption: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'change'])

const { t } = useI18n()

// L'endpoint /amm-software/lookup/email-log-stati/ ritorna una lista nuda nel
// campo `data` (non envelope paginato): transform `(r) => r.data.data` evita
// il default `r.data.data.results`. Stesso comportamento documentato per
// EmittenteRoundingModeSelect.
const lookup = useGlobalLookup(
  'amm.email_log_stati',
  lookupEmailLogStati,
  { immediate: true, transform: (r) => r.data.data },
)

// Composizione options: 'Tutti' (opzionale) + i codici dal BE.
const options = computed(() => {
  const items = lookup.items.value
  if (!props.includeAllOption) return items
  return [
    { codice: null, descrizione: t('amm.email_stato_tutti') },
    ...items,
  ]
})

const selectedItem = computed(() =>
  options.value.find((i) => i.codice === props.modelValue) || null,
)

function onChange(event) {
  emit('update:modelValue', event.value)
  emit('change', event.value)
}
</script>

<template>
  <Select
    :modelValue="modelValue"
    @update:modelValue="(v) => emit('update:modelValue', v)"
    :options="options"
    :loading="lookup.loading.value"
    optionLabel="descrizione"
    optionValue="codice"
    :placeholder="placeholder || t('amm.email_stato_tutti')"
    :disabled="disabled"
    @change="onChange"
  >
    <template #value>
      <span v-if="selectedItem">{{ selectedItem.descrizione }}</span>
      <span v-else class="text-color-secondary">
        {{ placeholder || t('amm.email_stato_tutti') }}
      </span>
    </template>
  </Select>
</template>
