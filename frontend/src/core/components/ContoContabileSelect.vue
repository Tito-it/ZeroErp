<script setup>
// Scopo: Select standard per conti contabili filtrati per tipo (A/V).
// Usa l'endpoint dedicato /core/lookup/conti-contabili/?tipo=A|V che espone
// tipo_conto (il lookup generico config.conti_contabili non lo esporrebbe).
// Mostra "descrizione (codice)" per leggibilita'.
//
// Uso:
//   <ContoContabileSelect v-model="form.conto_contabile_vendita_id" tipo="V" />
//   <ContoContabileSelect v-model="form.conto_contabile_acquisto_id" tipo="A" />
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLookup } from '../composables/useLookup'
import { lookupContiContabili } from '../apiCore'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [Number, null], default: null },
  // Tipo conto obbligatorio: 'A' (acquisto) o 'V' (vendita).
  tipo: {
    type: String,
    required: true,
    validator: (v) => ['A', 'V'].includes(v),
  },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  showClear: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'change'])

const { t } = useI18n()

// Carica conti filtrati per tipo. Ricarica se cambia (non dovrebbe succedere
// ma rende il componente resiliente a prop reattive).
const lookup = useLookup(
  () => lookupContiContabili(props.tipo),
  { immediate: true }
)

watch(() => props.tipo, () => {
  lookup.reload?.()
})

// Scopo: Formato display "descrizione (codice)" — codice contabile e' informativo.
function formatOption(item) {
  if (!item) return ''
  return item.codice ? `${item.descrizione} (${item.codice})` : item.descrizione
}

const selectedItem = computed(() =>
  lookup.items.value.find(i => i.id === props.modelValue) || null
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
    :options="lookup.items.value"
    :loading="lookup.loading.value"
    optionLabel="descrizione"
    optionValue="id"
    :placeholder="placeholder || t('common.select_conto')"
    :showClear="showClear"
    :filter="true"
    :disabled="disabled"
    @change="onChange"
  >
    <template #option="{ option }">
      {{ formatOption(option) }}
    </template>
    <template #value>
      <span v-if="selectedItem">{{ formatOption(selectedItem) }}</span>
      <span v-else class="text-color-secondary">{{ placeholder || t('common.select_conto') }}</span>
    </template>
  </Select>
</template>
