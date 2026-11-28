<script setup>
// Scopo: Select riusabile per scegliere una utility che le aziende GESTISCONO
// (brief-db-utility-gestite-dall-emittente §10 R-2), filtrata per tipo ruolo
// soggetto (CL, FO, ecc.) se dato.
//   - con `emittenteFiscaleId`: le utility di quell'azienda. Drawer e form lo
//     passano SEMPRE, con l'azienda del documento: un'utility che l'azienda non
//     gestisce il database la rifiuta al salvataggio;
//   - senza: le utility gestite da almeno un'azienda del perimetro (filtri lista).
//
// Uso:
//   <UtilityPerRuoloSelect v-model="form.utility_id" :emittente-fiscale-id="form.emittente_fiscale_id" />
//   <UtilityPerRuoloSelect v-model="filter.utility_id" apply-default />  <!-- filtri lista -->
//
// Backend: GET /api/v1/core/lookup/utilities-per-emittente/?ruolo=CL&emittente_fiscale_id=<pk>
import { computed, ref, watch, onMounted } from 'vue'
import { lookupUtilitiesPerEmittente } from '../apiCore'
import { useFetchVersion } from '../composables/useFetchVersion'
import { useUtilityDefaultId } from '../composables/useUtilityDefaultId'
import { etichettaSelezionata } from '../utils/etichettaSelezionata'
import Select from 'primevue/select'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  tipoRuoloCodice: { type: String, default: '' },
  // PK dell'azienda (emittente fiscale) del documento; null = il perimetro.
  emittenteFiscaleId: { type: Number, default: null },
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
  ruolo: props.tipoRuoloCodice || null,
  emittenteFiscaleId: () => props.emittenteFiscaleId
})

// ⚠️ Al cambio di `tipoRuoloCodice` o dell'azienda la fetch riparte mentre la
// precedente e' ancora in volo: senza il guard di versione una risposta lenta
// della chiave VECCHIA arriverebbe dopo e sovrascriverebbe le voci giuste.
const fetchVersion = useFetchVersion()

// Scopo: Carica le utility gestite dall'azienda (o dal perimetro), col ruolo
// del soggetto se dato.
// Solo la chiamata piu' recente scrive `items` e spegne `loading`.
// Ritorna true se ha scritto voci LETTE (non una lettura fallita, non una
// risposta superata da una piu' recente).
async function load() {
  const t = fetchVersion.tag()
  loading.value = true
  let risultati
  let letto = true
  try {
    const res = await lookupUtilitiesPerEmittente(
      props.tipoRuoloCodice || undefined, props.emittenteFiscaleId
    )
    risultati = res.data?.data?.results || []
  } catch {
    risultati = []
    letto = false
  }
  if (!fetchVersion.isCurrent(t)) return false
  items.value = risultati
  loading.value = false
  return letto
}

// Scopo: rilegge le voci al cambio di ruolo o d'azienda e, se il cambio e'
//        dell'UTENTE, ritira il valore che le voci nuove non contengono.
// ⭐ D-BE-2 (Tid, 2026-11-28, brief-db-utility-gestite-dall-emittente §11.4):
//    fino a quel giorno il valore restava, il campo sembrava vuoto e l'utility
//    partiva col salvataggio anche se la nuova azienda non la gestisce (il
//    super admin multi-azienda col default calcolato sul perimetro).
// ⛔ Il cambio dell'utente si riconosce perche' cambia la CHIAVE e NON il
//    valore: quando si apre un documento il form arriva intero, azienda e
//    utility nello stesso giro, e il valore salvato non si tocca. Ne' si tocca
//    un campo disabilitato (l'utility che viene dal cliente o dal documento),
//    ne' dopo una lettura fallita, che darebbe voci vuote.
watch(
  () => [props.tipoRuoloCodice, props.emittenteFiscaleId, props.modelValue],
  async (ora, prima) => {
    const chiaveCambiata = !prima || ora[0] !== prima[0] || ora[1] !== prima[1]
    if (!chiaveCambiata) return
    const cambioUtente = !!prima && ora[2] === prima[2]
    const letto = await load()
    if (!letto || !cambioUtente || props.disabled) return
    const valore = props.modelValue
    // `modelValue` ammette anche una stringa (un filtro letto dall'URL).
    if (valore == null || items.value.some(v => String(v[CAMPO_VALORE]) === String(valore))) return
    emit('update:modelValue', null)
    emit('change', null)
  },
  { immediate: true }
)

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
