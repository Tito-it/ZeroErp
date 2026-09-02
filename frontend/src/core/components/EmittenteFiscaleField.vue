<script setup>
// Scopo: Campo emittente fiscale, SEMPRE IN SOLA LETTURA. Rendering `<Select>`
//        con una sola opzione, che cambia sorgente a seconda del modo:
//
//         - edit:                     opzione sintetizzata dal record
//                                     (`emittente_fiscale_id/codice` + ragione
//                                     sociale denormalizzati dal BE detail).
//         - create:                   l'emittente della SESSIONE — quello di
//                                     permesso per l'operatore, quello scelto
//                                     in topbar per il super admin
//                                     (`auth.emittenteScritturaId`).
//
// ⛔ NON E' UNA SCELTA DI RIGA, ED E' LA DECISIONE DI TID DEL 2026-09-02.
//    Prima il super admin in create aveva una combo editabile sul lookup admin:
//    poteva creare il record dentro un emittente DIVERSO da quello in cui sta
//    lavorando — due verita' sullo stesso perimetro, nella stessa sessione, e
//    la seconda invisibile a chi guarda la topbar. L'emittente di lavoro si
//    sceglie una volta per sessione, e da li' comanda: chi vuole cambiarlo
//    passa dalla combo in alto, che chiede conferma e ricarica l'applicazione.
//
// ⚠️ Il lookup admin resta caricato nel ramo create+admin, ma solo per
//    RISOLVERE L'ETICHETTA dell'id attivo: `/me/` dice quale emittente e',
//    non come si chiama.
//
//        Beneficio rispetto al doppio rendering (InputText vs Select) usato
//        in passato: il display passa sempre da `formatEmittenteOptionLabel`,
//        single source di formattazione (`<ragione_sociale> (<codice>)`),
//        senza dipendere dal solo blob `auth.user.emittente.ragione_sociale_completa`
//        e senza branch di template duplicato.
//
//        Il componente NON applica autopopulate del modelValue: spetta
//        al consumer leggere `useEmittenteFiscaleField().defaultEmittenteId`
//        e impostarlo nel form prima del POST.
//
//        Modello permessi 1-a-1 documentato in stores/auth.js.

import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittenteFiscaleField } from '../composables/useEmittenteFiscaleField'
import { useAuthStore } from '../../stores/auth'
import Select from 'primevue/select'
import Message from 'primevue/message'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: [Number, null], default: null },
  // Record di dettaglio in edit (per leggere emittente_fiscale_codice e
  // emittente_ragione_sociale denormalizzati). Non usato in create.
  record: { type: Object, default: null },
  isEdit: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  // I18n keys overridable per riuso fuori dal contesto documenti.
  noneI18nKey: {
    type: String,
    default: 'config.modelli_documenti.field_emittente_none',
  },
  placeholderI18nKey: {
    type: String,
    default: 'config.modelli_documenti.field_emittente_placeholder',
  },
  errorI18nKey: { type: String, default: 'errors.lookup_load_failed' },
})
const emit = defineEmits(['update:modelValue'])

const {
  isAdminMode,
  currentEmittente,
  defaultEmittenteId,
  opzioneSessione,
  emittentiLoading,
  emittentiError,
  loadOptions,
  formatEmittenteOptionLabel,
} = useEmittenteFiscaleField()
const auth = useAuthStore()

// Il lookup admin serve solo a dare un NOME all'id attivo: l'operatore il nome
// ce l'ha gia' nel profilo, e in edit lo porta il record.
const useAdminLookup = computed(() => isAdminMode.value && !props.isEdit)

// Sintesi della singola option per i casi disabled (edit o operatore-mode).
// Riusa lo stesso shape del lookup admin (campi `id, codice, ragione_sociale`)
// cosi' il `formatEmittenteOptionLabel` produce display uniforme.
// La chiave `descrizione` e' stata tolta il 2026-08-02: era una copia dello
// stesso valore, tenuta in vita solo dal fallback del formatter — ora rimosso
// (`brief-emittente-ragione-sociale-dal-soggetto.md`). Il campo denormalizzato
// `emittente_ragione_sociale` porta gia' la ragione sociale del soggetto.
const recordAsOption = computed(() => {
  const r = props.record
  if (!r || r.emittente_fiscale_id == null) return null
  return {
    id: r.emittente_fiscale_id,
    codice: r.emittente_fiscale_codice ?? null,
    ragione_sociale: r.emittente_ragione_sociale ?? null,
  }
})

