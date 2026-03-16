<script setup>
// Scopo: Building block form contatto riutilizzabile.
// Associabile a soggetto, ruolo o utility. Campi adattabili via props.
// Usa useContattoForm per stato e lookup.

import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'

const { t } = useI18n()

defineProps({
  form: { type: Object, required: true },
  tipiContatto: { type: Object, required: true },
  unitaOrganizzative: { type: Object, default: null },
  requireEmail: { type: Boolean, default: false },
  showUO: { type: Boolean, default: true },
  tipoDisabled: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false }
})
</script>

<template>
  <div class="form-grid">
    <div class="form-field">
      <label>{{ t('contatto.nominativo') }} *</label>
      <InputText v-model="form.nominativo" :disabled="disabled" class="w-full" />
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('common.email') }}{{ requireEmail ? ' *' : '' }}</label>
        <InputText v-model="form.email" :disabled="disabled" class="w-full" />
      </div>
      <div class="form-field">
        <label>{{ t('common.pec') }}</label>
        <InputText v-model="form.pec" :disabled="disabled" class="w-full" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('common.telefono') }}</label>
        <InputText v-model="form.telefono" :disabled="disabled" class="w-full" />
      </div>
      <div class="form-field">
        <label>{{ t('contatto.cellulare') }}</label>
        <InputText v-model="form.cellulare" :disabled="disabled" class="w-full" />
      </div>
    </div>

    <div class="form-field">
      <label>{{ t('contatto.tipo_contatto') }}</label>
      <Select
        v-model="form.tipo_contatto_id"
        :options="tipiContatto.items.value"
        :loading="tipiContatto.loading.value"
        option-label="descrizione"
        option-value="id"
        :placeholder="t('contatto.select_tipo_contatto')"
        :disabled="disabled || tipoDisabled"
        show-clear
        class="w-full"
      />
    </div>

    <div v-if="showUO && unitaOrganizzative" class="form-field">
      <label>{{ t('contatto.unita_organizzativa') }}</label>
      <Select
        v-model="form.unita_organizzativa_id"
        :options="unitaOrganizzative.items.value"
        :loading="unitaOrganizzative.loading.value"
        option-label="descrizione"
        option-value="id"
        :placeholder="t('contatto.select_unita_organizzativa')"
        :disabled="disabled"
        show-clear
        class="w-full"
      />
    </div>

    <div class="form-field">
      <label>{{ t('contatto.note') }}</label>
      <Textarea v-model="form.note" :disabled="disabled" rows="2" class="w-full" />
    </div>
  </div>
</template>

<!-- Stili .form-grid, .form-field, .form-grid-2col definiti in main.css -->
