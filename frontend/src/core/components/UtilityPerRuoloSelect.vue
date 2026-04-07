<script setup>
// Scopo: Select riusabile per scegliere una utility ammessa per un dato tipo ruolo.
// Filtraggio strict lato backend tramite config.utilities_tipi_ruolo: l'utente
// vede solo utility configurate per il ruolo (EF, FO, CL, ...).
//
// Uso:
//   <UtilityPerRuoloSelect v-model="form.utility_id" :tipo-ruolo-codice="TIPO_RUOLO.EMITTENTE_FISCALE" />
//   <UtilityPerRuoloSelect v-model="form.utility_id" tipo-ruolo-codice="FO" :placeholder="t(...)" />
//
// Equivalente a LookupSelect ma per il caso specifico utility-per-ruolo,
// dove il filtro NON e' supportato dall'endpoint generico /lookup/codici/.
import { ref, watch } from 'vue'
import { lookupUtilitiesPerRuolo } from '../apiCore'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  tipoRuoloCodice: { type: String, required: true },
  placeholder: { type: String, default: '' },
  showClear: { type: Boolean, default: false },
  filter: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  // optionLabel: 'descrizione' (default) o 'codice'
  labelField: { type: String, default: 'descrizione' }
})

const emit = defineEmits(['update:modelValue', 'change'])

const items = ref([])
const loading = ref(false)

// Scopo: Carica le utility ammesse per il tipo_ruolo corrente. Reagisce al cambio
// di tipoRuoloCodice (es. uno stesso form che cambia ruolo target dinamicamente).
async function load() {
  if (!props.tipoRuoloCodice) {
    items.value = []
    return
  }
  loading.value = true
  try {
    const res = await lookupUtilitiesPerRuolo(props.tipoRuoloCodice)
    items.value = res.data?.data?.results || []
  } catch (e) {
    items.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.tipoRuoloCodice, load, { immediate: true })

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
