<script setup>
// Scopo: Select generico per tabelle lookup whitelisted (id, codice, descrizione).
// Usa l'endpoint /api/v1/core/lookup/codici/?rel=<schema.tabella> tramite lookupCodici.
// Riusabile ovunque serva un dropdown da tabella config/catalogo/vendite.
//
// Uso:
//   <LookupSelect v-model="form.iva_id" rel="config.iva" />
//   <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura" :label-field="'codice'" />
//   <LookupSelect v-model="form.conto_id" rel="config.conti_contabili" show-code />
import { computed } from 'vue'
import { useGlobalLookup } from '../composables/useGlobalLookup'
import { lookupCodici } from '../apiCore'
import Select from 'primevue/select'

const props = defineProps({
  // `null` non e' un costruttore valido in defineProps: tipi supportati
  // [Number, String] + default null copre il caso "nessun valore".
  modelValue: { type: [Number, String], default: null },
  rel: { type: String, required: true },
  placeholder: { type: String, default: '' },
  labelField: { type: String, default: 'descrizione' },
  valueField: { type: String, default: 'id' },
  // Se true, mostra "descrizione (codice)" sia nel display che nel dropdown.
  // Utile per tabelle con codice significativo (es. conti contabili).
  showCode: { type: Boolean, default: false },
  showClear: { type: Boolean, default: false },
  filter: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  filterField: { type: String, default: '' },
  filterValue: { type: [Number, String, Boolean], default: null },
  pageSize: { type: Number, default: 200 },
})

const emit = defineEmits(['update:modelValue', 'change'])

// Cache globale per-rel: tutte le istanze di LookupSelect con lo stesso rel
// condividono la stessa fetch (evita N chiamate duplicate nei form con
// piu' dropdown su tabelle config).
const lookup = useGlobalLookup(
  props.rel,
  () => lookupCodici(props.rel, { page_size: props.pageSize }),
  { immediate: true }
)

const visibleOptions = computed(() => {
  if (!props.filterField || props.filterValue == null) return lookup.items.value
  return lookup.items.value.filter(item => item?.[props.filterField] === props.filterValue)
})

// Scopo: Compone l'etichetta visualizzata per una riga del lookup.
// Se showCode e' true, ritorna "descrizione (codice)" — altrimenti
// usa solo labelField (di default "descrizione").
function formatOption(item) {
  if (!item) return ''
  const label = item[props.labelField] ?? ''
  if (props.showCode && item.codice) {
    return `${label} (${item.codice})`
  }
  return label
}

// Scopo: Trova la riga selezionata dal modelValue corrente (per lo slot #value).
const selectedItem = computed(() =>
  lookup.items.value.find(i => i[props.valueField] === props.modelValue) || null
)

function onChange(event) {
  emit('update:modelValue', event.value)
  emit('change', event.value)
}
</script>

<template>
  <Select
    :modelValue="modelValue"
    @update:modelValue="v => emit('update:modelValue', v)"
    :options="visibleOptions"
    :loading="lookup.loading.value"
    :optionLabel="labelField"
    :optionValue="valueField"
    :placeholder="placeholder"
    :showClear="showClear"
    :filter="filter"
    :disabled="disabled"
    @change="onChange"
  >
    <template v-if="showCode" #option="{ option }">
      {{ formatOption(option) }}
    </template>
    <template v-if="showCode" #value>
      <span v-if="selectedItem">{{ formatOption(selectedItem) }}</span>
      <span v-else class="text-color-secondary">{{ placeholder }}</span>
    </template>
  </Select>
</template>
