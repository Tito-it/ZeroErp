<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
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
//
// ⭐ IL LOOKUP MOSTRA IL DOCUMENTO, NON IL CONTATORE (D19-a, Tid 2026-09-15;
//    scritto il 2026-09-17 a P-1 consegnata). Un contatore nudo e' ambiguo per
//    costruzione — una fattura 1 e una nota di credito 1 nello stesso anno — e
//    chi digita un incasso riconosce il documento da com'e' scritto: il numero
//    parlante, il registro, la data, il totale, la natura. L'opzione ha TRE
//    righe (`app-lookup-option`, la forma di `IstanzaUtilityLookup`):
//      1234 - R1   [Nota di credito]     numero_documento · Tag natura (solo se ≠ FATTURA)
//      REG-01 · 12/09/2026 · 1.220,00 €  registro_codice · data · totale_doc
//      Rossi Mario SRL · 01234567890     ragione_sociale_completa · id fiscale
//    ⛔ NESSUNA composizione del numero qui: `numero_documento` viene dalla
//    sede unica a DB (`fn_numero_documento_fattura`, via `vw_fatture_lista`);
//    il ripiego «senza numero» copre la bozza non numerata, mai una colonna
//    assente.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import AutoComplete from 'primevue/autocomplete'

import NaturaDocTag from '../../core/components/NaturaDocTag.vue'
import { useLookupDisplayModel } from '../../core/composables/useLookupDisplayModel'
import { useServerAutocomplete } from '../../core/composables/useServerAutocomplete'
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { listFatture } from '../api/fatture'

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

// Scopo: il numero parlante di una riga, col ripiego sulla bozza non numerata.
function numeroDocumento(r) {
  return r?.numero_documento || t('fattura_lookup.senza_numero')
}

// Scopo: l'etichetta di una fattura nel campo, dopo la scelta. Numero parlante
//        e cliente: le due cose con cui una persona riconosce il documento che
//        ha in mano.
function buildDisplay(r) {
  if (!r) return ''
  const parti = [numeroDocumento(r)]
  if (r.ragione_sociale_completa) parti.push(r.ragione_sociale_completa)
  return parti.join(' — ')
}

// Scopo: la seconda riga dell'opzione — registro · data · totale — coi soli
//        pezzi che la riga ha (una bozza puo' non avere registro ne' data).
function rigaDocumento(r) {
  const parti = []
  if (r.registro_codice) parti.push(r.registro_codice)
  if (r.data) parti.push(displayDate(r.data))
  if (r.totale_doc != null) parti.push(formatCurrency(r.totale_doc))
  return parti.join(' · ')
}

// Scopo: la terza riga — il cliente e il suo id fiscale.
function rigaCliente(r) {
  const parti = []
  if (r.ragione_sociale_completa) parti.push(r.ragione_sociale_completa)
  if (r.id_fiscale_univoco_cf_piva) parti.push(r.id_fiscale_univoco_cf_piva)
  return parti.join(' · ')
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
    <!-- ⭐ Tre righe: il documento com'e' scritto, dov'e' e quanto vale, e chi
         c'e' dietro. La natura si SEGNALA con un Tag (il BB tace da se' su una
         fattura ordinaria): una nota di credito fra le fatture e' il caso in
         cui il cliente ce la paga (D19-e), e va vista prima di sceglierla. -->
    <template #option="{ option }">
      <div class="app-lookup-option">
        <div class="app-lookup-option__primary">
          <span>{{ numeroDocumento(option) }}</span>
          <NaturaDocTag
            :codice="option.natura_doc_codice_interno"
            :descrizione="option.natura_doc_descrizione"
          />
        </div>
        <div v-if="rigaDocumento(option)" class="app-lookup-option__secondary">
          {{ rigaDocumento(option) }}
        </div>
        <div class="app-lookup-option__meta">
          <span>{{ rigaCliente(option) || '—' }}</span>
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
