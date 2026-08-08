<script setup>
// Scopo: Form testata ordine di vendita — emittente, cliente (BA), utility,
// data, valuta, modalita'/termine pagamento, fatturazione_trigger. Usato dentro
// OrdiniDrawer. A differenza dei preventivi: niente istanza_utility (l'ordine si
// aggancia al cliente BA → soggetto_ruolo derivato dal BE), niente validita',
// niente listino. `tasso_cambio` non in UI (default 1, decisione Tid §6.2).
//
// Granularita' disabilitazione: isModificabile (stato form, legato a
// can_edit_testata + readonly) OPPURE campo in nonEditableFields (per-campo BE).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { DATE_FORMAT } from '../../../core/constants'
import { FATTURAZIONE_TRIGGER_CODES } from '../constants'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import BillingAccountLookup from '../../../core/components/BillingAccountLookup.vue'
import EmittenteFiscaleField from '../../../core/components/EmittenteFiscaleField.vue'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()

const form = defineModel('form', { type: Object, required: true })

const props = defineProps({
  // Campi che il BACKEND indica come da correggere (envelope `error.fields`).
  // Arrivano dal padre: questo componente non chiama le API da solo.
  campiErrati: { type: Array, default: () => [] },
  isModificabile: { type: Boolean, default: true },
  nonEditableFields: { type: Array, default: () => [] },
  isEdit: { type: Boolean, default: false },
  // Detail record dal backend (in EDIT): EmittenteFiscaleField legge i campi
  // denormalizzati emittente_fiscale_codice/descrizione senza round-trip.
  record: { type: Object, default: null },
})

const lockedFields = computed(() => new Set(props.nonEditableFields))
function isLocked(field) {
  return !props.isModificabile || lockedFields.value.has(field)
}

// Opzioni fatturazione_trigger: codici dal dominio, label i18n.
const fatturazioneTriggerOptions = computed(() =>
  FATTURAZIONE_TRIGGER_CODES.map((code) => ({
    value: code,
    label: t(`vendite.ordini.fatturazione_trigger_opt.${code}`),
  })),
)

// Il BA risolve cliente (soggetto_ruolo) + utility in modo univoco. Mutiamo il
// form via defineModel (form.value.*): resta lo stesso oggetto reattivo, quindi
// il drawer reagisce al watch su billing_account_id (autosave bozza CREATE).
function onBaSelected(item) {
  if (!item) {
    form.value.billing_account_id = null
    form.value.billing_account_obj = null
    return
  }
  form.value.billing_account_id = item.id
  form.value.billing_account_obj = item
  // Coerenza utility/BA: se l'operatore non aveva selezionato utility, pre-compila
  // quella del BA. Se gia' valorizzata e diversa, lascia intervenire il lookup
  // (BillingAccountLookup resetta il BA al cambio utility).
  if (!form.value.utility_id && item.utility_id) {
    form.value.utility_id = item.utility_id
  }
}

function onBaClear() {
  onBaSelected(null)
}
</script>

<template>
  <div class="form-grid">
    <div class="form-grid-2col">
      <!-- Emittente fiscale: operatore con EF assegnato → read-only auto;
           admin globale → Select sugli EF disponibili. In edit mostra codice +
           ragione sociale denormalizzati dal record. -->
      <div class="form-field">
        <label>{{ t('vendite.ordini.field_emittente_fiscale') }} <span v-if="!isEdit">*</span></label>
        <EmittenteFiscaleField
          v-model="form.emittente_fiscale_id"
          :record="record"
          :is-edit="isEdit"
          :disabled="isLocked('emittente_fiscale_id')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ordini.field_utility') }}</label>
        <UtilityPerRuoloSelect v-model="form.utility_id"
          :placeholder="t('vendite.ordini.field_utility')"
          :disabled="isLocked('utility_id')" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ordini.field_billing_account') }} <span v-if="!isEdit">*</span></label>
        <BillingAccountLookup
          :model-value="form.billing_account_obj"
          :utility-id="form.utility_id"
          :disabled="isLocked('billing_account_id')"
          :placeholder="t('vendite.ordini.field_billing_account_placeholder')"
          @select="onBaSelected"
          @clear="onBaClear" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ordini.field_data') }}</label>
        <DatePicker v-model="form.data"
        :invalid="campiErrati.includes('data')" :date-format="DATE_FORMAT"
          show-icon show-button-bar :disabled="isLocked('data')" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ordini.field_valuta') }}</label>
        <LookupSelect v-model="form.valuta_id" rel="config.valute"
          :placeholder="t('vendite.ordini.field_valuta')" :disabled="isLocked('valuta_id')"
          show-clear />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ordini.field_fatturazione_trigger') }}</label>
        <Select v-model="form.fatturazione_trigger"
          :options="fatturazioneTriggerOptions" option-label="label" option-value="value"
          :placeholder="t('vendite.ordini.field_fatturazione_trigger')"
          :disabled="isLocked('fatturazione_trigger')" show-clear
          v-tooltip.bottom="t('vendite.ordini.fatturazione_trigger_hint')" />
      </div>
    </div>

    <div class="form-grid-2col">
      <!-- Corsia di fatturazione: «questo ordine va fatturato subito».
           E' un INSTRADAMENTO, non un'azione: si decide prima che il lavoro
           entri in commessa (dopo il push il flag e' inerte e il DB respinge la
           modifica). Per fatturare adesso qualcosa gia' in commessa si usa
           l'emissione mirata dal cruscotto Competenza. -->
      <div class="form-field">
        <label for="ord-fatt-immediata">{{ t('vendite.ordini.field_fatturazione_immediata') }}</label>
        <div class="app-form-inline-toggle">
          <ToggleSwitch
            input-id="ord-fatt-immediata"
            v-model="form.fatturazione_immediata"
            :invalid="campiErrati.includes('fatturazione_immediata')"
            :disabled="isLocked('fatturazione_immediata')" />
          <small class="text-color-secondary">
            {{ t('vendite.ordini.fatturazione_immediata_hint') }}
          </small>
        </div>
      </div>
      <div class="form-field"></div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ordini.field_modalita_pagamento') }}</label>
        <LookupSelect v-model="form.modalita_pagamento_id" rel="config.modalita_pagamento"
          :placeholder="t('vendite.ordini.field_modalita_pagamento')"
          :disabled="isLocked('modalita_pagamento_id')" show-clear />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ordini.field_termini_pagamento') }}</label>
        <LookupSelect v-model="form.termine_pagamento_id" rel="config.termini_pagamento"
          :placeholder="t('vendite.ordini.field_termini_pagamento')"
          :disabled="isLocked('termine_pagamento_id')" show-clear />
      </div>
    </div>
  </div>
</template>
