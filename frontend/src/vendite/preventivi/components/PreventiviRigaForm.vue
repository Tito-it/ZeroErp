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
import { useAuthStore } from '../../../stores/auth'
import { suggerisciPrezzoRiga } from '../api/preventiviApi'
import { pricingOrigineSeverity } from '../../../core/utils/severity'
import { coerceJsonbToObject } from '../../../core/utils/meta'
import { PRICING_ACTIONS } from '../../constants'
import ArticoloLookup from '../../../core/components/ArticoloLookup.vue'
import IvaSelect from '../../../core/components/IvaSelect.vue'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'

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
const auth = useAuthStore()
const canOverride = computed(() => auth.isActionAllowed(PRICING_ACTIONS.OVERRIDE))
const maxScontoPct = computed(() => Number(limiti.value.max_sconto_pct) || 0)
const maxMaggiorazionePct = computed(() => Number(limiti.value.max_maggiorazione_pct) || 0)
const limitiPricingText = computed(() => {
  const s = maxScontoPct.value
  const m = maxMaggiorazionePct.value
  // Discriminazione del messaggio in 3 casi distinti:
  //  1) Operatore senza azione `prezzo_override_manuale` (Junior o ruolo
  //     limitato): non puo' modificare punto. Messaggio "Richiedi al
  //     responsabile l'autorizzazione".
  //  2) Operatore con azione ma limiti L2 a 0/0 (admin non ha ancora
  //     impostato VENDITE_MAX_SCONTO_PCT/MAGGIORAZIONE_PCT, oppure ha
  //     scelto policy zero per quell'utente): autorizzato in linea di
  //     principio ma 0% di variazione ammessa. Suggerisce di chiedere
  //     un limite concreto invece di "non sei autorizzato".
  //  3) Caso normale: mostra i limiti effettivi (sconto/maggiorazione).
  if (!canOverride.value) return t('preventivi.limiti_prezzo_non_autorizzato')
  if (s === 0 && m === 0) return t('preventivi.limiti_prezzo_zero_autorizzato')
  return t('preventivi.limiti_prezzo_hint', { sconto: s, maggiorazione: m })
})

// Prezzo "originale del listino" sempre visibile accanto al campo prezzo
// editabile. Sorgenti in ordine di priorita':
//  1) `_resolverPriceLive` — popolato da `suggerisciPrezzo()` ad ogni cambio
//     articolo/uom (sia in CREATE che in EDIT), ed e' la fonte piu' fresca.
//  2) `meta.prezzo_base_resolver` — denormalizzato dal BE quando viene
//     applicato un override (sopravvive a refresh). Utile in EDIT subito al
//     caricamento del form, prima che il resolver risponda.
// Cosi' l'operatore ha sempre il riferimento del listino vicino al prezzo
// che sta proponendo (utile in particolare dopo un rifiuto, ma anche in
// CREATE per giustificare a colpo d'occhio uno sconto/maggiorazione).
const _resolverPriceLive = ref(null)
const prezzoBaseResolverNum = computed(() => {
  if (_resolverPriceLive.value != null) return _resolverPriceLive.value
  // Coerce difensivo (vedi commento utility): meta puo' essere stringa.
  const meta = coerceJsonbToObject(props.riga?.meta)
  const raw = meta.prezzo_base_resolver
  if (raw == null) return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})
const formatCurrencyBaseListino = computed(() => {
  const n = prezzoBaseResolverNum.value
  if (n == null) return '—'
  return new Intl.NumberFormat('it-IT',
    { style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 6 }
  ).format(n)
})
// Mostra "Usa prezzo listino" solo se: c'e' un valore di riferimento, non
// coincide gia' col campo prezzo, e l'operatore puo' modificare il prezzo
// (override autorizzato — non ha senso il bottone se il campo e' bloccato).
const canRipristinaPrezzoListino = computed(() => {
  if (prezzoBaseResolverNum.value == null) return false
  const cur = Number(form.value.prezzo_unitario)
  if (Number.isFinite(cur)
      && Math.abs(cur - prezzoBaseResolverNum.value) < 1e-4) return false
  return canOverride.value
})
function ripristinaPrezzoListino() {
  form.value.prezzo_unitario = prezzoBaseResolverNum.value
}

