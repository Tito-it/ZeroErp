<script setup>
// Scopo: Building block form universale per soggetto PF/PG/ENTE.
// Si adatta al tipo selezionato mostrando/nascondendo campi.
// Usa useSoggettoForm per stato e logica.

import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import ComuneAutocomplete from './ComuneAutocomplete.vue'

const { t } = useI18n()

const props = defineProps({
  form: { type: Object, required: true },
  tipiSoggetto: { type: Object, required: true },
  isPF: { type: Boolean, default: true },
  showPartitaIva: { type: Boolean, default: false },
  tipoForzato: { type: Number, default: null },
  disabled: { type: Boolean, default: false }
})

const sessoOptions = [
  { label: t('common.sesso_m'), value: 'M' },
  { label: t('common.sesso_f'), value: 'F' }
]
</script>

<template>
  <div class="soggetto-form">
    <!-- Select tipo soggetto (nascosto se forzato) -->
    <div v-if="!tipoForzato" class="field">
      <label>{{ t('common.tipo_soggetto') }} *</label>
      <Select
        v-model="form.tipo_soggetto_dettaglio_id"
        :options="tipiSoggetto.items.value"
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
      <div class="field">
        <label>{{ t('common.cognome') }} *</label>
        <InputText v-model="form.cognome" :disabled="disabled" class="w-full" />
      </div>
      <div class="field">
        <label>{{ t('common.nome') }} *</label>
        <InputText v-model="form.nome" :disabled="disabled" class="w-full" />
      </div>
      <div class="field">
        <label>{{ t('common.sesso') }}</label>
        <Select v-model="form.sesso" :options="sessoOptions"
          option-label="label" option-value="value" :disabled="disabled" class="w-full" />
      </div>
      <div class="field">
        <label>{{ t('common.data_nascita') }}</label>
        <DatePicker v-model="form.data_nascita" dateFormat="yy-mm-dd"
          :disabled="disabled" class="w-full" />
      </div>
      <div class="field">
        <label>{{ t('common.comune_nascita') }}</label>
        <ComuneAutocomplete v-model="form.comune_nascita_id" :disabled="disabled" />
      </div>
    </template>

    <!-- Sezione PG/ENTE -->
    <template v-else>
      <div class="field">
        <label>{{ t('common.ragione_sociale') }} *</label>
        <InputText v-model="form.ragione_sociale" :disabled="disabled" class="w-full" />
      </div>
    </template>

    <!-- Sempre visibili -->
    <div class="field">
      <label>{{ t('common.codice_fiscale') }} *</label>
      <InputText v-model="form.codice_fiscale" :disabled="disabled" class="w-full" />
    </div>
    <div v-if="showPartitaIva" class="field">
      <label>{{ t('common.partita_iva') }} *</label>
      <InputText v-model="form.partita_iva" :disabled="disabled" class="w-full" />
    </div>
    <div class="field">
      <label>{{ t('common.email') }} *</label>
      <InputText v-model="form.email" type="email" :disabled="disabled" class="w-full" />
    </div>
  </div>
</template>

<style scoped>
.soggetto-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.field label {
  font-weight: 600;
  font-size: 0.875rem;
}
</style>
