<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: PUNTARE UNA FATTURA da qualunque schermata — autocomplete server-side
//        sulla lista dei documenti fiscali (`vendite.vw_fatture_lista`).
//
// ⭐ Estratto il 2026-08-28 alla SECONDA occorrenza (regola del 2, ed e' il
//    primo dei quattro candidati dichiarati in §5.3 del brief incassi): il
//    primo consumatore e' l'abbinamento di una riga contabile alla fattura, il
//    secondo la sistemazione di un'eccedenza, che deve puntare il documento su
//    cui portare il credito. Due schermate di due domini diversi che fanno la
//    stessa domanda: «quale documento?».
//
// ⚠️ Vive in `core/` e non in `vendite/`: chi lo usa sta FUORI da vendite —
//    metterlo la' dentro farebbe dipendere `pagamenti` da un componente di un
//    modulo di pari livello, che e' esattamente cio' che si vuole evitare.
//
// ⚠️ Una fattura in BOZZA non ha numero (`numero`, `serie` e `anno` restano
//    NULL finche' non e' numerata): l'etichetta lo DICE invece di mostrare una
//    riga che comincia con un trattino, o peggio vuota.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import AutoComplete from 'primevue/autocomplete'

import { useLookupDisplayModel } from '../composables/useLookupDisplayModel'
import { useServerAutocomplete } from '../composables/useServerAutocomplete'
import { listFatture } from '../../vendite/api/fatture'

const props = defineProps({
  // L'oggetto riga completo (`id`, `numero`, `ragione_sociale_completa`,
  // `billing_account_id`, ...): chi chiama spesso ne usa piu' di un campo.
  modelValue: { type: Object, default: null },
  placeholder: { type: String, default: null },
  disabled: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
  // Filtri aggiuntivi passati alla lista (es. `billing_account_id` per non
  // proporre i documenti di un altro cliente).
  params: { type: Object, default: () => ({}) },
  // ⚠️ Tre caratteri e' la soglia di ricerca del progetto: sotto, il backend
  //    non filtra e la tendina mostrerebbe «le prime venti fatture qualsiasi».
  //    ⛔ Per la stessa ragione NON c'e' la freccetta `dropdown`: il click la
  //    apre con query vuota, che sotto la soglia non lista niente — un pulsante
  //    che non fa niente si legge come un guasto.
  minLength: { type: Number, default: 3 },
  // Quante ne chiede al server. Il footer dice quante ce n'erano in tutto.
  limit: { type: Number, default: 20 },
})
const emit = defineEmits(['update:modelValue', 'select', 'clear'])

const { t } = useI18n()

// ⚠️ Il conteggio si legge da `count`, che e' la chiave dell'envelope di
//    QUESTA lista. ⛔ Non si usa `useAutocompleteRefineHint`: quel BB legge
//    `total_count`, che qui non esiste — leggerebbe sempre zero e il footer non
//    comparirebbe mai, cioe' direbbe in silenzio «ci sono solo queste».
const totale = ref(0)

// Scopo: l'etichetta di una fattura. Numero e cliente: le due cose con cui una
//        persona riconosce il documento che ha in mano.
function buildDisplay(r) {
  if (!r) return ''
  const parti = [r.numero || t('fattura_lookup.senza_numero')]
  if (r.ragione_sociale_completa) parti.push(r.ragione_sociale_completa)
  return parti.join(' — ')
}

const ac = useServerAutocomplete(
  (query) => listFatture({ ...props.params, search: query, limit: props.limit }),
  {
    minLength: () => props.minLength,
    transform: (res) => {
      const data = res.data?.data || {}
      totale.value = data.count || 0
      return (data.results || []).map((r) => ({ ...r, _display: buildDisplay(r) }))
    },
  },
)

const mostrati = computed(() => ac.suggestions.value.length)
const troppiRisultati = computed(() => totale.value > mostrati.value && mostrati.value > 0)

const displayedModel = useLookupDisplayModel(() => props.modelValue, buildDisplay)

function onSelect(evento) {
  emit('update:modelValue', evento.value)
  emit('select', evento.value)
}

function onClear() {
  emit('update:modelValue', null)
  emit('clear')
}
</script>

<template>
  <AutoComplete
    :model-value="displayedModel"
    :suggestions="ac.suggestions.value"
    :loading="ac.loading.value"
    option-label="_display"
    :placeholder="placeholder || t('fattura_lookup.placeholder')"
    :disabled="disabled"
    :invalid="invalid"
    :min-length="minLength"
    :empty-search-message="t('fattura_lookup.nessun_risultato')"
    force-selection
    @complete="ac.onSearch"
    @item-select="onSelect"
    @clear="onClear"
  >
    <!-- ⭐ Due righe: il numero e chi c'e' dietro. Su un elenco di documenti
         omonimi il cliente e' l'unica cosa che li distingue. -->
    <template #option="{ option }">
      <div class="app-lookup-option">
        <div class="app-lookup-option__primary">
          <span>{{ option.numero || t('fattura_lookup.senza_numero') }}</span>
        </div>
        <div class="app-lookup-option__secondary">
          {{ option.ragione_sociale_completa || '—' }}
        </div>
      </div>
    </template>

    <!-- ⚠️ «Mostrate N di M» non e' una rifinitura: senza, una ricerca larga
         sembra un elenco completo, e il documento giusto e' fuori. -->
    <template v-if="troppiRisultati" #footer>
      <div class="app-lookup-hint">
        {{ t('fattura_lookup.affina', { shown: mostrati, total: totale }) }}
      </div>
    </template>
  </AutoComplete>
</template>
