<script setup>
// Scopo: Select standard per ambito contratto (COMMODITY / COMMERCIO).
// Sostituisce `ambitoOptions` cablato in ContrattoDrawer.
// Single source of truth: BE vendite_lookups_service._AMBITI_CONTRATTO.
//
// Uso:
//   <AmbitoContrattoSelect v-model="form.ambito" :disabled="..." />
import { computed } from 'vue'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { lookupAmbitiContratto } from '../api/lookup'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [String, null], default: null },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  showClear: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

const lookup = useGlobalLookup(
  'vendite.ambiti_contratto',
  lookupAmbitiContratto,
  { immediate: true, transform: (r) => r.data.data },
)

function formatOption(item) {
  if (!item) return ''
  return item.codice ? `${item.descrizione} (${item.codice})` : item.descrizione
}

const selectedItem = computed(() =>
  lookup.items.value.find((i) => i.codice === props.modelValue) || null,
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
    :options="lookup.items.value"
    :loading="lookup.loading.value"
    optionLabel="descrizione"
    optionValue="codice"
    :placeholder="placeholder"
    :showClear="showClear"
    :disabled="disabled"
    @change="onChange"
  >
    <template #option="{ option }">
      {{ formatOption(option) }}
    </template>
    <template #value>
      <span v-if="selectedItem">{{ formatOption(selectedItem) }}</span>
      <span v-else class="text-color-secondary">{{ placeholder }}</span>
    </template>
  </Select>
</template>
