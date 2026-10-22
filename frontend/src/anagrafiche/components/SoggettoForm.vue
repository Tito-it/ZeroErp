<script setup>
// Scopo: Building block form universale per soggetto PF/PG/ENTE.
// Si adatta al tipo selezionato mostrando/nascondendo campi.
// Include: generazione CF, validazione congruenza CF, check duplicati CF/PIVA.

import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { generaCF, validaCFPIVA } from '../api/anagrafiche'
import { toDateString, displayDate } from '../../core/utils/date'
import { capitalizeWords, capitalizeFirst, blockNonAlphanumeric, normalizeUpperNoSpaces } from '../../core/utils/string'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { DATE_FORMAT, MANAGE_ICONS } from '../../core/constants'
import ComuneAutocomplete from './ComuneAutocomplete.vue'

const { t } = useI18n()

// Form reattivo del padre via defineModel: il figlio muta `form.value.xxx`
// (oggetto condiviso per riferimento), senza violare no-mutating-props.
const form = defineModel('form', { type: Object, required: true })

const props = defineProps({
  // Campi che il BACKEND indica come da correggere (envelope `error.fields`).
  // Arrivano dal padre, che li prende da `useApiHandler().campiErrati`: questo
  // e' un form condiviso e non chiama le API da solo.
  // ⚠️ Qui il caso vive sul percorso DB: `script.fn_validate_cf_piva_it`
  // solleva `E_CF_NON_VALIDO` con `COLUMN = codice_fiscale`, e il nome arriva
  // fino a qui senza che nessuno lo scriva in Python.
  campiErrati: { type: Array, default: () => [] },
  tipiSoggetto: { type: Object, required: true },
  isPF: { type: Boolean, default: true },
  // Dalla `sesso_policy` del tipo scelto, decisa in `useSoggettoForm`:
  // NONE -> campo nascosto, REQUIRED -> asterisco, OPTIONAL -> vuoto ammesso.
  showSesso: { type: Boolean, default: false },
  requireSesso: { type: Boolean, default: false },
  showPartitaIva: { type: Boolean, default: false },
  tipoForzato: { type: Number, default: null },
  tipiAmmessiIds: { type: Array, default: null },
  // Fase 6 B3: ids dei tipi modificabili in edit (backend-driven, stessa
  // natura del soggetto corrente). Sostituisce il filtro client-side
  // basato su natura_soggetto.
  tipiModificabiliIds: { type: Array, default: null },
  // Fase 6 B4: lista dei campi non modificabili per questo soggetto
  // (es. ['codice_fiscale', 'partita_iva']). Backend-driven.
  // null = non popolato (create mode o legacy) → fallback alla regola
  // cablata. [] = popolato vuoto (edit con CF/PIVA mancanti) → niente
  // bloccato. Coerente con tipiModificabiliIds.
  nonEditableFields: { type: Array, default: null },
  isEdit: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  comuneNascitaItem: { type: Object, default: null }
})

// `X`: il sesso serve ma non si puo' stabilire (dati storici, CF estero o non
// riconoscibile). Lo si sceglie esplicitamente; il vuoto vuol dire «non serve».
const sessoOptions = [
  { label: t('common.sesso_m'), value: 'M' },
  { label: t('common.sesso_f'), value: 'F' },
  { label: t('common.sesso_x'), value: 'X' }
]

// CF/PIVA bloccati: regola backend-driven via non_editable_fields (Fase 6 B4).
// nonEditableFields === null → fallback al cablato (create o legacy);
// nonEditableFields === [] → backend ha risposto, niente bloccato;
// nonEditableFields === [...] → backend ha indicato i campi bloccati.
const cfDisabled = computed(() => {
  if (props.nonEditableFields !== null) return props.nonEditableFields.includes('codice_fiscale')
  return props.isEdit && !!form.value.codice_fiscale?.trim()
})
const pivaDisabled = computed(() => {
  if (props.nonEditableFields !== null) return props.nonEditableFields.includes('partita_iva')
  return props.isEdit && !!form.value.partita_iva?.trim()
})

