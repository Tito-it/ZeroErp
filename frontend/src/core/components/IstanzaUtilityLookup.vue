<script setup>
// Scopo: Autocomplete istanze_utilities server-side riutilizzabile cross-dominio.
// Ricerca multi-campo (codice istanza, ragione sociale soggetto, indirizzo)
// con scope emittente automatico via BA collegato all'istanza.
// Display dropdown a 3 righe:
//   primary: ragione sociale + tag utility (se BA dichiara utility) +
//            badge "Solo istanza" se istanza orfana / "Fittizia" se fittizia
//   secondary: codice istanza
//   meta: indirizzo + (se BA) codice BA
// Usato da: PreventiviForm (prospect senza BA), future utility-aware flows.
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServerAutocomplete } from '../composables/useServerAutocomplete'
import { useLookupDisplayModel } from '../composables/useLookupDisplayModel'
import { useAutocompleteRefineHint } from '../composables/useAutocompleteRefineHint'
import { lookupIstanzeUtility } from '../apiCore'
import AutoComplete from 'primevue/autocomplete'

const { t } = useI18n()

const props = defineProps({
  // Oggetto istanza completo {id, codice, fittizia, soggetto_id,
  //   ragione_sociale_completa, indirizzo_display, pdp_id, pdp_codice,
  //   billing_account_id, billing_account_codice, utility_id, utility_codice,
  //   utility_descrizione, ...}
  modelValue: { type: Object, default: null },
  // Filtro utility strict (post Strategia C ogni istanza dichiara utility via
  // BA, dati_precontrattuali o clienti). Opzionale.
  utilityId: { type: Number, default: null },
  // Filtro soggetto (UUID). Restringe la ricerca al solo soggetto.
  soggettoId: { type: String, default: null },
  // Filtro ruolo (soggetto_ruolo_id). Restringe alle sole istanze legate a
  // quel ruolo via clienti (le forniture del cliente/BA selezionato) —
  // evita l'aggancio a istanze del soggetto estranee al rapporto cliente.
  soggettoRuoloId: { type: Number, default: null },
  placeholder: { type: String, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'select', 'clear'])

// Perimetro contestuale attivo: stessi predicati usati nel build dei params
// (soggettoId truthy — '' non conta — e soggettoRuoloId valorizzato).
function hasPerimetro() {
  return Boolean(props.soggettoId) || props.soggettoRuoloId != null
}

// Hint "affina la ricerca" (total_count > limit). BB condiviso (B6).
const { totalCount, mostrati, daAffinare, onResponse } = useAutocompleteRefineHint()

const ac = useServerAutocomplete(async (query) => {
  const params = { q: query }
  if (props.utilityId != null) params.utility_id = props.utilityId
  if (props.soggettoId) params.soggetto_id = props.soggettoId
  if (props.soggettoRuoloId != null) params.soggetto_ruolo_id = props.soggettoRuoloId
  return await lookupIstanzeUtility(params)
}, {
  // Con perimetro soggetto/ruolo il set e' gia' ristretto: la tendina lista
  // le istanze al click senza obbligare a digitare (il BE accetta q vuota
  // solo in presenza del perimetro). Senza perimetro resta search-first.
  minLength: () => (hasPerimetro() ? 0 : 2),
  transform: (res) => {
    const data = res.data.data || {}
    const results = data.results || []
    return results.map(r => ({
      ...r,
      _display: buildDisplay(r)
    }))
  },
  onResponse,
})

function buildDisplay(r) {
  const parts = []
  if (r.ragione_sociale_completa) parts.push(r.ragione_sociale_completa)
  if (r.codice) parts.push(r.codice)
  if (r.indirizzo_display) parts.push(r.indirizzo_display)
  if (r.pdp_codice) parts.push(`PDP ${r.pdp_codice}`)
  return parts.join(' · ') || `#${r.id}`
}

// Normalizza il modelValue garantendo `_display` (anti "[object Object]" sui
// restore by-id). BB condiviso (B6); buildDisplay resta caller-side.
const displayedModel = useLookupDisplayModel(() => props.modelValue, buildDisplay)

function onSelect(event) {
  emit('update:modelValue', event.value)
  emit('select', event.value)
}

function onClear() {
  emit('update:modelValue', null)
  emit('clear')
}

// Quando l'utility cambia, l'istanza selezionata potrebbe non essere piu'
// coerente con la nuova utility. Azzera la selezione per forzare ricerca
// nel contesto aggiornato. Si azzera solo se l'istanza dichiara utility
// diversa da quella nuova (evita reset inutili su transizioni null → id).
watch(() => props.utilityId, (newUtility, oldUtility) => {
  if (newUtility === oldUtility) return
  const current = props.modelValue
  if (current && current.utility_id != null && current.utility_id !== newUtility) {
    emit('update:modelValue', null)
    emit('clear')
  }
})
</script>

<template>
  <AutoComplete
    :modelValue="displayedModel"
    :suggestions="ac.suggestions.value"
    @complete="ac.onSearch"
    @item-select="onSelect"
    @clear="onClear"
    optionLabel="_display"
    :placeholder="placeholder || t('istanza_utility.search_placeholder')"
    :disabled="disabled"
    :emptySearchMessage="t('istanza_utility.no_results')"
    dropdown
  >
    <template #option="{ option }">
      <div class="app-lookup-option">
        <div class="app-lookup-option__primary">
          <span>{{ option.ragione_sociale_completa || '—' }}</span>
          <span v-if="option.utility_codice" class="app-lookup-badge app-lookup-badge--utility">
            {{ option.utility_codice }}
          </span>
          <span v-if="option.fittizia" class="app-lookup-badge">
            {{ t('istanza_utility.fittizia_badge') }}
          </span>
          <span v-if="!option.billing_account_id" class="app-lookup-badge">
            {{ t('istanza_utility.solo_istanza_badge') }}
          </span>
        </div>
        <div class="app-lookup-option__secondary">
          {{ option.codice }}
        </div>
        <div class="app-lookup-option__meta">
          <span v-if="option.indirizzo_display">
            <i class="pi pi-map-marker"></i>
            {{ option.indirizzo_display }}
          </span>
          <span v-if="option.pdp_codice">
            <i class="pi pi-bolt"></i>
            {{ t('istanza_utility.pdp_label') }}: {{ option.pdp_codice }}
          </span>
          <span v-if="option.billing_account_codice">
            {{ t('istanza_utility.ba_label') }}: {{ option.billing_account_codice }}
          </span>
        </div>
      </div>
    </template>
    <template #footer v-if="daAffinare">
      <div class="app-lookup-hint">
        {{ t('istanza_utility.refine_hint', { shown: mostrati, total: totalCount }) }}
      </div>
    </template>
  </AutoComplete>
</template>
