<script setup>
// Scopo: Select riusabile per scegliere una utility configurata per l'emittente
// dell'utente corrente, filtrata per tipo ruolo soggetto (CL, FO, ecc.).
// Se tipoRuoloCodice non e' fornito, mostra tutte le utility EF dell'emittente.
//
// Uso:
//   <UtilityPerRuoloSelect v-model="form.utility_id" :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE" />
//   <UtilityPerRuoloSelect v-model="form.utility_id" />  <!-- tutte le utility EF emittente -->
//   <UtilityPerRuoloSelect v-model="filter.utility_id" apply-default />  <!-- filtri lista -->
//
// Backend: GET /api/v1/core/lookup/utilities-per-emittente/?ruolo=CL
// Filtra per: matrice utilities_tipi_ruolo + emittenti_fiscali_utilities per emittente utente.
import { ref, watch, onMounted } from 'vue'
import { lookupUtilitiesPerEmittente } from '../apiCore'
import { useUtilityDefaultId } from '../composables/useUtilityDefaultId'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  tipoRuoloCodice: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  showClear: { type: Boolean, default: false },
  filter: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  // optionLabel: 'descrizione' (default) o 'codice'
  labelField: { type: String, default: 'descrizione' },
  // Se true, al primo mount applica DEFAULT_UTILITY (parameter, catena
  // user→group→emittente→default sistema) come modelValue iniziale quando
  // il caller non ha gia' un valore. Usato dai filtri di lista per partire
  // pre-filtrati sull'utility tipica dell'operatore. I drawer non lo usano:
  // hanno gia' una propria orchestrazione di defaults via useUtilityDefaultId.
  applyDefault: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'change'])

const items = ref([])
const loading = ref(false)

const { id: defaultUtilityId, load: loadDefaultUtility } = useUtilityDefaultId({
  ruolo: props.tipoRuoloCodice || null
})

// Scopo: Carica le utility configurate per l'emittente dell'utente corrente.
// Se tipoRuoloCodice e' valorizzato, filtra per intersezione ruolo + EF.
async function load() {
  loading.value = true
  try {
    const res = await lookupUtilitiesPerEmittente(props.tipoRuoloCodice || undefined)
    items.value = res.data?.data?.results || []
  } catch (e) {
    items.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.tipoRuoloCodice, load, { immediate: true })

// Auto-applica il default solo al primo mount e solo se il caller non ha
// gia' un valore. Emette anche `change` per innescare l'eventuale handler
// di filtro (onUtilityChange → applyFilters) nelle search table.
onMounted(async () => {
  if (!props.applyDefault) return
  if (props.modelValue != null) return
  await loadDefaultUtility()
  if (props.modelValue == null && defaultUtilityId.value != null) {
    emit('update:modelValue', defaultUtilityId.value)
    emit('change', defaultUtilityId.value)
  }
})

function onChange(event) {
  emit('update:modelValue', event.value)
  emit('change', event.value)
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
    :placeholder="placeholder"
    :showClear="showClear"
    :filter="filter"
    :disabled="disabled"
    @change="onChange"
  />
</template>
