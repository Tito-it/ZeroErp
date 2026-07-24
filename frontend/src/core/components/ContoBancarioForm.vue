<script setup>
// Scopo: Building block form conto bancario riutilizzabile.
// Associabile a soggetto o ruolo. IBAN con autocomplete server-side.
// Filiale con autocomplete server-side. Uso con dropdown fisso.

import { useI18n } from 'vue-i18n'
import { useServerAutocomplete } from '../composables/useServerAutocomplete'
import { lookupContiBancari, lookupBankBranches } from '../../anagrafiche/api/anagrafiche'
import { DATE_FORMAT, FIELD_LENGTH } from '../constants'
import { blockNonAlphanumeric, normalizeUpperNoSpaces } from '../utils/string'
import AutoComplete from 'primevue/autocomplete'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Checkbox from 'primevue/checkbox'

const { t } = useI18n()

// Form reattivo del padre via defineModel: il figlio muta `form.value.xxx`
// (oggetto condiviso per riferimento), senza violare no-mutating-props.
const form = defineModel('form', { type: Object, required: true })

const props = defineProps({
  usiDisponibili: { type: Array, required: true },
  disabled: { type: Boolean, default: false },
  errors: { type: Array, default: () => [] }
})

const emit = defineEmits(['iban-select', 'iban-clear', 'branch-select'])

// Autocomplete IBAN — cerca nel registro conti_bancari
const ibanAc = useServerAutocomplete(
  (query) => lookupContiBancari(query),
  { minLength: 4 }
)

// Autocomplete filiale — cerca in bank_branches
const branchAc = useServerAutocomplete(
  (query) => lookupBankBranches(query),
  { minLength: 2 }
)

// Scopo: Quando l'utente seleziona un IBAN dalla lista autocomplete.
function onIbanItemSelect(event) {
  emit('iban-select', event.value)
}

// Scopo: Quando l'utente pulisce o modifica l'IBAN manualmente.
function onIbanChange() {
  emit('iban-clear')
}

// Scopo: Quando l'utente seleziona una filiale dalla lista autocomplete.
function onBranchItemSelect(event) {
  emit('branch-select', event.value)
}

// Opzioni dropdown uso tradotte
const usiOptions = props.usiDisponibili.map(u => ({
  value: u,
  label: t(`anagrafiche.conti_bancari.uso_${u.toLowerCase()}`)
}))

// Scopo: Label per autocomplete filiale — usata da optionLabel.
function branchOptionLabel(item) {
  if (!item) return ''
  if (typeof item === 'string') return item
  if (item.bank_code) return `${item.filiale_nome} (${item.bank_code})`
  return item.filiale_nome || ''
}

// Scopo: Label per autocomplete IBAN — usata da optionLabel.
function ibanOptionLabel(item) {
  if (!item) return ''
  if (typeof item === 'string') return item
  return item.iban || ''
}




</script>

<template>
  <div class="form-grid">
    <!-- Riga 1: Uso + Predefinito -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('anagrafiche.conti_bancari.uso') }} *</label>
        <Select
          v-model="form.uso"
          :options="usiOptions"
          option-label="label"
          option-value="value"
          :disabled="disabled"
          class="w-full"
          :invalid="errors.includes('uso')"
        />
      </div>
      <div class="form-field" style="justify-content: flex-end;">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <Checkbox v-model="form.predefinito" :binary="true" :disabled="disabled"
            input-id="cb-predefinito"
            @update:model-value="v => { if (v) form.bloccato = false }" />
          <label for="cb-predefinito">{{ t('anagrafiche.conti_bancari.predefinito') }}</label>
        </div>
      </div>
    </div>

    <!-- Riga 2: Intestatario predefinito -->
    <div class="form-field">
      <label>{{ t('anagrafiche.conti_bancari.intestatario') }}</label>
      <InputText v-model="form.intestatario_predefinito" :disabled="disabled" class="w-full" />
    </div>

    <!-- Riga 3: Intestazione dichiarata -->
    <div class="form-field">
      <label>{{ t('anagrafiche.conti_bancari.intestazione_dichiarata') }}</label>
      <InputText v-model="form.intestazione_dichiarata" :disabled="disabled" class="w-full" />
    </div>

    <!-- Riga 4: Banca/Filiale con autocomplete -->
    <div class="form-field">
      <label>{{ t('anagrafiche.conti_bancari.banca_filiale') }} *</label>
      <AutoComplete
        v-model="form.bank_branch_obj"
        :suggestions="branchAc.suggestions.value"
        :loading="branchAc.loading.value"
        :option-label="branchOptionLabel"
        :placeholder="t('anagrafiche.conti_bancari.banca_filiale')"
        :disabled="disabled"
        class="w-full"
        :invalid="errors.includes('bank_branch_id')"
        :min-length="2"
        force-selection
        fluid
        @complete="branchAc.onSearch"
        @item-select="onBranchItemSelect"
      />
    </div>

    <!-- Riga 5: IBAN (largo) + BIC/SWIFT (corto) -->
    <div class="form-grid-2col cb-iban-row">
      <div class="form-field">
        <label>{{ t('anagrafiche.conti_bancari.iban') }} *</label>
        <AutoComplete
          v-model="form.iban"
          :suggestions="ibanAc.suggestions.value"
          :loading="ibanAc.loading.value"
          :option-label="ibanOptionLabel"
          :placeholder="t('anagrafiche.conti_bancari.iban')"
          :disabled="disabled"
          class="w-full"
          :invalid="errors.includes('iban') || errors.includes('iban_format')"
          :min-length="4"
          :inputProps="{ maxlength: FIELD_LENGTH.IBAN_MAX }"
          fluid
          @complete="ibanAc.onSearch"
          @item-select="onIbanItemSelect"
          @change="onIbanChange"
          @keypress="blockNonAlphanumeric"
          @input="normalizeUpperNoSpaces(form, 'iban')"
        />
        <small v-if="errors.includes('iban_format')" class="app-field-error">
          {{ t('anagrafiche.conti_bancari.iban_formato_errore') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('anagrafiche.conti_bancari.bic_swift') }}</label>
        <InputText v-model="form.bic_swift" :disabled="disabled" class="w-full" />
      </div>
    </div>

    <!-- Riga 6: Valido dal + Valido al -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('anagrafiche.conti_bancari.valido_dal') }}</label>
        <DatePicker v-model="form.valido_dal" :date-format="DATE_FORMAT"
          :disabled="disabled" show-icon icon-display="input" class="w-full" />
      </div>
      <div class="form-field">
        <label>{{ t('anagrafiche.conti_bancari.valido_al') }}</label>
        <DatePicker v-model="form.valido_al" :date-format="DATE_FORMAT"
          :disabled="disabled" show-icon icon-display="input" class="w-full"
          :invalid="errors.includes('date_range')" />
      </div>
    </div>

    <!-- Riga 7: Verificato + Bloccato -->
    <div class="form-grid-2col">
      <div class="form-field">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <Checkbox v-model="form.verificato" :binary="true" :disabled="disabled"
            input-id="cb-verificato" />
          <label for="cb-verificato">{{ t('anagrafiche.conti_bancari.verificato') }}</label>
        </div>
      </div>
      <div class="form-field">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <Checkbox v-model="form.bloccato" :binary="true" :disabled="disabled"
            input-id="cb-bloccato"
            @update:model-value="v => { if (v) form.predefinito = false }" />
          <label for="cb-bloccato">{{ t('anagrafiche.conti_bancari.bloccato') }}</label>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cb-iban-row {
  grid-template-columns: 2fr 1fr !important;
}
</style>
