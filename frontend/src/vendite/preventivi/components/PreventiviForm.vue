<script setup>
// Scopo: Form testata preventivo vendita — campi: utility, BA/cliente, validita', competenza,
// termini pagamento, valuta, fatturazione immediata. Usato dentro PreventiviDrawer.
import { useI18n } from 'vue-i18n'
import { DATE_FORMAT } from '../../../core/constants'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()

const props = defineProps({
  form: { type: Object, required: true },
  isEdit: { type: Boolean, default: false },
  isModificabile: { type: Boolean, default: true }
})
</script>

<template>
  <div class="form-grid">
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.field_utility') }}</label>
        <LookupSelect v-model="form.utility_id" rel="config.utilities"
          :placeholder="t('preventivi.field_utility')" :disabled="isEdit" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.field_billing_account') }}</label>
        <InputNumber v-model="form.billing_account_id" :disabled="!isModificabile"
          :placeholder="t('preventivi.field_billing_account')" :use-grouping="false" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.field_validita_dal') }}</label>
        <DatePicker v-model="form.validita_dal" :date-format="DATE_FORMAT"
          show-icon show-button-bar :disabled="!isModificabile" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.field_validita_al') }}</label>
        <DatePicker v-model="form.validita_al" :date-format="DATE_FORMAT"
          show-icon show-button-bar :disabled="!isModificabile" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.field_competenza') }}</label>
        <DatePicker v-model="form.competenza_mese" :date-format="DATE_FORMAT"
          show-icon show-button-bar view="month" :disabled="!isModificabile" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.field_valuta') }}</label>
        <LookupSelect v-model="form.valuta_id" rel="config.valute"
          :placeholder="t('preventivi.field_valuta')" :disabled="!isModificabile" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.field_termini_pagamento') }}</label>
        <LookupSelect v-model="form.termine_pagamento_id" rel="config.termini_pagamento"
          :placeholder="t('preventivi.field_termini_pagamento')" :disabled="!isModificabile" />
      </div>
      <div class="form-field" style="display: flex; align-items: center; gap: 0.5rem; padding-top: 1.5rem;">
        <ToggleSwitch v-model="form.fatturazione_immediata" :disabled="!isModificabile" />
        <label>{{ t('preventivi.field_fatturazione_immediata') }}</label>
      </div>
    </div>
  </div>
</template>
