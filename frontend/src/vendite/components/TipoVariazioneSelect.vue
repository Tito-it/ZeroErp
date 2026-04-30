<script setup>
// Scopo: Select standard per tipo_variazione (PERCENTUALE / VALORE_FISSO /
//        PREZZO_FISSO). Sostituisce le costanti hardcoded `tipoVariazioneOptions`
//        in ContrattoDrawer e PromoArticoloDrawer (Fase 2 refactor frontend).
//
// La prop `scope` discrimina la whitelist da fetchare:
//   - 'contratto' -> /vendite/lookup/tipi-variazione-contratto/  (PERCENTUALE,VALORE_FISSO)
//   - 'promo'     -> /vendite/lookup/tipi-variazione-promo/      (+ PREZZO_FISSO)
// Single source of truth lato BE: vendite_lookups_service. Cache modulo-level
// via useGlobalLookup con chiavi distinte ('vendite.tipi_variazione.<scope>').
//
// Uso:
//   <TipoVariazioneSelect scope="contratto" v-model="form.tipo_variazione_globale" />
//   <TipoVariazioneSelect scope="promo"     v-model="form.tipo_variazione" />
import { computed } from 'vue'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import {
  lookupTipiVariazioneContratto,
  lookupTipiVariazionePromo,
} from '../api/lookup'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [String, null], default: null },
  scope: {
    type: String,
    required: true,
    validator: (v) => ['contratto', 'promo'].includes(v),
  },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  showClear: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

// Config per scope: chiave cache + fetcher.
const _CONFIG = {
  contratto: {
    key: 'vendite.tipi_variazione.contratto',
    fetch: lookupTipiVariazioneContratto,
  },
  promo: {
    key: 'vendite.tipi_variazione.promo',
    fetch: lookupTipiVariazionePromo,
  },
}

// useGlobalLookup non ammette il cambio runtime della chiave; il drawer
// chiamante usa scope fisso quindi la scelta in setup va bene.
const cfg = _CONFIG[props.scope]
const lookup = useGlobalLookup(cfg.key, cfg.fetch, {
  immediate: true,
  // Endpoint vendite/lookup/* ritorna lista nuda in `data` (no envelope paginato).
  transform: (r) => r.data.data,
})

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