// Ultimo prezzo scritto dal resolver: serve al watch sotto per distinguere
// "prezzo proposto dal resolver" (badge origine valido) da "override manuale
// dell'operatore" (badge da nascondere). null = nessun resolver attivo.
let _lastResolverPrice = null

// Reset banner L2 + badge origine se l'utente modifica prezzo o articolo:
// segnale di retry con contesto potenzialmente diverso (articolo -> resolver
// diverso) oppure di override manuale (prezzo cambiato).
// Confronto sul prezzo: se coincide con l'ultimo valore del resolver, e' la
// scrittura del resolver stesso (badge resta); altrimenti e' override manuale.
watch(
  [() => form.value.prezzo_unitario, () => form.value.articolo_id],
  ([newPrezzo]) => {
    if (l2Error.value) l2Error.value = null
    if (!prezzoOrigine.value) return
    if (_lastResolverPrice != null && Number(newPrezzo) === Number(_lastResolverPrice)) return
    prezzoOrigine.value = null
  },
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

// State usato da suggerisciPrezzo(): DEVE stare prima del watch `immediate`
// qui sotto, altrimenti il primo fire (sincrono in setup) entra in TDZ su
// `_resolverToken` / `prezzoOrigine` e la POST iniziale del bootstrap viene
// silenziosamente abortita (regressione gia' osservata: il prezzo listino
// non si popolava al primo click su una riga in edit, partiva solo dal
// secondo cambio di selezione quando il watch fa fire fuori da setup).
const prezzoOrigine = ref(null)
let _resolverToken = 0

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
    // Bootstrap riferimento "Prezzo listino" in EDIT: priorita' al meta
    // denormalizzato (sopravvive a refresh, no round-trip), poi chiamata al
    // resolver per essere sicuri di avere il valore attuale (best-effort:
    // se il resolver fallisce restiamo col meta).
    const metaParsed = coerceJsonbToObject(riga.meta)
    const metaRef = metaParsed.prezzo_base_resolver
    _resolverPriceLive.value = metaRef != null && Number.isFinite(Number(metaRef))
      ? Number(metaRef)
      : null
    if (riga.articolo_id && riga.uom_operativa_id) {
      suggerisciPrezzo()
    }
  } else {
    form.value = { articolo_id: null, descrizione: '', quantita: 1, prezzo_unitario: null, sconto_percentuale: 0, iva_id: null, uom_operativa_id: null, ordine: null }
    articoloObj.value = null
    _resolverPriceLive.value = null
    resetUomOptions()
  }
}, { immediate: true })

function onArticoloSelect(item) {
  form.value.articolo_id = item.id
  form.value.descrizione = item.descrizione || ''
  // Auto-fill IVA dall'articolo (catalogo.vw_articoli_dettaglio.iva_id, esposto
  // dal lookup). L'operatore puo' comunque sovrascriverla manualmente prima di
  // salvare. Nessun reset se il lookup non la espone (vecchi BE / articoli senza
  // iva configurata): mantiene il valore precedente.
  if (item.iva_id != null) {
    form.value.iva_id = item.iva_id
  }
  // Reset UoM: cambio articolo invalida l'eventuale UoM precedente.
  // Reset prezzo: il resolver verra' richiamato dopo il pickBaseUomId via watch.
  form.value.uom_operativa_id = null
  form.value.prezzo_unitario = null
  // Reset stato resolver: con un nuovo articolo qualsiasi prezzo precedente
  // dal vecchio resolver e' irrilevante. Senza questo reset, se il nuovo
  // prezzo manuale coincidesse casualmente col vecchio prezzo del resolver
  // (numerica), il watch del banner mostrerebbe l'origine sbagliata.
  _lastResolverPrice = null
  _resolverPriceLive.value = null
  prezzoOrigine.value = null
  articoloObj.value = item
  // Create: autopick base; in edit articolo e' disabled e questo handler non scatta.
  caricaUomConPickBase(item.id)
}

