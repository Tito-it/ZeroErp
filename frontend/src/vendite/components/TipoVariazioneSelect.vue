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
// Thin wrapper su LookupSelect (B5 2026-06-05, regola del 2): binding di dominio
// (fetcher + chiave per scope), logica/render delegati al BB core.
//
// Uso:
//   <TipoVariazioneSelect scope="contratto" v-model="form.tipo_variazione_globale" />
//   <TipoVariazioneSelect scope="promo"     v-model="form.tipo_variazione" />
import LookupSelect from '../../core/components/LookupSelect.vue'
import {
  lookupTipiVariazioneContratto,
  lookupTipiVariazionePromo,
} from '../api/lookup'

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

// Config per scope: chiave cache + fetcher. useGlobalLookup non ammette il
// cambio runtime della chiave; il drawer chiamante usa scope fisso.
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
const cfg = _CONFIG[props.scope]
</script>

<template>
  <LookupSelect
    class="app-form-select"
    :model-value="modelValue"
    :fetcher="cfg.fetch"
    :lookup-key="cfg.key"
    :transform="(r) => r.data.data"
    value-field="codice"
    show-code
    :filter="false"
    :placeholder="placeholder"
    :disabled="disabled"
    :show-clear="showClear"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @change="(v) => emit('change', v)"
  />
</template>