// Tipo soggetto filtrato: per ids ammessi (resolver) o tipi_modificabili_ids (edit, backend-driven).
const tipiSoggettoFiltrati = computed(() => {
  if (!props.tipiSoggetto.items?.value) return props.tipiSoggetto
  // Filtro per ids ammessi dal config-resolver (creazione da resolver)
  if (props.tipiAmmessiIds && props.tipiAmmessiIds.length) {
    return {
      ...props.tipiSoggetto,
      items: { value: props.tipiSoggetto.items.value.filter(t => props.tipiAmmessiIds.includes(t.id)) },
    }
  }
  if (!props.isEdit) return props.tipiSoggetto
  // Edit: filtra con tipi_modificabili_ids dal backend (Fase 6 B3).
  if (props.tipiModificabiliIds?.length) {
    return {
      ...props.tipiSoggetto,
      items: { value: props.tipiSoggetto.items.value.filter(t => props.tipiModificabiliIds.includes(t.id)) },
    }
  }
  // Fallback compat: filtro per natura compatibile (vecchia logica)
  const current = props.tipiSoggetto.items.value.find(t => t.id === form.value.tipo_soggetto_dettaglio_id)
  if (!current) return props.tipiSoggetto
  const naturaCorrente = current.natura_soggetto
  return {
    ...props.tipiSoggetto,
    items: { value: props.tipiSoggetto.items.value.filter(t => t.natura_soggetto === naturaCorrente) },
  }
})

// === Genera CF ===
const cfLoading = ref(false)
const canGeneraCF = computed(() =>
  props.isPF
  && form.value.cognome?.trim()
  && form.value.nome?.trim()
  // Il CF codifica solo M e F: con X (o vuoto) non si calcola.
  && ['M', 'F'].includes(form.value.sesso)
  && form.value.data_nascita
  && form.value.comune_nascita_id
  && !props.disabled
)

async function onGeneraCF() {
  if (!canGeneraCF.value) return
  cfLoading.value = true
  try {
    const res = await generaCF({
      cognome: form.value.cognome.trim(),
      nome: form.value.nome.trim(),
      sesso: form.value.sesso,
      data_nascita: toDateString(form.value.data_nascita),
      comune_nascita_id: form.value.comune_nascita_id,
    })
    form.value.codice_fiscale = res.data.data.codice_fiscale
    onValidaCF()
  } catch {
    cfMessages.value = [{ severity: 'error', text: 'Errore generazione codice fiscale.' }]
  } finally {
    cfLoading.value = false
  }
}

// === Validazione CF/PIVA ===
const cfMessages = ref([])
const pivaMessages = ref([])

// ⚠️ TERZA SORGENTE DI ERRORE SU QUESTO CAMPO, e non passa da `useApiHandler`.
// `onValidaCF` chiama un endpoint che risponde **200** con
// `{errors, warnings}` nel payload: e' un REFERTO, non un errore HTTP. Quindi
// il `catch` non scatta mai e `campiErrati` resta vuoto — il messaggio
// compariva sotto il campo, ma l'input non si accendeva.
// Le due sorgenti sono complementari e servono entrambe:
//   - qui (al `blur`): il referto, prima di salvare;
//   - `campiErrati` (al salvataggio): il guard del database
//     (`fn_validate_cf_piva_it` -> `E_CF_NON_VALIDO` + `COLUMN`).
// ⚠️ Solo `severity: 'error'`: un warning non deve accendere il campo, o il
// rosso smette di voler dire «questo va corretto».
const cfHaErrore = computed(() => cfMessages.value.some(m => m.severity === 'error'))

async function onValidaCF() {
  const cf = (form.value.codice_fiscale || '').trim()
  if (cf.length < 16) { cfMessages.value = []; return }
  try {
    const res = await validaCFPIVA({
      codice_fiscale: cf,
      sesso: form.value.sesso || null,
      data_nascita: toDateString(form.value.data_nascita),
      comune_nascita_id: form.value.comune_nascita_id || null,
    })
    const data = res.data.data
    cfMessages.value = [
      ...data.errors.filter(e => e.field === 'codice_fiscale').map(e => ({ severity: 'error', text: e.message })),
      ...data.warnings.filter(w => w.field === 'codice_fiscale').map(w => ({ severity: 'warn', text: w.message })),
    ]
  } catch {
    cfMessages.value = []
  }
}

async function onValidaPIVA() {
  const piva = (form.value.partita_iva || '').trim()
  if (piva.length < 11) { pivaMessages.value = []; return }
  try {
    const res = await validaCFPIVA({ partita_iva: piva })
    const data = res.data.data
    pivaMessages.value = data.warnings
      .filter(w => w.field === 'partita_iva')
      .map(w => ({ severity: 'warn', text: w.message }))
  } catch {
    pivaMessages.value = []
  }
}
</script>