// Mappa locale origine -> i18n key del badge. Le label sono dominio-specifiche
// (preventivi.*), quindi restano qui. La severity (codice colore) e' invece
// centralizzata in core/utils/severity.js (`pricingOrigineSeverity`) e
// condivisa con TestResolverDialog + futuri consumer (ordini, fatture).
const ORIGINE_LABEL_KEY = {
  PROMO: 'preventivi.badge_origine_promo',
  CONTRATTO: 'preventivi.badge_origine_contratto',
  CONTRATTO_LISTINO: 'preventivi.badge_origine_contratto',
  CATEGORIA: 'preventivi.badge_origine_categoria',
}
const prezzoOrigineBadge = computed(() => {
  const code = prezzoOrigine.value
  if (!code) return null
  const key = ORIGINE_LABEL_KEY[code]
  if (!key) return null
  return { key, severity: pricingOrigineSeverity(code) }
})

// Suggerimento prezzo via pricing resolver v5. Trigger: articolo + uom presenti
// e prezzo non gia' valorizzato (rispetta override manuale dell'operatore).
// Token pattern interno (`_resolverToken`, dichiarato prima del watch sopra
// per evitare TDZ sull'immediate fire) per scartare risposte stantie su
// selezioni veloci.
async function suggerisciPrezzo() {
  if (!props.preventivoId) return
  if (!form.value.articolo_id || !form.value.uom_operativa_id) return
  // Auto-apply: in CREATE, e solo se il campo prezzo e' vuoto (rispetto
  // override manuale). In EDIT non scriviamo mai sul form: la riga ha
  // gia' un prezzo persistito, ma vogliamo COMUNQUE chiamare il resolver
  // per aggiornare il riferimento "Prezzo listino" mostrato accanto.
  const shouldApplyToForm = !isEdit.value && form.value.prezzo_unitario == null
  const tk = ++_resolverToken
  try {
    const res = await suggerisciPrezzoRiga(props.preventivoId, {
      articolo_id: form.value.articolo_id,
      uom_id: form.value.uom_operativa_id,
    })
    if (tk !== _resolverToken) return
    const data = res?.data?.data
    if (data && data.prezzo_finale != null) {
      const proposto = Number(data.prezzo_finale)
      // Aggiorno SEMPRE il riferimento "Prezzo listino" reattivo: cosi' la
      // cella accanto al prezzo si valorizza sia in CREATE (dopo pickBase
      // articolo) sia in EDIT (utile dopo rifiuto: l'operatore vede il
      // valore originale di confronto senza dover andare al listino).
      _resolverPriceLive.value = proposto
      _lastResolverPrice = proposto
      if (shouldApplyToForm) {
        form.value.prezzo_unitario = proposto
        prezzoOrigine.value = data.origine || null
      }
    }
  } catch (err) {
    // Resolver fallito: pre-fill non riuscito ma il save non e' bloccato.
    // Mostriamo un toast warn col messaggio BE quando disponibile (es. "Listino
    // non applicabile per articolo/utility/data") in modo che l'operatore capisca
    // perche' il prezzo non si e' compilato e non resti col campo vuoto senza
    // motivo. Codici tipici: E_PREZZO_LISTINO_NON_TROVATO,
    // E_CATEGORIA_LISTINO_NON_MAPPATA, E_PREZZO_LISTINO_RIGA_NON_TROVATA,
    // E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C, E_PREV_VALIDAZIONE.
    prezzoOrigine.value = null
    const msg = extractApiError(err, t('preventivi.prezzo_non_risolto'))
    notify.warn(msg)
  }
}

// Quando l'utente seleziona la UoM (dopo articolo) il resolver puo' partire.
// Usiamo un watch dedicato perche' la UoM viene impostata sia da onArticoloSelect
// (autopick base via caricaUomConPickBase) sia dalla Select manuale.
// In edit non ricalcoliamo: rispettiamo i valori persistiti.
// Al cambio UoM esplicito (oldUom != null) resettiamo il prezzo affinche' il
// resolver lo ricalcoli col nuovo contesto; in autopick iniziale (oldUom=null)
// non c'e' nulla da resettare.
watch(() => form.value.uom_operativa_id, (newUom, oldUom) => {
  if (isEdit.value) return
  if (!newUom) return
  if (oldUom && oldUom !== newUom) {
    form.value.prezzo_unitario = null
  }
  suggerisciPrezzo()
})

