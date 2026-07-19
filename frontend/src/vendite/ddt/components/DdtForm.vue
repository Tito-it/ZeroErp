<script setup>
// Scopo: Form testata DDT di vendita — emittente fiscale (legato allo user,
// mirror ordini), cliente (BA), utility, data, valuta + sezione TRASPORTO
// (causale, aspetto beni, modalita addebito, vettore, mittente,
// colli/pesi/volume, targa, autista, tracking). Usato dentro DdtDrawer.
// L'emittente è MEMORIZZATO sulla testata (addendum §15): in create e'
// prefillato dal profilo operatore (admin globale: Select) ed entra nel
// payload; il trigger DB resta fallback (da BA o ordine sorgente). A
// differenza di ordini: niente modalita/termine pagamento, niente
// fatturazione_trigger; in piu' i campi logistici del documento di trasporto.
// Clone adattato di OrdiniForm (§D-4).
//
// Granularita' disabilitazione: isModificabile (stato form, legato a
// can_edit_testata + readonly) OPPURE campo in nonEditableFields (per-campo BE).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { DATE_FORMAT } from '../../../core/constants'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import BillingAccountLookup from '../../../core/components/BillingAccountLookup.vue'
import SoggettoRuoloLookup from '../../../core/components/SoggettoRuoloLookup.vue'
import EmittenteFiscaleField from '../../../core/components/EmittenteFiscaleField.vue'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Divider from 'primevue/divider'

const { t } = useI18n()

const form = defineModel('form', { type: Object, required: true })

const props = defineProps({
  isModificabile: { type: Boolean, default: true },
  nonEditableFields: { type: Array, default: () => [] },
  isEdit: { type: Boolean, default: false },
  // Detail testata per il display denormalizzato dell'emittente in EDIT
  // (emittente_fiscale_descrizione/codice via EmittenteFiscaleField :record).
  // null in create: il campo mostra l'emittente del profilo operatore.
  record: { type: Object, default: null },
})

const lockedFields = computed(() => new Set(props.nonEditableFields))
function isLocked(field) {
  return !props.isModificabile || lockedFields.value.has(field)
}

// Il BA risolve cliente (destinatario_soggetto_ruolo lato BE) + utility. Mutiamo
// il form via defineModel (form.value.*): resta lo stesso oggetto reattivo,
// quindi il drawer reagisce al watch su billing_account_id (autosave bozza CREATE).
function onBaSelected(item) {
  if (!item) {
    form.value.billing_account_id = null
    form.value.billing_account_obj = null
    return
  }
  form.value.billing_account_id = item.id
  form.value.billing_account_obj = item
  // Coerenza utility/BA: se l'operatore non aveva selezionato utility, pre-compila
  // quella del BA. Se gia' valorizzata e diversa, lascia intervenire il lookup.
  if (!form.value.utility_id && item.utility_id) {
    form.value.utility_id = item.utility_id
  }
}

function onBaClear() {
  onBaSelected(null)
}

// Mittente / vettore: soggetti_ruolo (nullable). SoggettoRuoloLookup emette
// l'oggetto riga con `soggetto_ruolo_id`; teniamo l'_obj per il restore ricco.
function onMittenteSelected(item) {
  form.value.mittente_soggetto_ruolo_id = item?.soggetto_ruolo_id ?? null
  form.value.mittente_obj = item || null
}
function onMittenteClear() {
  form.value.mittente_soggetto_ruolo_id = null
  form.value.mittente_obj = null
}
function onVettoreSelected(item) {
  form.value.vettore_soggetto_ruolo_id = item?.soggetto_ruolo_id ?? null
  form.value.vettore_obj = item || null
}
function onVettoreClear() {
  form.value.vettore_soggetto_ruolo_id = null
  form.value.vettore_obj = null
}
</script>