const operatoreAsOption = computed(() => {
  const ef = currentEmittente.value
  if (!ef || ef.id == null) return null
  return {
    id: ef.id,
    codice: ef.codice,
    ragione_sociale: ef.ragioneSociale,
  }
})

// L'emittente della SESSIONE come option, in create.
// ⚠️ Per il super admin il nome non arriva da `/me/` — che dichiara solo l'id —
//    ma dal lookup gia' caricato in questo ramo. Finche' non e' arrivato,
//    nessuna option: il Select mostra il placeholder invece di un id nudo.
const sessioneAsOption = computed(
  () => operatoreAsOption.value ?? opzioneSessione.value,
)

// Opzioni effettive: sempre UNA sola, perche' il campo non e' una scelta.
const finalOptions = computed(() => {
  const unica = props.isEdit ? recordAsOption.value : sessioneAsOption.value
  return unica ? [unica] : []
})

// ⛔ SEMPRE disabilitato: vedi l'intestazione — non esiste piu' un ramo in cui
//    questo campo si sceglie.
// ⚠️ Il prop `disabled` resta DICHIARATO ma non ha piu' effetto, e va detto: i
//    nove chiamanti lo passano ancora (`:disabled="isReadonly"`) e il
//    risultato non cambia, perche' `true` domina comunque. Toglierlo dalle
//    props non lo toglierebbe dai template: diventerebbe un attributo
//    `disabled` sul `<div>` esterno, cioe' rumore nel DOM al posto di un
//    contratto. Resta qui, dichiarato e inerte, finche' qualcuno non ripulisce
//    i chiamanti.
const isFieldDisabled = true

// La sessione non ha un emittente su cui scrivere. Non e' una combo vuota da
// riempire: e' una condizione da DIRE, perche' senza di quella il salvataggio
// verrebbe rifiutato dopo aver compilato tutto.
// ⚠️ Due testi, perche' sono due situazioni diverse e una sola frase ne
//    mentirebbe a meta': il super admin deve SCEGLIERE dalla topbar,
//    l'operatore non configurato non ha niente da scegliere.
// ⛔ La domanda e' «la sessione HA un emittente?», non «sono riuscito a
//    trovarne il nome»: guardare l'option era sbagliato in due modi, e li ho
//    scritti e corretti nella stessa passata. (1) mentre il lookup carica
//    l'option non c'e' ancora, e l'avviso lampeggiava su una sessione che un
//    emittente ce l'ha; (2) se il lookup FALLISCE l'option non arriva mai, e
//    l'avviso avrebbe detto «stai lavorando su tutti gli emittenti» — che e'
//    falso. Quel caso lo dice gia' il messaggio d'errore qui sopra.
const sessioneSenzaEmittente = computed(
  () => !props.isEdit && defaultEmittenteId.value == null,
)
const messaggioSenzaEmittente = computed(
  () => (auth.puoScegliereEmittente
    ? t('core.emittente_attivo.serve_per_creare')
    : t(props.noneI18nKey)),
)

const selectModel = computed({
  get: () => props.modelValue,
  set: v => emit('update:modelValue', v),
})

// Lazy load del lookup admin: parte solo nel ramo create+admin.
watch(
  useAdminLookup,
  value => {
    if (value) {
      loadOptions().catch(() => { /* errore visibile via emittentiError */ })
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="emittente-fiscale-field">
    <Select
      v-model="selectModel"
      :options="finalOptions"
      option-value="id"
      :option-label="formatEmittenteOptionLabel"
      :placeholder="t(placeholderI18nKey)"
      :loading="useAdminLookup && emittentiLoading"
      :disabled="isFieldDisabled"
      class="app-form-select"
      style="width: 100%; min-width: 0;"
    />
    <Message
      v-if="useAdminLookup && emittentiError"
      severity="error"
      :closable="false"
      class="mt-025"
    >
      {{ t(errorI18nKey) }}
    </Message>
    <Message
      v-else-if="sessioneSenzaEmittente"
      severity="warn"
      :closable="false"
      class="mt-025"
    >
      {{ messaggioSenzaEmittente }}
    </Message>
  </div>
</template>
