<script setup>
// Scopo: Select standard per modi di arrotondamento emittente fiscale.
// Sostituisce ROUNDING_METHODS hardcoded (Fase 3 — A6).
// Usa l'endpoint dedicato /amm-software/lookup/rounding-modes/ con cache
// modulo-level (useGlobalLookup): primo consumer fa la fetch, i successivi
// riusano stessa lista reattiva (stesso pattern di RoundingModeSelect catalogo).
//
// I 4 codici (HALF_UP, HALF_DOWN, UP, DOWN) sono allineati al CHECK
// chk_emittenti_fiscali_rounding_policy: NIENTE HALF_EVEN (a differenza
// di catalogo UoM operativa che ne ha 5).
// Single source of truth: BE amm_software_service._ROUNDING_MODE_VALIDI_EMITTENTE.
//
// Uso:
//   <EmittenteRoundingModeSelect v-model="form.rounding_policy" />
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { lookupEmittenteRoundingModes } from '../api/amministrazione'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [String, null], default: null },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  showClear: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

const { t } = useI18n()

// L'endpoint /amm-software/lookup/rounding-modes/ ritorna una lista nuda nel
// campo `data` (non l'envelope paginato `{count, results}`): il transform
// di default `r.data.data.results` non funzionerebbe.
// IMPORTANTE: se in futuro qualcuno migra il BE a `paginated_envelope` per
// uniformita', QUESTO transform va rimosso (default torna corretto). Senza
// quel cambio coordinato il componente smetterebbe di popolare `items`.
const lookup = useGlobalLookup(
  'amm.emittenti_rounding_modes',
  lookupEmittenteRoundingModes,
  { immediate: true, transform: (r) => r.data.data },
)

// Display "descrizione (codice)": codice e' un'informazione tecnica utile
// (l'admin sa cosa significa HALF_UP), descrizione lo rende leggibile.
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
    :placeholder="placeholder || t('amm.select_rounding_policy')"
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
        {{ placeholder || t('amm.select_rounding_policy') }}
      </span>
    </template>
  </Select>
</template>
