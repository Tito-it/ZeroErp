<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: La tendina del listino di un documento commerciale (contratto, offerta):
// propone i listini che un documento di QUESTA utility e di QUESTO emittente puo'
// scegliere, e si ricarica quando il form cambia l'una o l'altro.
//
// Uso:
//   <ListinoDocumentoSelect v-model="form.listino_id"
//     :utility-id="form.utility_id" :emittente-fiscale-id="form.emittente_fiscale_id"
//     :record="detail" @update:model-value="onListinoChange" />
//
// ⛔ QUI NON C'E' UNA REGOLA. Quali listini si scelgono lo dice il DB
// (`vendite.fn_listini_selezionabili`), con lo stesso predicato del guard che
// rifiuta al salvataggio un listino di un'altra utility o di un altro emittente
// (F-2 di brief-db-offerta-emissione-ed-erogazione). La tendina non propone
// cio' che il DB rifiuterebbe.
// ⭐ REGOLA DEL 2 (ok Tid, 2026-10-08): prende il posto delle due copie in
// ContrattoDrawer e OffertaDrawer (useGlobalLookup a chiave fissa sul vecchio
// filtro «almeno una versione ATTIVA», ritirato col D.4.3).
// ⚠️ Quando utility o emittente cambiano (in creazione: la scelta del cliente
// porta la sua utility), un listino gia' scelto che il DB non propone piu' si
// AZZERA: resterebbe nel form senza vedersi nella tendina, e il salvataggio lo
// rifiuterebbe su un campo che a video e' vuoto. A differenza di
// `TipologiaListinoSelect` lo fa il componente: il «documento che si sta
// caricando» qui lo copre `record`, il cui listino resta sempre fra le opzioni.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import { lookupListiniSelezionabili } from '../api/lookup'
import { useFetchVersion } from '../../core/composables/useFetchVersion'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  // Utility ed emittente del FORM: in creazione il documento non esiste.
  utilityId: { type: [Number, String, null], default: null },
  emittenteFiscaleId: { type: [Number, String, null], default: null },
  // Il documento letto (il `detail` del drawer, null in creazione): il suo
  // listino (`listino_id`, `listino_codice`, `listino_descrizione`) resta fra le
  // opzioni anche se oggi non si sceglierebbe (i documenti gia' scritti restano
  // come sono, F-2.4), o la tendina lo mostrerebbe vuoto. Come il `record` di
  // `EmittenteFiscaleField`.
  record: { type: Object, default: null },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const items = ref([])
const loading = ref(false)
// ⚠️ Al cambio di utility o emittente la fetch riparte mentre la precedente e'
// ancora in volo: senza il guard di versione la risposta VECCHIA, se arriva per
// ultima, sovrascriverebbe i listini giusti, senza errore.
const fetchVersion = useFetchVersion()

const contestoCompleto = computed(() => props.utilityId != null && props.emittenteFiscaleId != null)

// Scopo: Carica i listini sceglibili per la coppia corrente (utility, emittente).
// Senza uno dei due non chiede niente: il DB risponderebbe comunque nessun listino.
// Solo la chiamata piu' recente scrive `items` e spegne `loading`. Su una risposta
// buona azzera la scelta che non e' piu' fra le opzioni; su un errore no: la
// lista vuota allora non dice che il listino non si sceglie.
async function load() {
  const tag = fetchVersion.tag()
  if (!contestoCompleto.value) {
    items.value = []
    loading.value = false
    return
  }
  loading.value = true
  let risultati
  let riuscita = true
  try {
    const res = await lookupListiniSelezionabili(props.utilityId, props.emittenteFiscaleId)
    risultati = res.data?.data?.results || []
  } catch {
    risultati = []
    riuscita = false
  }
  if (!fetchVersion.isCurrent(tag)) return
  items.value = risultati
  loading.value = false
  if (riuscita && !props.disabled && props.modelValue != null
    && !opzioni.value.some((l) => l.id === props.modelValue)) {
    emit('update:modelValue', null)
  }
}

const corrente = computed(() => (props.record?.listino_id == null ? null : {
  id: props.record.listino_id,
  codice: props.record.listino_codice,
  descrizione: props.record.listino_descrizione,
}))

const opzioni = computed(() => {
  const c = corrente.value
  if (c == null || items.value.some((l) => l.id === c.id)) return items.value
  return [...items.value, c]
})

// ⚠️ Dopo `opzioni`: `load` la legge, e il watch immediate la chiama subito.
watch(() => [props.utilityId, props.emittenteFiscaleId], load, { immediate: true })

// Scopo: «descrizione (codice)», come `LookupSelect show-code`.
function etichetta(item) {
  if (!item) return ''
  return item.codice ? `${item.descrizione} (${item.codice})` : item.descrizione
}

const segnaposto = computed(() => {
  if (!contestoCompleto.value) return t('vendite.listini.selezionabili_utility_emittente_first')
  if (loading.value) return t('common.loading')
  return props.placeholder
})
</script>

<template>
  <Select
    :model-value="modelValue"
    :options="opzioni"
    :option-label="etichetta"
    option-value="id"
    :loading="loading"
    :placeholder="segnaposto"
    :invalid="invalid"
    :disabled="disabled"
    show-clear
    filter
    @update:model-value="(v) => emit('update:modelValue', v)"
  />
</template>