<template>
  <div class="form-grid">
    <!-- Select tipo soggetto (nascosto se forzato) -->
    <div v-if="!tipoForzato" class="form-field">
      <label>{{ t('common.tipo_soggetto') }} *</label>
      <Select
        v-model="form.tipo_soggetto_dettaglio_id"
        :options="tipiSoggettoFiltrati.items.value"
        :loading="tipiSoggetto.loading.value"
        option-label="descrizione"
        option-value="id"
        :placeholder="t('common.select_tipo_soggetto')"
        :disabled="disabled"
      />
    </div>

    <!-- Sezione PF -->
    <template v-if="isPF">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('common.cognome') }} *</label>
          <InputText v-model="form.cognome" :disabled="disabled"
            @blur="form.cognome = capitalizeWords(form.cognome)" />
        </div>
        <div class="form-field">
          <label>{{ t('common.nome') }} *</label>
          <InputText v-model="form.nome" :disabled="disabled"
            @blur="form.nome = capitalizeWords(form.nome)" />
        </div>
      </div>
      <!-- Sesso, data e comune di nascita su una riga (~25/30/45): `flex-basis`
           0 e i pesi danno le proporzioni; senza il sesso (natura che non lo
           prevede) data e comune si dividono la riga negli stessi rapporti. -->
      <div class="form-row-inline">
        <div v-if="showSesso" class="form-field" style="flex: 25 1 0; min-width: 0;">
          <label>{{ t('common.sesso') }}{{ requireSesso ? ' *' : '' }}</label>
          <Select v-model="form.sesso" :options="sessoOptions"
            option-label="label" option-value="value" :disabled="disabled"
            :show-clear="!requireSesso && !disabled"
            :invalid="campiErrati.includes('sesso')" />
        </div>
        <div class="form-field" style="flex: 30 1 0; min-width: 0;">
          <label>{{ t('common.data_nascita') }}</label>
          <InputText v-if="disabled" :model-value="displayDate(form.data_nascita)" disabled />
          <DatePicker v-else v-model="form.data_nascita" :dateFormat="DATE_FORMAT"
            show-icon icon-display="input" show-button-bar :manual-input="true" />
        </div>
        <div class="form-field" style="flex: 45 1 0; min-width: 0;">
          <label>{{ t('common.comune_nascita') }}</label>
          <ComuneAutocomplete v-model="form.comune_nascita_id" :disabled="disabled"
            :initial-item="comuneNascitaItem" />
        </div>
      </div>
    </template>

    <!-- Sezione PG/ENTE -->
    <template v-else>
      <div class="form-field">
        <label>{{ t('common.ragione_sociale') }} *</label>
        <InputText v-model="form.ragione_sociale" :disabled="disabled"
          @blur="form.ragione_sociale = capitalizeFirst(form.ragione_sociale)" />
      </div>
    </template>

    <!-- CF + PIVA sulla stessa riga -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('common.codice_fiscale') }} *</label>
        <div class="app-input-with-action">
          <InputText v-model="form.codice_fiscale" :disabled="disabled || cfDisabled"
            :invalid="campiErrati.includes('codice_fiscale') || cfHaErrore"
            @blur="onValidaCF"
            @keypress="blockNonAlphanumeric"
            @input="normalizeUpperNoSpaces(form, 'codice_fiscale')" />
          <Button
            v-if="isPF && !cfDisabled"
            :icon="MANAGE_ICONS.GENERA"
            :loading="cfLoading"
            :disabled="!canGeneraCF"
            @click="onGeneraCF"
            :title="t('anagrafiche.soggetti.genera_cf')"
            text
            rounded
            size="small"
            class="app-action-btn"
          />
        </div>
        <Message v-for="(msg, i) in cfMessages" :key="i" :severity="msg.severity" size="small" class="mt-1">
          {{ msg.text }}
        </Message>
      </div>

      <div v-if="showPartitaIva" class="form-field">
        <label>{{ t('common.partita_iva') }} *</label>
        <InputText v-model="form.partita_iva" :disabled="disabled || pivaDisabled"
          :invalid="campiErrati.includes('partita_iva')"
          @blur="onValidaPIVA" />
        <Message v-for="(msg, i) in pivaMessages" :key="i" :severity="msg.severity" size="small" class="mt-1">
          {{ msg.text }}
        </Message>
      </div>
    </div>
  </div>
</template>

<!-- Stili .form-grid e .form-field definiti in main.css -->
