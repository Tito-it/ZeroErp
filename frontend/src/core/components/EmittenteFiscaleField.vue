<script setup>
// Scopo: Campo emittente fiscale auto-adattivo. Tre rami di rendering
//        scelti automaticamente:
//         - edit:               testo read-only (codice + descrizione
//                               dal record denormalizzato);
//         - create + admin globale: Select dal lookup admin (lazy load
//                                   modulo-level, dedotto da useGlobalLookup);
//         - create + operatore: testo read-only con emittente del profilo.
//
//        Il componente NON applica autopopulate del modelValue: spetta
//        al consumer leggere `useEmittenteFiscaleField().defaultEmittenteId`
//        e impostarlo nel form prima del POST. Questa separazione tiene
//        il componente "stupido" (presentazione) e lascia al drawer il
//        controllo di quando/come popolare il form (es. emptyForm in
//        watch su props.visible).
//
//        Modello permessi 1-a-1 documentato in stores/auth.js.

import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittenteFiscaleField } from '../composables/useEmittenteFiscaleField'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Message from 'primevue/message'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: [Number, null], default: null },
  // Record di dettaglio in edit (per leggere emittente_fiscale_codice e
  // emittente_fiscale_descrizione denormalizzati). Non usato in create.
  record: { type: Object, default: null },
  isEdit: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  // I18n keys overridable per riuso fuori dal contesto documenti.
  noneI18nKey: {
    type: String,
    default: 'config.modelli_documenti.field_emittente_none',
  },
  placeholderI18nKey: {
    type: String,
    default: 'config.modelli_documenti.field_emittente_placeholder',
  },
  errorI18nKey: { type: String, default: 'errors.lookup_load_failed' },
})
const emit = defineEmits(['update:modelValue'])

const {
  isAdminMode,
  currentEmittenteDisplay,
  emittentiOptions,
  emittentiLoading,
  emittentiError,
  loadOptions,
  formatEmittenteOptionLabel,
  formatEmittenteFromRecord,
} = useEmittenteFiscaleField()

// Mostra Select solo nel ramo create + admin globale.
const showSelect = computed(() => !props.isEdit && isAdminMode.value)

// Display read-only: in edit usa il record denormalizzato; altrimenti
// l'emittente del profilo. Em-dash come ultimo fallback se entrambi
// mancano (caso difensivo: non dovrebbe accadere col BE attuale).
const displayValue = computed(() => {
  if (props.isEdit) {
    return formatEmittenteFromRecord(props.record) || '—'
  }
  return currentEmittenteDisplay.value || t(props.noneI18nKey)
})

const selectModel = computed({
  get: () => props.modelValue,
  set: v => emit('update:modelValue', v),
})

// Lazy load: parte solo quando il Select e' davvero da renderizzare.
// useGlobalLookup e' idempotente (cache modulo-level), quindi e' sicuro
// chiamare ad ogni transizione false->true.
watch(
  showSelect,
  value => {
    if (value) {
      loadOptions().catch(() => { /* errore visibile via emittentiError */ })
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="emittente-fiscale-field">
    <InputText
      v-if="!showSelect"
      :model-value="displayValue"
      disabled
    />
    <Select
      v-else
      v-model="selectModel"
      :options="emittentiOptions"
      option-value="id"
      :option-label="formatEmittenteOptionLabel"
      :placeholder="t(placeholderI18nKey)"
      :loading="emittentiLoading"
      :disabled="disabled"
      filter
      show-clear
    />
    <Message
      v-if="showSelect && emittentiError"
      severity="error"
      :closable="false"
      class="mt-025"
    >
      {{ t(errorI18nKey) }}
    </Message>
  </div>
</template>
