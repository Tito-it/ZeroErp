<script setup>
// Scopo: Autocomplete articolo server-side riutilizzabile cross-dominio.
// Usato da: righe ordine, righe preventivo, righe listino, righe fattura,
//           BoM componente, lookup test resolver.
//
// Filtri contestuali: la prop `filtri` permette al caller di restringere
// il dominio dei risultati in base al contesto. Shape:
//
//   {
//     soloComponenti?: 'qualsiasi' | 'escludi' | 'solo',
//     compositi?:      'qualsiasi' | 'escludi' | 'solo',
//   }
//
// Mappa FE → BE:
//   'qualsiasi' o assente → nessun parametro inviato
//   'escludi'             → is_solo_componente=false / is_composito=false
//   'solo'                → is_solo_componente=true  / is_composito=true
//
// Valori sconosciuti → warn console + fallback a 'qualsiasi'.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServerAutocomplete } from '../composables/useServerAutocomplete'
import { useLookupDisplayModel } from '../composables/useLookupDisplayModel'
import { lookupArticoli } from '../../catalogo/api/catalogo'
import AutoComplete from 'primevue/autocomplete'

const { t } = useI18n()

// Mappa dichiarativa dei filtri ammessi: chiave (camelCase, lato FE) →
// nome parametro query lato BE. Aggiungere qui per estendere a nuovi
// filtri tri-stato (vedi piano `piano-filtri-articolo-lookup.md` §5).
const FILTRI_TRI_STATO = Object.freeze({
  soloComponenti: 'is_solo_componente',
  compositi:      'is_composito',
})
const FILTRO_VALORI_VALIDI = Object.freeze(['qualsiasi', 'escludi', 'solo'])

const props = defineProps({
  modelValue: { type: Object, default: null },
  filtri: { type: Object, default: () => ({}) },
  soloAttivi: { type: Boolean, default: true },
  placeholder: { type: String, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'select'])

// Scopo: validazione one-shot di `props.filtri`. Computed → riesegue
// solo al cambio della prop, non a ogni keystroke (no log-spam su valori
// sconosciuti). Emette warn per:
//   - chiavi sconosciute (non in `FILTRI_TRI_STATO`)
//   - valori non in `FILTRO_VALORI_VALIDI`
// Ritorna un map { chiaveFE → valore enum normalizzato } che esclude
// `'qualsiasi'`, valori invalidi e chiavi sconosciute.
const filtriValidati = computed(() => {
  const out = {}
  const raw = props.filtri || {}
  for (const [chiave, valore] of Object.entries(raw)) {
    if (!(chiave in FILTRI_TRI_STATO)) {
      console.warn(
        `[ArticoloLookup] chiave sconosciuta in filtri: '${chiave}'. `
        + `Ammesse: ${Object.keys(FILTRI_TRI_STATO).join(', ')}.`,
      )
      continue
    }
    if (valore === undefined || valore === null || valore === 'qualsiasi') {
      continue
    }
    if (!FILTRO_VALORI_VALIDI.includes(valore)) {
      console.warn(
        `[ArticoloLookup] valore non valido per filtri.${chiave}: `
        + `${JSON.stringify(valore)}. Atteso: ${FILTRO_VALORI_VALIDI.join('|')}.`,
      )
      continue
    }
    out[chiave] = valore
  }
  return out
})

// Scopo: costruisce i query params per lookupArticoli a partire dalla
// query testuale + filtri normalizzati. 'escludi' → false, 'solo' → true.
function _buildLookupParams(query) {
  const params = { search: query, attivo: props.soloAttivi, limit: 20 }
  for (const [chiave, valore] of Object.entries(filtriValidati.value)) {
    params[FILTRI_TRI_STATO[chiave]] = (valore === 'solo')
  }
  return params
}

const ac = useServerAutocomplete(async (query) => {
  return await lookupArticoli(_buildLookupParams(query))
}, {
  minLength: 3,
  transform: (res) => (res.data.data.results ?? res.data.data ?? []).map(r => ({
    ...r,
    _display: `${r.codice} — ${r.descrizione}`
  }))
})

function buildDisplay(r) {
  if (!r) return ''
  if (r.codice && r.descrizione) return `${r.codice} — ${r.descrizione}`
  return r.codice || r.descrizione || `#${r.id}`
}

// Normalizza il modelValue garantendo `_display` (anti "[object Object]" sui
// restore con sole {id, codice, descrizione}). BB condiviso (B6).
const displayedModel = useLookupDisplayModel(() => props.modelValue, buildDisplay)

function onSelect(event) {
  emit('update:modelValue', event.value)
  emit('select', event.value)
}

function onClear() {
  emit('update:modelValue', null)
}
</script>

<template>
  <AutoComplete
    :modelValue="displayedModel"
    :suggestions="ac.suggestions.value"
    @complete="ac.onSearch"
    @item-select="onSelect"
    @clear="onClear"
    optionLabel="_display"
    :placeholder="placeholder || t('catalogo.search_placeholder')"
    :disabled="disabled"
    dropdown
  />
</template>
