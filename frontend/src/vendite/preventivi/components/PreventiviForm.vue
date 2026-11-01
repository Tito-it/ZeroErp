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
import { DATE_FORMAT, MANAGE_ICONS } from '../../../core/constants'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import BillingAccountLookup from '../../../core/components/BillingAccountLookup.vue'
import IstanzaUtilityLookup from '../../../core/components/IstanzaUtilityLookup.vue'
import EmittenteFiscaleField from '../../../core/components/EmittenteFiscaleField.vue'
import DatePicker from 'primevue/datepicker'

const { t } = useI18n()

// Form reattivo del padre via defineModel: il figlio muta `form.value.xxx`
// (oggetto condiviso per riferimento), senza violare no-mutating-props.
const form = defineModel('form', { type: Object, required: true })

const props = defineProps({
  isModificabile: { type: Boolean, default: true },
  nonEditableFields: { type: Array, default: () => [] },
  // Discrimina create vs edit per mostrare l'asterisco sui campi obbligatori
  // (pattern allineato a ContrattoDrawer: `<span v-if="!isEdit">*</span>`).
  isEdit: { type: Boolean, default: false },
  // Detail record dal backend (in EDIT). Necessario a `EmittenteFiscaleField`
  // per leggere `emittente_fiscale_codice`/`descrizione` denormalizzati senza
  // round-trip aggiuntivo. In CREATE il record e' null e il campo si comporta
  // in base al profilo (operatore→read-only auto, admin globale→Select).
  record: { type: Object, default: null },
  // Campi che il BACKEND indica come da correggere (envelope `error.fields`),
  // dall'handler del drawer: per esempio `validita_al` quando l'emissione si
  // rifiuta perche' la validita' e' gia' finita (E_PREV_EMISSIONE_VALIDITA_SCADUTA).
  campiErrati: { type: Array, default: () => [] },
})

// Lookup O(1) per campo non editabile.
const lockedFields = computed(() => new Set(props.nonEditableFields))
function isLocked(field) {
  return !props.isModificabile || lockedFields.value.has(field)
}

// Pattern coerente con ContrattoDrawer.onBaSelected: il BA risolve
// utility/istanza in modo univoco. Mutiamo il form via defineModel
// (form.value.*): resta lo stesso oggetto reattivo condiviso, quindi il
// PreventiviDrawer reagisce al watch su form.billing_account_id (chiama
// getPreventivoFormDefaults, vedi Fase 2.B4 + 2.F6).
function onBaSelected(item) {
  if (!item) {
    form.value.billing_account_id = null
    form.value.billing_account_obj = null
    form.value.istanza_utility_id = null
    form.value.istanza_utility_obj = null
    return
  }
  form.value.billing_account_id = item.id
  form.value.billing_account_obj = item
  form.value.istanza_utility_id = item.istanza_utility_id || null
  // Quando il BA porta con se' un'istanza, l'_obj per il picker istanza non
  // viene popolato qui (sapremmo solo l'id, non i campi ricchi). Il picker
  // istanza in questo caso e' disabled e mostra "auto-derivata da BA".
  form.value.istanza_utility_obj = null
  // Coerenza utility/BA: se l'operatore non aveva selezionato utility prima,
  // pre-compila quella del BA. Se era gia' valorizzata e diversa, lascia
  // intervenire BillingAccountLookup che gia' resetta il BA al cambio utility.
  if (!form.value.utility_id && item.utility_id) {
    form.value.utility_id = item.utility_id
  }
}

function onBaClear() {
  onBaSelected(null)
}

// Pattern simmetrico al BA: il picker delle forniture (una riga per BA) e'
// l'altra strada per scegliere il cliente, partendo dall'istanza. La selezione
// popola id + obj nel form; il BA della coppia istanza+utility lo risolve il
// backend (il preventivo ha sempre il BA, brief-db-istanza-nasce-col-ba R-2).
function onIstanzaSelected(item) {
  if (!item) {
    form.value.istanza_utility_id = null
    form.value.istanza_utility_obj = null
    return
  }
  form.value.istanza_utility_id = item.id
  form.value.istanza_utility_obj = item
  // Coerenza utility/istanza: se utility non ancora valorizzata, pre-compila
  // quella della fornitura scelta (la utility del suo BA). Il picker stesso
  // gia' resetta la selezione su cambio utility incoerente.
  if (!form.value.utility_id && item.utility_id) {
    form.value.utility_id = item.utility_id
  }
}

