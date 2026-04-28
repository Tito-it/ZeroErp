<script setup>
// Scopo: Select standard per modi di arrotondamento UoM operativa.
// Sostituisce il `roundingOptions` hardcoded nei drawer catalogo.
// Usa l'endpoint dedicato /catalogo/lookup/rounding-modes/ con cache
// modulo-level (useGlobalLookup): primo consumer fa la fetch, i successivi
// riusano la stessa lista reattiva (stesso pattern adottato per LookupSelect).
//
// I 5 codici (HALF_UP, HALF_DOWN, HALF_EVEN, UP, DOWN) sono enum tecnici fissi
// (single source of truth: BE catalogo_service._ROUNDING_MODE_VALIDI).
//
// Uso:
//   <RoundingModeSelect v-model="form.rounding_mode" />
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { lookupUomRoundingModes } from '../api/catalogo'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [String, null], default: null },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  showClear: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

const { t } = useI18n()

// L'endpoint /catalogo/lookup/rounding-modes/ ritorna una lista nuda nel
// campo `data` (non l'envelope paginato `{count, results}`): il transform
// di default `r.data.data.results` non funzionerebbe.
// IMPORTANTE: se in futuro qualcuno migra il BE a `paginated_envelope` per
// uniformita', QUESTO transform va rimosso (default torna corretto). Senza
// quel cambio coordinato il componente smetterebbe di popolare `items`.
const lookup = useGlobalLookup(
  'catalogo.uom_rounding_modes',
  lookupUomRoundingModes,
  { immediate: true, transform: (r) => r.data.data },
)

// Display "descrizione (codice)": codice e' un'informazione tecnica utile
// (l'admin sa cosa significa HALF_EVEN), descrizione lo rende leggibile.
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
    :placeholder="placeholder || t('catalogo.select_rounding_mode')"
    :showClear="showClear"
    :disabled="disabled"
    @change="onChange"
  >
    <template #option="{ option }">
      {{ formatOption(option) }}
    </template>
    <template #value>
      <span v-if="selectedItem">{{ formatOption(selectedItem) }}</span>
      <span v-else class="text-color-secondary">
        {{ placeholder || t('catalogo.select_rounding_mode') }}
      </span>
    </template>
  </Select>
</template>
