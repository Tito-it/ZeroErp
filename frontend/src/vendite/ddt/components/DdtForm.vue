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
//
// Cliente (brief-db-esecutivi-ba-coppia, D-2/D-4, 2026-10-10): il BA e'
// FACOLTATIVO e si sceglie in bozza. Col BA, destinatario e utility sono copie
// del BA e le scrive il DB: qui si mostrano, non si scelgono. Senza BA
// (trasferimento, conto lavoro, riparazione) il destinatario lo sceglie
// l'operatore. Se la causale vuole un cliente lo dice l'emissione, con la
// capability (reason CLIENTE_MANCANTE): nessuna regola ricopiata qui.
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
  // Detail testata per il display denormalizzato dell'emittente in EDIT
  // (emittente_ragione_sociale/codice via EmittenteFiscaleField :record).
  // null in create: il campo mostra l'emittente del profilo operatore.
  record: { type: Object, default: null },
})

const lockedFields = computed(() => new Set(props.nonEditableFields))
function isLocked(field) {
  return !props.isModificabile || lockedFields.value.has(field)
}

// Col BA, destinatario e utility vengono dal BA (li scrive il DB): i due campi
// si spengono e mostrano cio' che il BA dice.
const conCliente = computed(() => form.value.billing_account_id != null)

// Mutiamo il form via defineModel (form.value.*): resta lo stesso oggetto
// reattivo, quindi il drawer reagisce al watch su billing_account_id /
// destinatario (autosave bozza CREATE).
function onBaSelected(item) {
  if (!item) {
    form.value.billing_account_id = null
    form.value.billing_account_obj = null
    // ⚠️ Il destinatario RESTA (id e nome insieme): e' quello del BA tolto,
    // come fa il DB su un BA tolto (`trgfn_ddt_normalize`), e senza BA si
    // manda nel payload — l'operatore lo cambia se serve.
    return
  }
  form.value.billing_account_id = item.id
  form.value.billing_account_obj = item
  // La utility e' quella del BA (copia, la scrive il DB): il campo la mostra.
  if (item.utility_id != null) form.value.utility_id = item.utility_id
  // ⛔ Id e nome del destinatario si scrivono INSIEME, dal ruolo del BA: un
  //    nome nuovo accanto all'id del BA precedente farebbe mostrare un
  //    destinatario e mandarne un altro, se poi il BA si toglie.
  form.value.destinatario_soggetto_ruolo_id = item.soggetto_ruolo_id ?? null
  form.value.destinatario_obj = item.soggetto_ruolo_id != null
    ? { soggetto_ruolo_id: item.soggetto_ruolo_id, ragione_sociale_completa: item.ragione_sociale_completa }
    : null
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
// Destinatario senza cliente: il terzista o il deposito.
function onDestinatarioSelected(item) {
  form.value.destinatario_soggetto_ruolo_id = item?.soggetto_ruolo_id ?? null
  form.value.destinatario_obj = item || null
}
function onDestinatarioClear() {
  form.value.destinatario_soggetto_ruolo_id = null
  form.value.destinatario_obj = null
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
      <!-- Utility: col BA e' la sua (copia scritta dal DB) e si spegne; senza
           BA filtra solo la ricerca del cliente, e non si salva. -->
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_utility') }}</label>
        <UtilityPerRuoloSelect v-model="form.utility_id"
          v-tooltip.bottom="t('vendite.ddt.utility_dal_cliente_hint')"
          :placeholder="t('vendite.ddt.field_utility')"
          :disabled="isLocked('billing_account_id') || conCliente" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_billing_account') }}</label>
        <BillingAccountLookup
          :model-value="form.billing_account_obj"
          :utility-id="form.utility_id"
          :invalid="campiErrati.includes('billing_account_id')"
          :disabled="isLocked('billing_account_id')"
          :placeholder="t('vendite.ddt.field_billing_account_placeholder')"
          @select="onBaSelected"
          @clear="onBaClear" />
      </div>
      <div class="form-field">
        <label>
          {{ t('vendite.ddt.field_destinatario') }}
          <span v-if="!conCliente && !isLocked('destinatario_soggetto_ruolo_id')">*</span>
        </label>
        <SoggettoRuoloLookup
          :model-value="form.destinatario_obj"
          :invalid="campiErrati.includes('destinatario_soggetto_ruolo_id')"
          :disabled="isLocked('destinatario_soggetto_ruolo_id') || conCliente"
          :placeholder="t('vendite.ddt.field_destinatario_placeholder')"
          @select="onDestinatarioSelected"
          @clear="onDestinatarioClear" />
        <small class="app-text-muted">{{ t('vendite.ddt.destinatario_dal_cliente_hint') }}</small>
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ddt.field_data') }}</label>
        <DatePicker v-model="form.data"
        :invalid="campiErrati.includes('data')" :date-format="DATE_FORMAT"
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
      <!-- Corsia di fatturazione: instradamento deciso PRIMA che il lavoro
           entri in commessa (dopo il push il flag e' inerte e il DB respinge
           la modifica). Per fatturare adesso qualcosa gia' in commessa si usa
           l'emissione mirata dal cruscotto Competenza. -->
      <div class="form-field">
        <label for="ddt-fatt-immediata">{{ t('vendite.ddt.field_fatturazione_immediata') }}</label>
        <div class="app-form-inline-toggle">
          <ToggleSwitch
            input-id="ddt-fatt-immediata"
            v-model="form.fatturazione_immediata"
            :invalid="campiErrati.includes('fatturazione_immediata')"
            :disabled="isLocked('fatturazione_immediata')" />
          <small class="app-text-muted">
            {{ t('vendite.ddt.fatturazione_immediata_hint') }}
          </small>
        </div>
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
