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
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServerAutocomplete } from '../composables/useServerAutocomplete'
import { lookupIstanzeUtility } from '../apiCore'
import AutoComplete from 'primevue/autocomplete'

const { t } = useI18n()

const props = defineProps({
  // Oggetto istanza completo {id, codice, fittizia, soggetto_id,
  //   ragione_sociale_completa, indirizzo_display, billing_account_id,
  //   billing_account_codice, utility_id, utility_codice, utility_descrizione, ...}
  modelValue: { type: Object, default: null },
  // Filtro utility strict (post Strategia C ogni istanza dichiara utility via
  // BA, dati_precontrattuali o clienti). Opzionale.
  utilityId: { type: Number, default: null },
  // Filtro soggetto (UUID). Restringe la ricerca al solo soggetto.
  soggettoId: { type: String, default: null },
  placeholder: { type: String, default: null },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'select', 'clear'])

// Tiene traccia del total_count ritornato dall'ultima ricerca
// per mostrare il messaggio "affina la ricerca" quando total > limit.
const totalCount = ref(0)
const limitShown = ref(0)

const ac = useServerAutocomplete(async (query) => {
  const params = { q: query }
  if (props.utilityId != null) params.utility_id = props.utilityId
  if (props.soggettoId) params.soggetto_id = props.soggettoId
  return await lookupIstanzeUtility(params)
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
  onResponse: (res) => {
    if (!res) {
      totalCount.value = 0
      limitShown.value = 0
      return
    }
    const data = res.data.data || {}
    totalCount.value = data.total_count || 0
    limitShown.value = data.limit || 0
  }
})

function buildDisplay(r) {
  const parts = []
  if (r.ragione_sociale_completa) parts.push(r.ragione_sociale_completa)
  if (r.codice) parts.push(r.codice)
  if (r.indirizzo_display) parts.push(r.indirizzo_display)
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
    :modelValue="modelValue"
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
          <span v-if="option.billing_account_codice">
            {{ t('istanza_utility.ba_label') }}: {{ option.billing_account_codice }}
          </span>
        </div>
      </div>
    </template>
    <template #footer v-if="totalCount > limitShown && limitShown > 0">
      <div class="app-lookup-hint">
        {{ t('istanza_utility.refine_hint', { shown: limitShown, total: totalCount }) }}
      </div>
    </template>
  </AutoComplete>
</template>