// Validazione FE: tutti i campi obbligatori devono essere valorizzati prima
// di abilitare il save. Backend richiede: articolo, UoM (per derivare
// qta_operativa via factor_to_base), quantita > 0, prezzo non null,
// IVA. Senza UoM scattava il guard DB E_QTA_MISSING; senza prezzo o IVA
// scattano altri trigger DB. Bloccando lato UX evitiamo round-trip inutili
// e diamo feedback immediato.
const canSave = computed(() => {
  const f = form.value
  if (!f.articolo_id) return false
  if (!f.uom_operativa_id) return false
  if (!(f.quantita > 0)) return false
  if (f.prezzo_unitario == null || f.prezzo_unitario === '') return false
  if (!f.iva_id) return false
  return true
})

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
      <label>{{ t('preventivi.riga_articolo') }} <span v-if="!isEdit">*</span></label>
      <ArticoloLookup :model-value="articoloObj" :disabled="isEdit"
        :placeholder="t('preventivi.riga_cerca_articolo')" @select="onArticoloSelect" />
    </div>

    <div class="form-field">
      <label>{{ t('preventivi.riga_descrizione') }}</label>
      <InputText v-model="form.descrizione" />
    </div>

    <div class="form-grid-3col">
      <div class="form-field">
        <label>{{ t('preventivi.riga_quantita') }} *</label>
        <InputNumber v-model="form.quantita" :min-fraction-digits="2" :max-fraction-digits="6" />
      </div>
      <div class="form-field">
        <label style="display: flex; align-items: center; gap: 0.5rem;">
          {{ t('preventivi.riga_prezzo') }} *
          <Tag v-if="prezzoOrigineBadge"
            :severity="prezzoOrigineBadge.severity"
            :value="t(prezzoOrigineBadge.key)"
            v-tooltip.top="t('preventivi.badge_origine_tooltip', { origine: prezzoOrigine })" />
        </label>
        <InputNumber v-model="form.prezzo_unitario" mode="currency" currency="EUR" locale="it-IT"
          :min-fraction-digits="6" :max-fraction-digits="6" />
        <small class="text-color-secondary">{{ limitiPricingText }}</small>
      </div>
      <!-- Prezzo listino: cella sempre visibile accanto al prezzo editabile.
           Sorgente: resolver vivo (cambio articolo/uom) o meta denormalizzato.
           Read-only — il bottone undo (visibile solo se il valore attuale
           differisce dal listino e l'operatore puo' fare override) ricopia
           il valore listino nel campo prezzo. Utile dopo un rifiuto: vede
           subito il valore originale per riallineare. -->
      <div class="form-field">
        <label style="display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;">
          <span>{{ t('preventivi.riga_prezzo_listino') }}</span>
          <Button
            v-if="canRipristinaPrezzoListino"
            v-tooltip.top="t('preventivi.azione_usa_prezzo_listino')"
            icon="pi pi-undo"
            text
            rounded
            size="small"
            severity="secondary"
            @click="ripristinaPrezzoListino"
          />
        </label>
        <InputText
          :model-value="formatCurrencyBaseListino"
          disabled
          class="app-readonly"
        />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.riga_sconto') }}</label>
        <InputNumber v-model="form.sconto_percentuale" suffix="%" :min="0" :max="100"
          :min-fraction-digits="2" :max-fraction-digits="2" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.riga_iva') }} *</label>
        <IvaSelect v-model="form.iva_id"
          :placeholder="t('preventivi.riga_iva')" :disabled="isEdit" />
      </div>
    </div>

    <div class="form-grid-2col" v-if="!isEdit">
      <div class="form-field">
        <label>{{ t('preventivi.riga_uom') }} *</label>
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
