<script setup>
// Scopo: Building block form dati societari/camerali per PG/ENC.
// Forma giuridica, REA (provincia + iscrizione), capitale sociale,
// socio unico, liquidazione, destinatario FE (PEC/SDI).
// Visibilita' condizionale basata sulle policy della forma selezionata.

import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import InputMaiuscolo from '../../core/components/InputMaiuscolo.vue'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import { DATE_FORMAT } from '../../core/constants'
import { toDateString, parseIsoDate } from '../../core/utils/date'

const { t } = useI18n()

// Form reattivo del padre via defineModel: il figlio muta `form.value.xxx`
// (oggetto condiviso per riferimento), senza violare no-mutating-props.
const form = defineModel('form', { type: Object, required: true })

defineProps({
  // Campi che il BACKEND indica come da correggere (envelope `error.fields`),
  // dal padre via `useApiHandler().campiErrati`. Qui li manda il guard del
  // canale FE (`anagrafiche.trgfn_dati_societari_guard_canale_fe`): canale `C`
  // senza codice o codice fuori forma -> `codice_sdi`, canale `P` senza PEC ->
  // `pec_fatturazione`. Dal 2026-10-10 anche il guard della forma giuridica
  // (`trgfn_dati_societari_guard_forma_giuridica`): forma non ammessa dalla
  // natura -> `forma_giuridica_id`, REA o capitale contro la regola della
  // forma -> `iscrizione_rea` / `capitale_sociale`.
  campiErrati: { type: Array, default: () => [] },
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
    <!-- Forma giuridica + Data di costituzione. La data c'e' in creazione e in
         modifica, come il resto della sezione: fino al 2026-10-22 solo in
         modifica, la porta di creazione non la riceveva
         (brief-db-dati-societari-in-creazione §1.2). -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('dati_societari.forma_giuridica') }}{{ required ? ' *' : '' }}</label>
        <Select
          v-model="form.forma_giuridica_id"
          :options="formeGiuridiche"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('dati_societari.select_forma_giuridica')"
          :invalid="campiErrati.includes('forma_giuridica_id')"
          :disabled="disabled"
          filter
        />
      </div>
      <div class="form-field">
        <label>{{ t('dati_societari.data_costituzione') }}</label>
        <DatePicker :model-value="parseIsoDate(form.data_costituzione)"
          @update:model-value="form.data_costituzione = toDateString($event)"
          :date-format="DATE_FORMAT" show-icon show-button-bar :disabled="disabled" />
      </div>
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
            :invalid="campiErrati.includes('id_prov_iscri_rea')"
            :disabled="disabled"
            filter
          />
        </div>
        <div class="form-field">
          <label>{{ t('dati_societari.iscrizione_rea') }}{{ requireRea ? ' *' : '' }}</label>
          <InputText v-model="form.iscrizione_rea"
            :invalid="campiErrati.includes('iscrizione_rea')" :disabled="disabled" />
        </div>
      </div>
    </template>

    <!-- Capitale sociale -->
    <div v-if="showCapitaleSociale" class="form-field">
      <label>{{ t('dati_societari.capitale_sociale') }}{{ requireCapitaleSociale ? ' *' : '' }}</label>
      <InputNumber
        v-model="form.capitale_sociale"
        :invalid="campiErrati.includes('capitale_sociale')"
        :disabled="disabled"
        mode="currency"
        currency="EUR"
        locale="it-IT"
        :min-fraction-digits="2"
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
        />
      </div>
    </div>

    <!-- Fatturazione elettronica: il canale e, accanto, il recapito che il
         canale chiede (PEC per `P`, codice SDI per `C`). -->
    <div class="form-grid-2col">
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
        />
      </div>
      <div v-if="form.destinatario_fe === 'P'" class="form-field">
        <label>{{ t('dati_societari.pec_fatturazione') }}</label>
        <InputText
          v-model="form.pec_fatturazione"
          :invalid="campiErrati.includes('pec_fatturazione')"
          :disabled="disabled"
        />
      </div>
      <div v-if="form.destinatario_fe === 'C'" class="form-field">
        <label>{{ t('dati_societari.codice_sdi') }}</label>
        <!-- Il codice SDI e' in maiuscolo (lettere e cifre, 7 o 6 per la PA):
             lo si trasforma mentre si digita. La forma la decide il DB. -->
        <InputMaiuscolo
          v-model="form.codice_sdi"
          :invalid="campiErrati.includes('codice_sdi')"
          maxlength="7"
          :disabled="disabled"
        />
      </div>
    </div>
  </div>
</template>

<!-- Stili .form-grid, .form-field, .form-grid-2col definiti in main.css -->
