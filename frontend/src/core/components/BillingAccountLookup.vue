<script setup>
// Scopo: Autocomplete billing_account server-side riutilizzabile cross-dominio.
// Ricerca multi-campo (codice, ragione sociale, id fiscale, PDP) con JOIN ricchi.
// Display dropdown a 3 righe: ragione sociale (primary), codice BA (secondary),
// id fiscale + PDP (meta). Utility (se presente) come tag nella riga primary.
// Scope emittente fiscale applicato automaticamente lato backend.
// Usato da: righe listini, righe preventivi, ordini, fatture, pratiche.
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServerAutocomplete } from '../composables/useServerAutocomplete'
import { useLookupDisplayModel } from '../composables/useLookupDisplayModel'
import { useAutocompleteRefineHint } from '../composables/useAutocompleteRefineHint'
import { lookupBillingAccount } from '../apiCore'
import AutoComplete from 'primevue/autocomplete'

const { t } = useI18n()

const props = defineProps({
  // Oggetto BA completo {id, codice, ragione_sociale_completa, id_fiscale, pdp, ...}
  modelValue: { type: Object, default: null },
  // Filtro utility (passato dal form chiamante; opzionale se utility non selezionata)
  utilityId: { type: Number, default: null },
  // Se true (default), mostra solo BA validi alla data di riferimento
  soloValidi: { type: Boolean, default: true },
  // Data ISO YYYY-MM-DD per audit retroattivo (solo con soloValidi=true)
  validAt: { type: String, default: null },
  placeholder: { type: String, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'select', 'clear'])

// Hint "affina la ricerca" (total_count > limit). BB condiviso (B6).
const { totalCount, mostrati, daAffinare, onResponse } = useAutocompleteRefineHint()

const ac = useServerAutocomplete(async (query) => {
  const params = {
    q: query,
    solo_validi: props.soloValidi,
  }
  if (props.utilityId != null) params.utility_id = props.utilityId
  if (props.validAt) params.valid_at = props.validAt
  return await lookupBillingAccount(params)
}, {
  minLength: 2,
  transform: (res) => {
    const data = res.data.data || {}
    const results = data.results || []
    // Costruisci _display compatto per il campo input chiuso:
    // "Ragione Sociale — BA-XXX · ID Fiscale" (formato C approvato).
    return results.map(r => ({
      ...r,
      _display: buildDisplay(r)
    }))
  },
  onResponse,
})

// Normalizza il modelValue garantendo `_display` (anti "[object Object]" sui
// restore by-id). BB condiviso (B6); buildDisplay resta caller-side.
const displayedModel = useLookupDisplayModel(() => props.modelValue, buildDisplay)

function buildDisplay(r) {
  const parts = []
  if (r.ragione_sociale_completa) parts.push(r.ragione_sociale_completa)
  if (r.codice) parts.push(r.codice)
  if (r.id_fiscale) parts.push(r.id_fiscale)
  // Fallback per evitare input vuoto quando tutti i campi sono null (edge case
  // vw_soggetti_ruoli_dettaglio senza match): mostra almeno #id.
  return parts.join(' · ') || `#${r.id}`
}

function onSelect(event) {
  emit('update:modelValue', event.value)
  emit('select', event.value)
}

function onClear() {
  emit('update:modelValue', null)
  emit('clear')
}

// Quando l'utility cambia, il BA selezionato potrebbe non essere piu' coerente
// (un BA appartiene a una sola utility). Azzera la selezione per forzare
// all'utente di ricercarne uno nuovo nel contesto aggiornato.
// Si azzera solo se il BA corrente aveva un'utility diversa da quella nuova,
// per evitare reset inutili su transizioni null → id.
watch(() => props.utilityId, (newUtility, oldUtility) => {
  if (newUtility === oldUtility) return
  const currentBa = props.modelValue
  if (currentBa && currentBa.utility_id != null && currentBa.utility_id !== newUtility) {
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
    :placeholder="placeholder || t('billing_account.search_placeholder')"
    :disabled="disabled"
    :emptySearchMessage="t('billing_account.no_results')"
    dropdown
  >
    <template #option="{ option }">
      <div class="app-lookup-option">
        <div class="app-lookup-option__primary">
          <span>{{ option.ragione_sociale_completa || '—' }}</span>
          <span v-if="option.utility_codice" class="app-lookup-badge app-lookup-badge--utility">
            {{ option.utility_codice }}
          </span>
          <span v-if="option.parent_codice" class="app-lookup-badge app-lookup-badge--parent"
            :title="t('billing_account.figlio_di', { parent: option.parent_codice })">
            <i class="pi pi-sitemap"></i>
            {{ option.parent_codice }}
          </span>
        </div>
        <div class="app-lookup-option__secondary">
          {{ option.codice }}
        </div>
        <div class="app-lookup-option__meta">
          <span v-if="option.id_fiscale">{{ option.id_fiscale }}</span>
          <span v-if="option.pdp">
            <i class="pi pi-bolt"></i>
            {{ t('billing_account.pdp_label') }}: {{ option.pdp }}
          </span>
        </div>
      </div>
    </template>
    <template #footer v-if="daAffinare">
      <div class="app-lookup-hint">
        {{ t('billing_account.refine_hint', { shown: mostrati, total: totalCount }) }}
      </div>
    </template>
  </AutoComplete>
</template>
