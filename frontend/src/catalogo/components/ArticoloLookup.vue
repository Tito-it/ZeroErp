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
import { useServerAutocomplete } from '../../core/composables/useServerAutocomplete'
import { useAutocompleteRefineHint } from '../../core/composables/useAutocompleteRefineHint'
import { useLookupDisplayModel } from '../../core/composables/useLookupDisplayModel'
import { lookupArticoli } from '../api/catalogo'
import AutoComplete from 'primevue/autocomplete'

const { t } = useI18n()

// Mappa dichiarativa dei filtri ammessi: chiave (camelCase, lato FE) →
// nome parametro query lato BE. Aggiungere qui per estendere a nuovi
// filtri tri-stato (vedi piano `piano-filtri-articolo-lookup.md` §5).
const FILTRI_TRI_STATO = Object.freeze({
  soloComponenti: 'is_solo_componente',
  compositi:      'is_composito',
  // R-5 (brief magazzino 2-bis, 2026-09-23): lo passa il picker di riga di
  // inventari e rettifiche — un articolo non gestito a magazzino si salva,
  // ma il piano lo marca NON_POSTABILE e la registrazione rifiuta tutto.
  // ⛔ Assente = nessun filtro: altrove la tendina continua a proporre tutto.
  gestitiAMagazzino: 'gestito_a_magazzino',
})
const FILTRO_VALORI_VALIDI = Object.freeze(['qualsiasi', 'escludi', 'solo'])

const props = defineProps({
  modelValue: { type: Object, default: null },
  filtri: { type: Object, default: () => ({}) },
  // Esclusione natura per DESTINAZIONE (data-driven, non per codice): array di
  // destinazioni da non proporre — es. ['CONTRATTO'] sulle righe preventivo per
  // non offrire articoli ricorrenti (difesa in profondità del blocco DB D9).
  escludiDestinazione: { type: Array, default: () => [] },
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
  // Esclusione natura per destinazione: CSV inviato al BE come `escludi_destinazione`.
  const escludi = (props.escludiDestinazione || []).filter(Boolean)
  if (escludi.length) {
    params.escludi_destinazione = escludi.join(',')
  }
  return params
}

// ⚠️ L'elenco degli articoli e' TAGLIATO dal tetto del lookup (50 lato
//    repository, 20 di default dalla view), e fino al 2026-09-10 chi guardava
//    non aveva modo di saperlo: il backend dichiarava `troncato` e a video non
//    lo leggeva nessuno. Il footer lo dice, con la stessa forma degli altri
//    quattro lookup ricchi — la condizione vive nel composable, non qui.
const { mostrati, daAffinare, onResponse } = useAutocompleteRefineHint()

const ac = useServerAutocomplete(async (query) => {
  return await lookupArticoli(_buildLookupParams(query))
}, {
  minLength: 3,
  transform: (res) => (res.data.data.results ?? res.data.data ?? []).map(r => ({
    ...r,
    _display: `${r.codice} — ${r.descrizione}`
  })),
  onResponse,
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
  >
    <template #footer v-if="daAffinare">
      <div class="app-lookup-hint">
        {{ t('common.refine_hint_troncato', { shown: mostrati }) }}
      </div>
    </template>
  </AutoComplete>
</template>
