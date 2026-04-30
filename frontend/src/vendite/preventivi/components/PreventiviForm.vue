<script setup>
// Scopo: Form testata preventivo vendita — campi: utility, BA/cliente, validita', competenza,
// termini pagamento, valuta, fatturazione immediata. Usato dentro PreventiviDrawer.
//
// Granularita' disabilitazione (Fase 1):
//   - isModificabile: stato globale del form (legato a can_edit_testata + readonly area)
//   - nonEditableFields: whitelist per-campo dal backend (script.fn_available_actions_preventivo)
//     Un campo e' disabled se !isModificabile OPPURE se compare in nonEditableFields.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { DATE_FORMAT } from '../../../core/constants'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()

const props = defineProps({
  form: { type: Object, required: true },
  isEdit: { type: Boolean, default: false },
  isModificabile: { type: Boolean, default: true },
  nonEditableFields: { type: Array, default: () => [] },
})

// Lookup O(1) per campo non editabile.
const lockedFields = computed(() => new Set(props.nonEditableFields))
function isLocked(field) {
  return !props.isModificabile || lockedFields.value.has(field)
}
</script>

<template>
  <div class="form-grid">
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.field_utility') }}</label>
        <UtilityPerRuoloSelect v-model="form.utility_id"
          :placeholder="t('preventivi.field_utility')"
          :disabled="isEdit || isLocked('utility_id')" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.field_billing_account') }}</label>
        <InputNumber v-model="form.billing_account_id"
          :disabled="isLocked('billing_account_id')"
          :placeholder="t('preventivi.field_billing_account')" :use-grouping="false" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.field_validita_dal') }}</label>
        <DatePicker v-model="form.validita_dal" :date-format="DATE_FORMAT"
          show-icon show-button-bar :disabled="isLocked('validita_dal')" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.field_validita_al') }}</label>
        <DatePicker v-model="form.validita_al" :date-format="DATE_FORMAT"
          show-icon show-button-bar :disabled="isLocked('validita_al')" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.field_competenza') }}</label>
        <DatePicker v-model="form.competenza_mese" :date-format="DATE_FORMAT"
          show-icon show-button-bar view="month" :disabled="isLocked('competenza_mese')" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.field_valuta') }}</label>
        <LookupSelect v-model="form.valuta_id" rel="config.valute"
          :placeholder="t('preventivi.field_valuta')" :disabled="isLocked('valuta_id')"
          show-clear />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.field_termini_pagamento') }}</label>
        <LookupSelect v-model="form.termine_pagamento_id" rel="config.termini_pagamento"
          :placeholder="t('preventivi.field_termini_pagamento')"
          :disabled="isLocked('termine_pagamento_id')" show-clear />
      </div>
      <div class="form-field" style="display: flex; align-items: center; gap: 0.5rem; padding-top: 1.5rem;">
        <ToggleSwitch v-model="form.fatturazione_immediata"
          :disabled="isLocked('fatturazione_immediata')" />
        <label>{{ t('preventivi.field_fatturazione_immediata') }}</label>
      </div>
    </div>
  </div>
</template>
