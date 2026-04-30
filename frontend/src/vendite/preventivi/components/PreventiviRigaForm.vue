<script setup>
// Scopo: Form singola riga preventivo — articolo (autocomplete), UoM, quantita', prezzo, sconto, IVA.
// Il prezzo viene proposto dal listino ma e' sempre sovrascrivibile dall'operatore.
import { ref, watch, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotify } from '../../../core/composables/useNotify'
import { extractApiError, extractApiErrorCode } from '../../../core/utils/apiError'
import { usePreventiviStore } from '../stores/preventivi'
import { useLimitiPricing } from '../../composables/useLimitiPricing'
import { useArticoloUomOptions } from '../../../core/composables/useArticoloUomOptions'
import ArticoloLookup from '../../../core/components/ArticoloLookup.vue'
import IvaSelect from '../../../core/components/IvaSelect.vue'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const store = usePreventiviStore()
const loading = ref(false)
const notify = useNotify()
const { limiti, load: loadLimiti, L2_ERROR_CODES } = useLimitiPricing()
onMounted(loadLimiti)

const props = defineProps({
  preventivoId: { type: Number, required: true },
  riga: { type: Object, default: null }
})
const emit = defineEmits(['saved', 'cancel'])

const isEdit = computed(() => props.riga != null)

const form = ref({
  articolo_id: null,
  descrizione: '',
  quantita: 1,
  prezzo_unitario: null,
  sconto_percentuale: 0,
  iva_id: null,
  uom_operativa_id: null,
  ordine: null,
})

// L2 autorizzazioni prezzi: cattura dettaglio errore per banner inline.
// Codici mappati centralizzati in useLimitiPricing per coerenza con il BE.
// L'azione "richiedi approvazione" resta disabled finche' L3 non e' rilasciato.
const l2Error = ref(null)

// L2 autorizzazioni prezzi: hint informativo sotto il campo prezzo.
// Valori cached modulo-level: una sola fetch per sessione.
const maxScontoPct = computed(() => Number(limiti.value.max_sconto_pct) || 0)
const maxMaggiorazionePct = computed(() => Number(limiti.value.max_maggiorazione_pct) || 0)
const limitiPricingText = computed(() => {
  const s = maxScontoPct.value
  const m = maxMaggiorazionePct.value
  if (s === 0 && m === 0) return t('preventivi.limiti_prezzo_zero')
  return t('preventivi.limiti_prezzo_hint', { sconto: s, maggiorazione: m })
})

// Reset banner L2 se l'utente modifica prezzo o articolo: segnale di retry
// con contesto potenzialmente diverso (articolo -> resolver diverso).
// Guard sul valore corrente per evitare set inutili.
watch(
  [() => form.value.prezzo_unitario, () => form.value.articolo_id],
  () => { if (l2Error.value) l2Error.value = null },
)

// Articolo selezionato (per restore autocomplete)
const articoloObj = ref(null)

// UoM operative dell'articolo (pattern VersioneDrawer/ContrattoRigheDrawer):
// le UoM ammesse per la riga sono solo quelle definite a livello articolo,
// non l'intero catalogo.unita_misura. Caricate al cambio articolo.
// Composable centralizzato (Fase 4.F1).
const {
  uomOptions, uomLoading, loadUomPerArticolo, pickBaseUomId, resetUomOptions,
} = useArticoloUomOptions()

