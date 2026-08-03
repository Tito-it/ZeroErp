<script setup>
// Scopo: Campo emittente fiscale auto-adattivo. Sempre rendering `<Select>`,
//        con opzioni e abilitazione contestuali al modo:
//
//         - edit:                     opzione singola sintetizzata dal record
//                                     (`emittente_fiscale_id/codice/descrizione`
//                                     denormalizzati dal BE detail). Disabled.
//         - create + admin globale:   opzioni dal lookup admin (cache modulo
//                                     via useGlobalLookup). Editabile.
//         - create + operatore:       opzione singola sintetizzata da
//                                     `auth.emittenteCorrente` (modello 1-a-1).
//                                     Disabled.
//
//        Beneficio rispetto al doppio rendering (InputText vs Select) usato
//        in passato: il display passa sempre da `formatEmittenteOptionLabel`,
//        single source di formattazione (`<ragione_sociale> (<codice>)`),
//        senza dipendere dal solo blob `auth.user.emittente.ragione_sociale_completa`
//        e senza branch di template duplicato.
//
//        Il componente NON applica autopopulate del modelValue: spetta
//        al consumer leggere `useEmittenteFiscaleField().defaultEmittenteId`
//        e impostarlo nel form prima del POST.
//
//        Modello permessi 1-a-1 documentato in stores/auth.js.

import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittenteFiscaleField } from '../composables/useEmittenteFiscaleField'
import Select from 'primevue/select'
import Message from 'primevue/message'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: [Number, null], default: null },
  // Record di dettaglio in edit (per leggere emittente_fiscale_codice e
  // emittente_ragione_sociale denormalizzati). Non usato in create.
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
  currentEmittente,
  emittentiOptions,
  emittentiLoading,
  emittentiError,
  loadOptions,
  formatEmittenteOptionLabel,
} = useEmittenteFiscaleField()

// L'admin globale puo' davvero scegliere: solo qui usiamo il lookup completo
// e abilitiamo la combo. Negli altri rami la combo resta disabled (display-only).
const useAdminLookup = computed(() => isAdminMode.value && !props.isEdit)

// Sintesi della singola option per i casi disabled (edit o operatore-mode).
// Riusa lo stesso shape del lookup admin (campi `id, codice, ragione_sociale`)
// cosi' il `formatEmittenteOptionLabel` produce display uniforme.
// La chiave `descrizione` e' stata tolta il 2026-08-02: era una copia dello
// stesso valore, tenuta in vita solo dal fallback del formatter — ora rimosso
// (`brief-emittente-ragione-sociale-dal-soggetto.md`). Il campo denormalizzato
// `emittente_ragione_sociale` porta gia' la ragione sociale del soggetto.
const recordAsOption = computed(() => {
  const r = props.record
  if (!r || r.emittente_fiscale_id == null) return null
  return {
    id: r.emittente_fiscale_id,
    codice: r.emittente_fiscale_codice ?? null,
    ragione_sociale: r.emittente_ragione_sociale ?? null,
  }
})

const operatoreAsOption = computed(() => {
  const ef = currentEmittente.value
  if (!ef || ef.id == null) return null
  return {
    id: ef.id,
    codice: ef.codice,
    ragione_sociale: ef.ragioneSociale,
  }
})

// Opzioni effettive renderizzate dal Select. In edit e operatore-mode e' un
// array di un solo elemento (sintetizzato sopra) che fa match col modelValue
// per visualizzare correttamente il label. In admin+create e' la lookup completa.
const finalOptions = computed(() => {
  if (props.isEdit) {
    return recordAsOption.value ? [recordAsOption.value] : []
  }
  if (useAdminLookup.value) {
    return emittentiOptions.value
  }
  return operatoreAsOption.value ? [operatoreAsOption.value] : []
})

// Combo modificabile solo per admin globale in CREATE. Operatore (1 solo EF) e
// qualsiasi EDIT (EF immutabile post-create) restano disabled.
const isFieldDisabled = computed(
  () => props.disabled || props.isEdit || !isAdminMode.value
)

const selectModel = computed({
  get: () => props.modelValue,
  set: v => emit('update:modelValue', v),
})

// Lazy load del lookup admin: parte solo nel ramo create+admin.
watch(
  useAdminLookup,
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
    <Select
      v-model="selectModel"
      :options="finalOptions"
      option-value="id"
      :option-label="formatEmittenteOptionLabel"
      :placeholder="t(placeholderI18nKey)"
      :loading="useAdminLookup && emittentiLoading"
      :disabled="isFieldDisabled"
      :filter="useAdminLookup"
      :show-clear="useAdminLookup"
      class="app-form-select"
      style="width: 100%; min-width: 0;"
    />
    <Message
      v-if="useAdminLookup && emittentiError"
      severity="error"
      :closable="false"
      class="mt-025"
    >
      {{ t(errorI18nKey) }}
    </Message>
  </div>
</template>
