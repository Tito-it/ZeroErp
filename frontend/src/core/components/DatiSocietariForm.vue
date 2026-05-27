<script setup>
// Scopo: Building block form dati societari/camerali per PG/ENC.
// Forma giuridica, REA (provincia + iscrizione), capitale sociale,
// socio unico, liquidazione, destinatario FE (PEC/SDI).
// Visibilita' condizionale basata sulle policy della forma selezionata.

import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'

const { t } = useI18n()

// Form reattivo del padre via defineModel: il figlio muta `form.value.xxx`
// (oggetto condiviso per riferimento), senza violare no-mutating-props.
const form = defineModel('form', { type: Object, required: true })

defineProps({
  formeGiuridiche: { type: Array, default: () => [] },
  provinceLookup: { type: Object, default: null },
  showRea: { type: Boolean, default: false },
  requireRea: { type: Boolean, default: false },
  showCapitaleSociale: { type: Boolean, default: false },
  requireCapitaleSociale: { type: Boolean, default: false },
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false }
})

const socioUnicoOptions = computed(() => [
  { label: t('dati_societari.su_unico'), value: 'SU' },
  { label: t('dati_societari.su_piu_soci'), value: 'SM' }
])

const liquidazioneOptions = computed(() => [
  { label: t('dati_societari.liq_no'), value: 'LN' },
  { label: t('dati_societari.liq_si'), value: 'LS' }
])

const destinatarioFeOptions = computed(() => [
  { label: t('dati_societari.fe_pec'), value: 'P' },
  { label: t('dati_societari.fe_sdi'), value: 'C' }
])
</script>

<template>
  <div class="form-grid">
    <div class="form-field">
      <label>{{ t('dati_societari.forma_giuridica') }}{{ required ? ' *' : '' }}</label>
      <Select
        v-model="form.forma_giuridica_id"
        :options="formeGiuridiche"
        option-label="descrizione"
        option-value="id"
        :placeholder="t('dati_societari.select_forma_giuridica')"
        :disabled="disabled"
        filter
        class="w-full"
      />
    </div>

    <!-- REA (provincia + iscrizione) -->
    <template v-if="showRea">
      <div class="form-grid-2col">
        <div class="form-field" v-if="provinceLookup">
          <label>{{ t('dati_societari.prov_rea') }}{{ requireRea ? ' *' : '' }}</label>
          <Select
            v-model="form.id_prov_iscri_rea"
            :options="provinceLookup.items.value"
            :loading="provinceLookup.loading.value"
            option-label="descrizione"
            option-value="id"
            :placeholder="t('geo.select_regione')"
            :disabled="disabled"
            filter
            class="w-full"
          />
        </div>
        <div class="form-field">
          <label>{{ t('dati_societari.iscrizione_rea') }}{{ requireRea ? ' *' : '' }}</label>
          <InputText v-model="form.iscrizione_rea" :disabled="disabled" class="w-full" />
        </div>
      </div>
    </template>

    <!-- Capitale sociale -->
    <div v-if="showCapitaleSociale" class="form-field">
      <label>{{ t('dati_societari.capitale_sociale') }}{{ requireCapitaleSociale ? ' *' : '' }}</label>
      <InputNumber
        v-model="form.capitale_sociale"
        :disabled="disabled"
        mode="currency"
        currency="EUR"
        locale="it-IT"
        :min-fraction-digits="2"
        class="w-full"
      />
    </div>

    <!-- Socio unico + Liquidazione -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('dati_societari.socio_unico') }}</label>
        <Select
          v-model="form.socio_unico"
          :options="socioUnicoOptions"
          option-label="label"
          option-value="value"
          :disabled="disabled"
          class="w-full"
        />
      </div>
      <div class="form-field">
        <label>{{ t('dati_societari.liquidazione') }}</label>
        <Select
          v-model="form.liquidazione"
          :options="liquidazioneOptions"
          option-label="label"
          option-value="value"
          :disabled="disabled"
          class="w-full"
        />
      </div>
    </div>

    <!-- Fatturazione elettronica -->
    <div class="form-field">
      <label>{{ t('dati_societari.destinatario_fe') }}</label>
      <Select
        v-model="form.destinatario_fe"
        :options="destinatarioFeOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('dati_societari.select_destinatario_fe')"
        :disabled="disabled"
        show-clear
        class="w-full"
      />
    </div>

    <div class="form-grid-2col">
      <div v-if="form.destinatario_fe === 'P'" class="form-field">
        <label>{{ t('dati_societari.pec_fatturazione') }}</label>
        <InputText v-model="form.pec_fatturazione" :disabled="disabled" class="w-full" />
      </div>
      <div v-if="form.destinatario_fe === 'C'" class="form-field">
        <label>{{ t('dati_societari.codice_sdi') }}</label>
        <InputText v-model="form.codice_sdi" :disabled="disabled" class="w-full" />
      </div>
    </div>
  </div>
</template>

<!-- Stili .form-grid, .form-field, .form-grid-2col definiti in main.css -->
