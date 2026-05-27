<script setup>
// Scopo: Building block form universale per soggetto PF/PG/ENTE.
// Si adatta al tipo selezionato mostrando/nascondendo campi.
// Include: generazione CF, validazione congruenza CF, check duplicati CF/PIVA.

import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { generaCF, validaCFPIVA } from '../../anagrafiche/api/anagrafiche'
import { toDateString, displayDate } from '../utils/date'
import { capitalizeWords, capitalizeFirst, blockNonAlphanumeric, normalizeUpperNoSpaces } from '../utils/string'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { DATE_FORMAT } from '../constants'
import ComuneAutocomplete from './ComuneAutocomplete.vue'

const { t } = useI18n()

// Form reattivo del padre via defineModel: il figlio muta `form.value.xxx`
// (oggetto condiviso per riferimento), senza violare no-mutating-props.
const form = defineModel('form', { type: Object, required: true })

const props = defineProps({
  tipiSoggetto: { type: Object, required: true },
  isPF: { type: Boolean, default: true },
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

const sessoOptions = [
  { label: t('common.sesso_m'), value: 'M' },
  { label: t('common.sesso_f'), value: 'F' }
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
  && form.value.sesso
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
        class="w-full"
      />
    </div>

    <!-- Sezione PF -->
    <template v-if="isPF">
      <div class="form-field">
        <label>{{ t('common.cognome') }} *</label>
        <InputText v-model="form.cognome" :disabled="disabled" class="w-full"
          @blur="form.cognome = capitalizeWords(form.cognome)" />
      </div>
      <div class="form-field">
        <label>{{ t('common.nome') }} *</label>
        <InputText v-model="form.nome" :disabled="disabled" class="w-full"
          @blur="form.nome = capitalizeWords(form.nome)" />
      </div>
      <div class="form-row-inline">
        <div class="form-field" style="flex: 0 0 8rem;">
          <label>{{ t('common.sesso') }}</label>
          <Select v-model="form.sesso" :options="sessoOptions"
            option-label="label" option-value="value" :disabled="disabled" class="w-full" />
        </div>
        <div class="form-field" style="flex: 1;">
          <label>{{ t('common.data_nascita') }}</label>
          <InputText v-if="disabled" :model-value="displayDate(form.data_nascita)" disabled class="w-full" />
          <DatePicker v-else v-model="form.data_nascita" :dateFormat="DATE_FORMAT"
            show-icon icon-display="input" show-button-bar :manual-input="true" class="w-full" />
        </div>
      </div>
      <div class="form-field">
        <label>{{ t('common.comune_nascita') }}</label>
        <ComuneAutocomplete v-model="form.comune_nascita_id" :disabled="disabled"
          :initial-item="comuneNascitaItem" />
      </div>
    </template>

    <!-- Sezione PG/ENTE -->
    <template v-else>
      <div class="form-field">
        <label>{{ t('common.ragione_sociale') }} *</label>
        <InputText v-model="form.ragione_sociale" :disabled="disabled" class="w-full"
          @blur="form.ragione_sociale = capitalizeFirst(form.ragione_sociale)" />
      </div>
    </template>

    <!-- CF + PIVA sulla stessa riga -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('common.codice_fiscale') }} *</label>
        <div class="app-input-with-action">
          <InputText v-model="form.codice_fiscale" :disabled="disabled || cfDisabled" class="w-full"
            @blur="onValidaCF"
            @keypress="blockNonAlphanumeric"
            @input="normalizeUpperNoSpaces(form, 'codice_fiscale')" />
          <Button
            v-if="isPF && !cfDisabled"
            icon="pi pi-bolt"
            :loading="cfLoading"
            :disabled="!canGeneraCF"
            @click="onGeneraCF"
            :title="t('soggetti.genera_cf')"
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
        <InputText v-model="form.partita_iva" :disabled="disabled || pivaDisabled" class="w-full"
          @blur="onValidaPIVA" />
        <Message v-for="(msg, i) in pivaMessages" :key="i" :severity="msg.severity" size="small" class="mt-1">
          {{ msg.text }}
        </Message>
      </div>
    </div>
  </div>
</template>

<!-- Stili .form-grid e .form-field definiti in main.css -->