function onIstanzaClear() {
  onIstanzaSelected(null)
}
</script>

<template>
  <div class="form-grid">
    <div class="form-grid-2col">
      <!-- Emittente fiscale: sempre visibile. Operatore con EF assegnato →
           read-only auto-popolato dal profilo; admin globale (multi-EF) →
           Select sugli EF disponibili (necessario per consentire la scelta:
           senza UI il backend non puo' derivarlo da GUC e l'INSERT fallisce).
           In edit mostra codice + ragione sociale denormalizzati dal record. -->
      <div class="form-field">
        <label>{{ t('vendite.preventivi.field_emittente_fiscale') }} <span v-if="!isEdit">*</span></label>
        <EmittenteFiscaleField
          v-model="form.emittente_fiscale_id"
          :record="record"
          :is-edit="isEdit"
          :disabled="isLocked('emittente_fiscale_id')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.preventivi.field_utility') }} <span v-if="!isEdit">*</span></label>
        <UtilityPerRuoloSelect v-model="form.utility_id"
          :placeholder="t('vendite.preventivi.field_utility')"
          :disabled="isLocked('utility_id')" />
      </div>
    </div>

    <!-- Cliente/BA e istanza stanno sulla stessa riga: quando il BA deriva
         l'istanza, il messaggio resta affiancato al campo BA invece di scendere
         su una riga separata. -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.preventivi.field_billing_account') }}</label>
        <BillingAccountLookup
          :model-value="form.billing_account_obj"
          :utility-id="form.utility_id"
          :disabled="isLocked('billing_account_id')"
          :placeholder="t('vendite.preventivi.field_billing_account_placeholder')"
          @select="onBaSelected"
          @clear="onBaClear" />
      </div>

      <!-- Istanza utility: obbligatoria. Se BA selezionato l'istanza e'
           auto-derivata (picker nascosto). Senza BA il picker delle forniture
           e' l'altra strada: si sceglie l'istanza, e il BA della coppia lo
           risolve il backend al salvataggio. -->
      <div class="form-field">
        <label>{{ t('vendite.preventivi.field_istanza_utility') }} <span v-if="!isEdit">*</span></label>
        <IstanzaUtilityLookup
          v-if="!form.billing_account_id"
          :model-value="form.istanza_utility_obj"
          :utility-id="form.utility_id"
          :disabled="isLocked('istanza_utility_id')"
          :placeholder="t('vendite.preventivi.field_istanza_utility_placeholder')"
          @select="onIstanzaSelected"
          @clear="onIstanzaClear" />
        <div v-else class="app-field-hint">
          <i :class="MANAGE_ICONS.DERIVATO" style="margin-right: 0.4rem;"></i>
          {{ t('vendite.preventivi.istanza_da_billing_account') }}
        </div>
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.preventivi.field_validita_dal') }}</label>
        <DatePicker v-model="form.validita_dal" :date-format="DATE_FORMAT"
          show-icon show-button-bar :disabled="isLocked('validita_dal')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.preventivi.field_validita_al') }}</label>
        <DatePicker v-model="form.validita_al" :date-format="DATE_FORMAT"
          show-icon show-button-bar :disabled="isLocked('validita_al')"
          :invalid="campiErrati.includes('validita_al')" />
      </div>
    </div>

    <!-- Valuta + termine pagamento sulla stessa riga.
         fatturazione_immediata e competenza_mese NON sono in form testata:
         sono proprieta' di processo settate alla transizione EMESSO →
         ACCETTATO via dialog dedicato (regola "immediata ⇒ competenza=oggi"
         applicata BE). Vedi PreventiviDrawer dialog accettazione. -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.preventivi.field_valuta') }}</label>
        <LookupSelect v-model="form.valuta_id" rel="config.valute"
          :placeholder="t('vendite.preventivi.field_valuta')" :disabled="isLocked('valuta_id')"
          show-clear />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.preventivi.field_termini_pagamento') }}</label>
        <LookupSelect v-model="form.termine_pagamento_id" rel="config.termini_pagamento"
          :placeholder="t('vendite.preventivi.field_termini_pagamento')"
          :disabled="isLocked('termine_pagamento_id')" show-clear />
      </div>
    </div>
  </div>
</template>
