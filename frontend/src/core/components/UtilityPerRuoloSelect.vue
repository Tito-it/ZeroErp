<script setup>
// Scopo: Select riusabile per scegliere una utility ammessa per il ruolo
// emittente (EF), filtrata per tipo ruolo soggetto (CL, FO, ecc.).
// Se tipoRuoloCodice non e' fornito, mostra tutte le utility ammesse per EF.
//
// Uso:
//   <UtilityPerRuoloSelect v-model="form.utility_id" :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE" />
//   <UtilityPerRuoloSelect v-model="form.utility_id" />  <!-- tutte le utility ammesse per EF -->
//   <UtilityPerRuoloSelect v-model="filter.utility_id" apply-default />  <!-- filtri lista -->
//
// Backend: GET /api/v1/core/lookup/utilities-per-emittente/?ruolo=CL
// Filtra per: matrice utilities_tipi_ruolo (ruolo EF, piu' il ruolo soggetto se dato).
import { computed, ref, watch, onMounted } from 'vue'
import { lookupUtilitiesPerEmittente } from '../apiCore'
import { useFetchVersion } from '../composables/useFetchVersion'
import { useUtilityDefaultId } from '../composables/useUtilityDefaultId'
import { etichettaSelezionata } from '../utils/etichettaSelezionata'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  tipoRuoloCodice: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  showClear: { type: Boolean, default: false },
  filter: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  // optionLabel: 'descrizione' (default) o 'codice'
  labelField: { type: String, default: 'descrizione' },
  // Se true, al primo mount applica DEFAULT_UTILITY (parameter, catena
  // user→group→emittente→default sistema) come modelValue iniziale quando
  // il caller non ha gia' un valore. Usato dai filtri di lista per partire
  // pre-filtrati sull'utility tipica dell'operatore. I drawer non lo usano:
  // hanno gia' una propria orchestrazione di defaults via useUtilityDefaultId.
  applyDefault: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'change'])

// Il campo valore delle voci: lo leggono sia il `Select` sia il `title`. ⚠️ Se
// divergessero il `title` sparirebbe senza errore — per questo sta in un posto.
const CAMPO_VALORE = 'id'

const items = ref([])
const loading = ref(false)

const { id: defaultUtilityId, load: loadDefaultUtility } = useUtilityDefaultId({
  ruolo: props.tipoRuoloCodice || null
})

// ⚠️ Al cambio di `tipoRuoloCodice` la fetch riparte mentre la precedente e'
// ancora in volo: senza il guard di versione una risposta lenta del ruolo
// VECCHIO arriverebbe dopo e sovrascriverebbe le voci giuste, senza errore.
const fetchVersion = useFetchVersion()

// Scopo: Carica le utility ammesse per il ruolo EF.
// Se tipoRuoloCodice e' valorizzato, filtra per intersezione ruolo + EF.
// Solo la chiamata piu' recente scrive `items` e spegne `loading`.
async function load() {
  const t = fetchVersion.tag()
  loading.value = true
  let risultati
  try {
    const res = await lookupUtilitiesPerEmittente(props.tipoRuoloCodice || undefined)
    risultati = res.data?.data?.results || []
  } catch {
    risultati = []
  }
  if (!fetchVersion.isCurrent(t)) return
  items.value = risultati
  loading.value = false
}

watch(() => props.tipoRuoloCodice, load, { immediate: true })

// Auto-applica il default solo al primo mount e solo se il caller non ha
// gia' un valore. Emette anche `change` per innescare l'eventuale handler
// di filtro (onUtilityChange → applyFilters) nelle search table.
onMounted(async () => {
  if (!props.applyDefault) return
  if (props.modelValue != null) return
  await loadDefaultUtility()
  if (props.modelValue == null && defaultUtilityId.value != null) {
    emit('update:modelValue', defaultUtilityId.value)
    emit('change', defaultUtilityId.value)
  }
})

// Il testo intero del valore nel `title`: in un filtro di lista la combo e'
// `md` e taglia la descrizione coi puntini. (A4, 2026-09-24)
const titolo = computed(() =>
  etichettaSelezionata(items.value, props.modelValue, {
    campoValore: CAMPO_VALORE,
    etichetta: props.labelField,
  })
)

function onChange(event) {
  emit('update:modelValue', event.value)
  emit('change', event.value)
}
</script>

<template>
  <Select
    :modelValue="modelValue"
    @update:modelValue="v => emit('update:modelValue', v)"
    :options="items"
    :loading="loading"
    :optionLabel="labelField"
    :optionValue="CAMPO_VALORE"
    :placeholder="placeholder"
    :showClear="showClear"
    :filter="filter"
    :disabled="disabled"
    :title="titolo"
    @change="onChange"
  />
</template>
