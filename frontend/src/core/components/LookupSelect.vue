<script setup>
// Scopo: Select generico per tabelle lookup whitelisted (id, codice, descrizione).
// Usa l'endpoint /api/v1/core/lookup/codici/?rel=<schema.tabella> tramite lookupCodici.
// Riusabile ovunque serva un dropdown da tabella config/catalogo/vendite.
//
// Due modi di fetch (regola del 2, B5 2026-06-05 — assorbe i wrapper Select
// su lookup statico per codice):
//   1) `rel` (default storico): fetch via lookupCodici(rel), transform
//      envelope paginato `r.data.data.results`.
//   2) `fetcher` esterno: una funzione che ritorna una Promise axios (es.
//      lookupTipiVariazioneContratto). Richiede `lookupKey` come chiave cache
//      e tipicamente `transform` custom (es. lista nuda in `r.data.data`).
// Esattamente UNO tra `rel` e `fetcher` va passato.
//
// Uso:
//   <LookupSelect v-model="form.iva_id" rel="config.iva" />
//   <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura" :label-field="'codice'" />
//   <LookupSelect v-model="form.conto_id" rel="config.conti_contabili" show-code />
//   <LookupSelect v-model="form.tipo" :fetcher="lookupX" lookup-key="vendite.x"
//                 :transform="r => r.data.data" value-field="codice" show-code />
import { computed } from 'vue'
import { useGlobalLookup } from '../composables/useGlobalLookup'
import { LOOKUP_CODICI_PAGE_SIZE, useLookupCodici } from '../composables/useLookupCodici'
import { etichettaVoce } from '../utils/etichettaSelezionata'
import Select from 'primevue/select'

const props = defineProps({
  // `null` non e' un costruttore valido in defineProps: tipi supportati
  // [Number, String] + default null copre il caso "nessun valore".
  modelValue: { type: [Number, String], default: null },
  // `rel` non e' piu' required: in alternativa si passa `fetcher` + `lookupKey`.
  rel: { type: String, default: '' },
  // Fetcher esterno (Promise axios). Mutuamente esclusivo con `rel`.
  fetcher: { type: Function, default: null },
  // Chiave cache useGlobalLookup quando si usa `fetcher` (fallback a `rel`).
  lookupKey: { type: String, default: '' },
  // Transform risposta. Default (undefined) -> envelope paginato di useGlobalLookup
  // (`r.data.data.results`). Passare `r => r.data.data` per liste nude.
  transform: { type: Function, default: undefined },
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
  // La voce da NON proporre (per `valueField`): il picker del PADRE di una
  // gerarchia non offre l'entita' stessa (2026-09-21, ubicazioni). ⛔ Va qui,
  // a valle della cache, e NON nel `transform`: `useGlobalLookup` registra il
  // primo transform per chiave e non lo sovrascrive, quindi un filtro «senza
  // me» dentro il transform resterebbe scritto nella cache condivisa — la
  // seconda entita' aperta non vedrebbe la prima fra i padri possibili.
  excludeValue: { type: [Number, String], default: null },
  pageSize: { type: Number, default: LOOKUP_CODICI_PAGE_SIZE },
  // Prepend di una voce "Tutti" (value=null) — per i Select usati come filtro
  // lista (es. stato email log). Etichetta da `allLabel`.
  includeAllOption: { type: Boolean, default: false },
  allLabel: { type: String, default: '' },
  // Default true = comportamento storico (mostra anche le voci di catalogo
  // obsolete, obsoleto_dal <= oggi). Passare false nella "selezione per il
  // nuovo" (es. tipo nuova pratica) per nasconderle. Vale solo in modalita' `rel`.
  includiObsoleti: { type: Boolean, default: true },
})

if (import.meta.env.DEV && !props.rel === !props.fetcher) {
  // Guard di sviluppo: esattamente uno tra rel/fetcher.
  console.warn('[LookupSelect] passare esattamente uno tra `rel` e `fetcher`.')
}

const emit = defineEmits(['update:modelValue', 'change'])

// Cache globale per-chiave: tutte le istanze con la stessa chiave condividono
// la stessa fetch (evita N chiamate duplicate nei form con piu' dropdown).
// Chiave = `rel` nel modo storico, `lookupKey` (fallback `rel`) col fetcher.
// In modalita' `rel` chiave e fetch le compone `useLookupCodici` (con gli
// obsoleti esclusi la chiave e' un'altra: stesso `rel`, insieme diverso), cosi'
// una preselezione o una home che leggono lo stesso insieme condividono
// l'entry per costruzione, non per aver ricopiato la stringa.
const lookupOptions = { immediate: true }
if (props.transform) lookupOptions.transform = props.transform
const lookup = props.fetcher
  ? useGlobalLookup(props.lookupKey || props.rel, props.fetcher, lookupOptions)
  : useLookupCodici(props.rel, {
      includiObsoleti: props.includiObsoleti,
      pageSize: props.pageSize,
      ...lookupOptions,
    })

const filteredItems = computed(() => {
  let items = lookup.items.value
  if (props.excludeValue != null) {
    items = items.filter(item => item?.[props.valueField] !== props.excludeValue)
  }
  if (!props.filterField || props.filterValue == null) return items
  return items.filter(item => item?.[props.filterField] === props.filterValue)
})

// Opzioni renderizzate: con includeAllOption prepende la voce "Tutti"
// (value=null), usando gli stessi field-name del Select.
const visibleOptions = computed(() => {
  if (!props.includeAllOption) return filteredItems.value
  return [
    { [props.valueField]: null, [props.labelField]: props.allLabel },
    ...filteredItems.value,
  ]
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
// Cerca in visibleOptions cosi' la voce "Tutti" (includeAllOption) e' matchata.
const selectedItem = computed(() =>
  visibleOptions.value.find(i => i[props.valueField] === props.modelValue) || null
)

// Il testo intero del valore nel `title`: la combo stretta (taglia `md` dei
// filtri) lo taglia coi puntini. Stesso testo di `formatOption`, cioe' cio' che
// si legge a video. Nessuna selezione ⇒ niente attributo. (A4, 2026-09-24)
// ⛔ NON MODIFICARE (decisione di Tid, 2026-09-24): il `title` deriva da
//    `selectedItem`, la voce selezionata si cerca UNA volta sola. Non passare
//    a `etichettaSelezionata(visibleOptions, ...)`: rifarebbe la stessa
//    ricerca, e due ricerche dello stesso valore prima o poi divergono.
const titolo = computed(() => etichettaVoce(selectedItem.value, formatOption))

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
    :title="titolo"
    @change="onChange"
  >
    <template v-if="showCode" #option="{ option }">
      {{ formatOption(option) }}
    </template>
    <template v-if="showCode" #value>
      <span v-if="selectedItem">{{ formatOption(selectedItem) }}</span>
      <span v-else class="app-text-muted">{{ placeholder }}</span>
    </template>
  </Select>
</template>
