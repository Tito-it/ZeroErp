<script setup>
// Scopo: Select tipologia listino filtrato per utility. Si aggiorna
// automaticamente al cambio della prop utilityId richiamando l'endpoint
// /vendite/listini/tipologie-per-utility/?utility_id=X. Se utilityId e'
// null o non positivo, il Select e' disabilitato e vuoto.
//
// Uso:
//   <TipologiaListinoSelect v-model="form.tipologia_id" :utility-id="form.utility_id" />
//
// Il componente e' autonomo: non conosce il form, emette solo update:modelValue
// e change. Il reset della selezione al cambio utility e' responsabilita' del
// parent (il componente NON azzera automaticamente il valore per evitare loop
// reattivi — il parent sa se sta pre-caricando uno stato esistente).
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listTipologiePerUtility } from '../api/listini'
import Select from 'primevue/select'

const { t } = useI18n()

const props = defineProps({
  // modelValue: id tipologia selezionata. null quando non valorizzata.
  modelValue: { type: [Number, String], default: null },
  // utilityId: id utility che filtra la matrice. null/0 → Select disabilitato.
  utilityId: { type: [Number, String], default: null },
  placeholder: { type: String, default: '' },
  showClear: { type: Boolean, default: false },
  filter: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  labelField: { type: String, default: 'descrizione' }
})

const emit = defineEmits(['update:modelValue', 'change'])

const items = ref([])
const loading = ref(false)

// Scopo: Carica le tipologie ammesse per la utility corrente.
// Se utilityId non e' valorizzato o non positivo, azzera la lista e skippa.
async function load() {
  const uid = Number(props.utilityId)
  if (!uid || uid <= 0) {
    items.value = []
    return
  }
  loading.value = true
  try {
    const res = await listTipologiePerUtility(uid)
    items.value = res.data?.data?.results || []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

// Watch su utilityId: la guardia interna di load() copre il caso utilityId
// iniziale null, quindi immediate e' sicuro.
watch(() => props.utilityId, load, { immediate: true })

// Scopo: Emette solo 'change' (l'update:modelValue e' gia' propagato da v-model
// del Select tramite @update:modelValue nel template). Evita il doppio emit.
function onChange(event) {
  emit('change', event.value)
}

// Scopo: placeholder dinamico.
//   - senza utilityId: guida l'utente ("Seleziona prima l'utility"),
//     altrimenti il Select disabilitato sembra un campo protetto
//   - durante il fetch: "Caricamento..." per evitare flash di "vuoto" in edit
//   - altrimenti: placeholder custom o default
function resolvedPlaceholder() {
  const uid = Number(props.utilityId)
  if (!uid || uid <= 0) return t('listini.tipologia_utility_first')
  if (loading.value) return t('common.loading')
  return props.placeholder || t('listini.tipologia_placeholder')
}
</script>

<template>
  <Select
    :modelValue="modelValue"
    @update:modelValue="v => emit('update:modelValue', v)"
    :options="items"
    :loading="loading"
    :optionLabel="labelField"
    optionValue="id"
    :placeholder="resolvedPlaceholder()"
    :showClear="showClear"
    :filter="filter"
    :disabled="disabled || !utilityId || loading"
    @change="onChange"
  />
</template>