function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('listini.uom_base_suffix')}` : ''
  return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
}

// Scopo: carica le UoM dell'articolo e, in create, pre-seleziona la base.
async function caricaUomConPickBase(articoloId) {
  const list = await loadUomPerArticolo(articoloId)
  if (!isEdit.value && !form.value.uom_operativa_id) {
    form.value.uom_operativa_id = pickBaseUomId(list)
  }
}

watch(() => props.riga, (riga) => {
  if (riga) {
    form.value = {
      articolo_id: riga.articolo_id,
      descrizione: riga.descrizione || '',
      quantita: Number(riga.quantita) || 1,
      prezzo_unitario: Number(riga.prezzo_unitario) || null,
      sconto_percentuale: Number(riga.sconto_percentuale) || 0,
      iva_id: riga.iva_id || null,
      uom_operativa_id: riga.uom_operativa_id || null,
      ordine: riga.ordine || null,
    }
    articoloObj.value = riga.articolo_id ? { id: riga.articolo_id, codice: riga.articolo_codice, descrizione: riga.articolo_descrizione } : null
  } else {
    form.value = { articolo_id: null, descrizione: '', quantita: 1, prezzo_unitario: null, sconto_percentuale: 0, iva_id: null, uom_operativa_id: null, ordine: null }
    articoloObj.value = null
    resetUomOptions()
  }
}, { immediate: true })

function onArticoloSelect(item) {
  form.value.articolo_id = item.id
  form.value.descrizione = item.descrizione || ''
  // Reset UoM: cambio articolo invalida l'eventuale UoM precedente.
  form.value.uom_operativa_id = null
  articoloObj.value = item
  // Create: autopick base; in edit articolo e' disabled e questo handler non scatta.
  caricaUomConPickBase(item.id)
}

const canSave = computed(() => form.value.articolo_id && form.value.quantita > 0)

// Scopo: costruisce il payload riga preventivo, opzionalmente con extras
//        (es. richiesta_approvazione=true per workflow L3 Sprint E).
//        Centralizza la build payload usata da handleSave + handleRichiediApprovazione.
function buildRigaPayload(extras = {}) {
  const f = form.value
  if (isEdit.value) {
    return {
      quantita: f.quantita,
      prezzo_unitario: f.prezzo_unitario,
      sconto_percentuale: f.sconto_percentuale,
      ...extras,
    }
  }
  return {
    articolo_id: f.articolo_id,
    descrizione: f.descrizione || null,
    quantita: f.quantita,
    prezzo_unitario: f.prezzo_unitario,
    sconto_percentuale: f.sconto_percentuale,
    iva_id: f.iva_id,
    uom_operativa_id: f.uom_operativa_id,
    ordine: f.ordine,
    ...extras,
  }
}

// Scopo: invia il payload riga al backend, gestendo edit vs create.
//        Le action dello store sono gia' unwrappate (ritornano res.data.data
//        direttamente, vedi memoria feedback_useapihandler_solo_axios), quindi
//        non serve nessun ulteriore unwrap qui.
function submitRiga(payload) {
  return isEdit.value
    ? store.aggiornaRiga(props.preventivoId, props.riga.id, payload)
    : store.addRiga(props.preventivoId, payload)
}

// Scopo: Salva riga intercettando specificamente i codici L2
//        (E_PREV_SCONTO_ECCESSIVO / E_PREV_MAGGIORAZIONE_ECCESSIVA) per
//        mostrare un banner inline invece del toast standard. Tutti gli
//        altri errori passano per il pattern standard useApiHandler.
async function handleSave() {
  l2Error.value = null
  const successMessage = isEdit.value ? t('preventivi.riga_salvata') : t('preventivi.riga_aggiunta')

  loading.value = true
  try {
    const result = await submitRiga(buildRigaPayload())
    notify.success(successMessage)
    emit('saved', result)
  } catch (err) {
    const code = extractApiErrorCode(err)
    if (L2_ERROR_CODES.includes(code)) {
      // Banner inline: niente toast, piu' spazio per il messaggio + azione.
      l2Error.value = {
        code,
        message: extractApiError(err, t('preventivi.errore_generico')),
        detail: err?.response?.data?.error?.detail || '',
      }
    } else {
      // Fallback pattern standard: toast unico col messaggio BE.
      notify.error(extractApiError(err, t('preventivi.errore_generico')))
    }
  } finally {
    loading.value = false
  }
}

// Scopo: ri-tenta il save aggiungendo flag richiesta_approvazione=true
//        (workflow L3 Sprint E). Il backend, in caso di violazione L2,
//        crea una pratica di approvazione e salva la riga in PENDING
//        invece di sollevare. Toast esplicito per dare feedback chiaro.
async function handleRichiediApprovazione() {
  l2Error.value = null
  loading.value = true
  try {
    const result = await submitRiga(buildRigaPayload({ richiesta_approvazione: true }))
    notify.success(t('preventivi.richiesta_approvazione_inviata'))
    emit('saved', result)
  } catch (err) {
    notify.error(extractApiError(err, t('preventivi.errore_generico')))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="form-grid">
    <div class="form-field">
      <label>{{ t('preventivi.riga_articolo') }}</label>
      <ArticoloLookup :model-value="articoloObj" :disabled="isEdit"
        :placeholder="t('preventivi.riga_cerca_articolo')" @select="onArticoloSelect" />
    </div>

    <div class="form-field">
      <label>{{ t('preventivi.riga_descrizione') }}</label>
      <InputText v-model="form.descrizione" />
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.riga_quantita') }}</label>
        <InputNumber v-model="form.quantita" :min-fraction-digits="2" :max-fraction-digits="6" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.riga_prezzo') }}</label>
        <InputNumber v-model="form.prezzo_unitario" mode="currency" currency="EUR" locale="it-IT" />
        <small class="text-color-secondary">{{ limitiPricingText }}</small>
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.riga_sconto') }}</label>
        <InputNumber v-model="form.sconto_percentuale" suffix="%" :min="0" :max="100"
          :min-fraction-digits="2" :max-fraction-digits="2" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.riga_iva') }}</label>
        <IvaSelect v-model="form.iva_id"
          :placeholder="t('preventivi.riga_iva')" :disabled="isEdit" />
      </div>
    </div>

    <div class="form-grid-2col" v-if="!isEdit">
      <div class="form-field">
        <label>{{ t('preventivi.riga_uom') }}</label>
        <Select v-model="form.uom_operativa_id"
          :options="uomOptions" :option-label="uomLabel" option-value="uom_id"
          :loading="uomLoading"
          :disabled="!form.articolo_id || uomLoading"
          :placeholder="form.articolo_id
            ? t('preventivi.riga_uom')
            : t('vendite.promo_articoli.field_uom_articolo_first')" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.riga_ordine') }}</label>
        <InputNumber v-model="form.ordine" :use-grouping="false" />
      </div>
    </div>

    <Message v-if="l2Error" severity="warn" :closable="false">
      <div style="display: flex; flex-direction: column; gap: 0.5rem;">
        <strong>{{ l2Error.message }}</strong>
        <small v-if="l2Error.detail">{{ l2Error.detail }}</small>
        <div>
          <Button
            :label="loading ? t('preventivi.richiedi_approvazione_in_corso') : t('preventivi.richiedi_approvazione')"
            icon="pi pi-send"
            size="small"
            severity="secondary"
            :loading="loading"
            v-tooltip.bottom="t('preventivi.richiedi_approvazione_tooltip')"
            @click="handleRichiediApprovazione"
          />
        </div>
      </div>
    </Message>

    <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem;">
      <Button :label="t('common.cancel')" severity="secondary" @click="emit('cancel')" />
      <Button :label="t('common.save')" :loading="loading" :disabled="!canSave" @click="handleSave" />
    </div>
  </div>
</template>
