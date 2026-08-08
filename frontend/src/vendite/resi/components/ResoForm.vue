<script setup>
// Scopo: Form testata reso — quasi tutta DISPLAY-ONLY: il reso eredita
// cliente/destinatario/utility/valuta/emittente dal DDT sorgente (trigger DB
// normalize) e i campi sono immutabili (non_editable_fields BE). L'unico
// campo editabile in DRAFT e' la data documento. Usato dentro ResoDrawer.
import { useI18n } from 'vue-i18n'
import { DATE_FORMAT } from '../../../core/constants'
import EmittenteFiscaleField from '../../../core/components/EmittenteFiscaleField.vue'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

const { t } = useI18n()

const form = defineModel('form', { type: Object, required: true })

defineProps({
  // Campi che il BACKEND indica come da correggere (envelope `error.fields`).
  // Arrivano dal padre: questo componente non chiama le API da solo.
  campiErrati: { type: Array, default: () => [] },
  isModificabile: { type: Boolean, default: true },
  // Detail testata (vw_resi_lista) per i display denormalizzati.
  record: { type: Object, default: null },
})
</script>

<template>
  <div class="form-grid">
    <div class="form-grid-2col">
      <!-- Emittente ereditato dal DDT sorgente: sempre display denormalizzato. -->
      <div class="form-field">
        <label>{{ t('vendite.resi.field_emittente_fiscale') }}</label>
        <EmittenteFiscaleField
          v-model="form.emittente_fiscale_id"
          :record="record"
          :is-edit="true"
          disabled />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.resi.field_data') }}</label>
        <DatePicker v-model="form.data"
        :invalid="campiErrati.includes('data')" :date-format="DATE_FORMAT"
          show-icon show-button-bar :disabled="!isModificabile" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.resi.field_billing_account') }}</label>
        <InputText :model-value="record?.ba_codice || '—'" disabled />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.resi.field_destinatario') }}</label>
        <InputText :model-value="record?.destinatario_denominazione || '—'" disabled />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.resi.field_ddt_origine') }}</label>
        <InputText :model-value="record?.ddt_origine_numero || '—'" disabled />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.resi.field_valuta') }}</label>
        <InputText :model-value="record?.valuta_codice || '—'" disabled />
      </div>
    </div>
  </div>
</template>
