<script setup>
// Scopo: Autocomplete soggetto+ruolo server-side riutilizzabile cross-dominio
// (selezione contesto pratica e futuri picker per-ruolo). Una opzione per
// soggetto_ruolo ("Rossi Srl — Cliente", "Rossi Srl — Fornitore") + opzione
// "senza ruolo" per i soggetti privi di ruoli (non hanno istanze: il ruolo
// CLIENTE nasce con la prima — brief-db-istanza-nasce-col-ba, D-3). Display
// dropdown a 3 righe: ragione sociale + badge ruolo (primary), codice soggetto
// (secondary), id fiscale + numero di forniture (meta). Scope emittente sul
// ruolo CL applicato lato backend.
// `n_billing_account` sull'oggetto selezionato (le forniture del ruolo, un BA
// per coppia istanza+utility) pilota la scelta della fornitura del chiamante.
import { useI18n } from 'vue-i18n'
import { useServerAutocomplete } from '../composables/useServerAutocomplete'
import { useLookupDisplayModel } from '../composables/useLookupDisplayModel'
import { useAutocompleteRefineHint } from '../composables/useAutocompleteRefineHint'
import { lookupSoggettiRuoli } from '../apiCore'
import AutoComplete from 'primevue/autocomplete'
import { MANAGE_ICONS } from '../constants'

const { t } = useI18n()

const props = defineProps({
  // Oggetto riga lookup completo {soggetto_id, soggetto_ruolo_id|null,
  // ruolo_codice_interno|null, ruolo_descrizione|null, ragione_sociale_completa,
  // id_fiscale, soggetto_codice, n_billing_account, billing_account_unico_id,
  // billing_account_unico_codice}
  modelValue: { type: Object, default: null },
  // Filtro codice tipo ruolo (CL, FO, ...). Esclude le righe "senza ruolo".
  tipoRuolo: { type: String, default: null },
  // Solo righe con un ruolo, di qualunque tipo: per i campi che salvano un
  // `soggetto_ruolo_id` (destinatario, vettore, mittente del DDT), dove una
  // riga "senza ruolo" non ha niente da salvare e lascerebbe il campo vuoto.
  soloConRuolo: { type: Boolean, default: false },
  placeholder: { type: String, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'select', 'clear'])

// Hint "affina la ricerca" (total_count > limit). BB condiviso.
const { totalCount, mostrati, daAffinare, onResponse } = useAutocompleteRefineHint()

const ac = useServerAutocomplete(async (query) => {
  const params = { q: query }
  if (props.tipoRuolo) params.tipo_ruolo = props.tipoRuolo
  if (props.soloConRuolo) params.con_ruolo = true
  return await lookupSoggettiRuoli(params)
}, {
  minLength: 2,
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

// Normalizza il modelValue garantendo `_display` (restore by-id).
const displayedModel = useLookupDisplayModel(() => props.modelValue, buildDisplay)

function buildDisplay(r) {
  const parts = []
  if (r.ragione_sociale_completa) parts.push(r.ragione_sociale_completa)
  parts.push(r.ruolo_descrizione || t('soggetto_ruolo_lookup.senza_ruolo'))
  if (r.id_fiscale) parts.push(r.id_fiscale)
  return parts.join(' · ') || `#${r.soggetto_id}`
}

function onSelect(event) {
  emit('update:modelValue', event.value)
  emit('select', event.value)
}

function onClear() {
  emit('update:modelValue', null)
  emit('clear')
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
    :placeholder="placeholder || t('soggetto_ruolo_lookup.search_placeholder')"
    :disabled="disabled"
    :emptySearchMessage="t('soggetto_ruolo_lookup.no_results')"
    dropdown
  >
    <template #option="{ option }">
      <div class="app-lookup-option">
        <div class="app-lookup-option__primary">
          <span>{{ option.ragione_sociale_completa || '—' }}</span>
          <span v-if="option.ruolo_codice_interno" class="app-lookup-badge app-lookup-badge--utility">
            {{ option.ruolo_descrizione || option.ruolo_codice_interno }}
          </span>
          <span v-else class="app-lookup-badge app-lookup-badge--parent">
            {{ t('soggetto_ruolo_lookup.senza_ruolo') }}
          </span>
        </div>
        <div class="app-lookup-option__secondary">
          {{ option.soggetto_codice }}
        </div>
        <div class="app-lookup-option__meta">
          <span v-if="option.id_fiscale">{{ option.id_fiscale }}</span>
          <span v-if="option.n_billing_account > 0">
            <i :class="MANAGE_ICONS.UTILITY"></i>
            {{ t('soggetto_ruolo_lookup.n_forniture', { n: option.n_billing_account }) }}
          </span>
        </div>
      </div>
    </template>
    <template #footer v-if="daAffinare">
      <div class="app-lookup-hint">
        {{ t('soggetto_ruolo_lookup.refine_hint', { shown: mostrati, total: totalCount }) }}
      </div>
    </template>
  </AutoComplete>
</template>