<template>
  <div class="form-grid">
    <!-- ── Testata ── -->
    <div class="form-grid-2col">
      <!-- Emittente fiscale: operatore con EF assegnato → read-only auto;
           admin globale → Select sugli EF disponibili. In edit mostra ragione
           sociale + codice denormalizzati dal record. Mirror OrdiniForm
           (uniformazione 2026-07-13: emittente legato allo user). -->
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_emittente_fiscale') }} <span v-if="!isEdit">*</span></label>
        <EmittenteFiscaleField
          v-model="form.emittente_fiscale_id"
          :record="record"
          :is-edit="isEdit"
          :disabled="isLocked('emittente_fiscale_id')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_utility') }}</label>
        <UtilityPerRuoloSelect v-model="form.utility_id"
          :placeholder="t('vendite.ddt.field_utility')"
          :disabled="isLocked('utility_id')" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_billing_account') }} <span v-if="!isEdit">*</span></label>
        <BillingAccountLookup
          :model-value="form.billing_account_obj"
          :utility-id="form.utility_id"
          :disabled="isLocked('billing_account_id')"
          :placeholder="t('vendite.ddt.field_billing_account_placeholder')"
          @select="onBaSelected"
          @clear="onBaClear" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_data') }}</label>
        <DatePicker v-model="form.data" :date-format="DATE_FORMAT"
          show-icon show-button-bar :disabled="isLocked('data')" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_valuta') }}</label>
        <LookupSelect v-model="form.valuta_id" rel="config.valute"
          :placeholder="t('vendite.ddt.field_valuta')" :disabled="isLocked('valuta_id')"
          show-clear />
      </div>
    </div>

    <!-- ── Trasporto ── -->
    <Divider />
    <h4 style="margin: 0; font-size: 1rem;">{{ t('vendite.ddt.section_trasporto') }}</h4>

    <div class="form-grid-2col">
      <div class="form-field">
        <!-- Obbligatoria all'EMISSIONE, non al create (gate DB
             trgfn_ddt_guard_causale_emissione, DL-28): in bozza il NULL e'
             legittimo, l'asterisco col tooltip dichiara il vincolo prima
             che l'utente lo scopra dall'errore 544. Solo a campo editabile:
             su DDT gia' emesso/readonly il vincolo non e' piu' azionabile
             e l'asterisco mentirebbe. -->
        <label>
          {{ t('vendite.ddt.field_causale_trasporto') }}
          <span
            v-if="!isLocked('causale_trasporto_id')"
            v-tooltip.bottom="t('vendite.ddt.field_causale_richiesta_emissione')"
          >*</span>
        </label>
        <LookupSelect v-model="form.causale_trasporto_id" rel="config.causali_trasporto"
          :placeholder="t('vendite.ddt.field_causale_trasporto')"
          :disabled="isLocked('causale_trasporto_id')" show-clear />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_aspetto_bene') }}</label>
        <LookupSelect v-model="form.aspetto_bene_id" rel="config.aspetti_beni"
          :placeholder="t('vendite.ddt.field_aspetto_bene')"
          :disabled="isLocked('aspetto_bene_id')" show-clear />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_modalita_addebito') }}</label>
        <LookupSelect v-model="form.modalita_addebito_trasporto_id" rel="config.modalita_addebito_trasporto"
          :placeholder="t('vendite.ddt.field_modalita_addebito')"
          :disabled="isLocked('modalita_addebito_trasporto_id')" show-clear />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_vettore') }}</label>
        <SoggettoRuoloLookup
          :model-value="form.vettore_obj"
          :disabled="isLocked('vettore_soggetto_ruolo_id')"
          :placeholder="t('vendite.ddt.field_vettore_placeholder')"
          @select="onVettoreSelected"
          @clear="onVettoreClear" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_mittente') }}</label>
        <SoggettoRuoloLookup
          :model-value="form.mittente_obj"
          :disabled="isLocked('mittente_soggetto_ruolo_id')"
          :placeholder="t('vendite.ddt.field_mittente_placeholder')"
          @select="onMittenteSelected"
          @clear="onMittenteClear" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_tracking_code') }}</label>
        <InputText v-model="form.tracking_code" :disabled="isLocked('tracking_code')" />
      </div>
    </div>

    <div class="form-grid-3col">
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_num_colli') }}</label>
        <InputNumber v-model="form.num_colli" :min="0" :disabled="isLocked('num_colli')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_peso_lordo') }}</label>
        <InputNumber v-model="form.peso_lordo" :min="0"
          :min-fraction-digits="0" :max-fraction-digits="3" suffix=" kg"
          :disabled="isLocked('peso_lordo')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_peso_netto') }}</label>
        <InputNumber v-model="form.peso_netto" :min="0"
          :min-fraction-digits="0" :max-fraction-digits="3" suffix=" kg"
          :disabled="isLocked('peso_netto')" />
      </div>
    </div>

    <div class="form-grid-3col">
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_volume') }}</label>
        <InputNumber v-model="form.volume" :min="0"
          :min-fraction-digits="0" :max-fraction-digits="3" suffix=" m³"
          :disabled="isLocked('volume')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_targa') }}</label>
        <InputText v-model="form.targa" :disabled="isLocked('targa')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_autista') }}</label>
        <InputText v-model="form.autista" :disabled="isLocked('autista')" />
      </div>
    </div>
  </div>
</template>
