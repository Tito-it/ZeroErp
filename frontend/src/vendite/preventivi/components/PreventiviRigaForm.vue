<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Form singola riga preventivo — articolo (autocomplete), UoM, quantita', prezzo, sconto, IVA.
// Il prezzo viene proposto dal listino ma e' sempre sovrascrivibile dall'operatore.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotify } from '../../../core/composables/useNotify'
import { extractApiError } from '../../../core/utils/apiError'
import { usePreventiviStore } from '../stores/preventivi'
import { useLimitiPricing } from '../../composables/useLimitiPricing'
import { useRigaArticoloComposito } from '../../_shared/righe/useRigaArticoloComposito'
import { useAuthStore } from '../../../stores/auth'
import { suggerisciPrezzoRiga, previewRigaComponenti } from '../api/preventiviApi'
import { pricingOrigineSeverity, pricingOrigineLabelKey } from '../../../core/utils/severity'
import { coerceJsonbToObject } from '../../../core/utils/meta'
import { formatCurrency } from '../../../core/utils/format'
import { PRICING_ACTIONS } from '../../constants'
import ArticoloLookup from '../../../catalogo/components/ArticoloLookup.vue'
import IvaSelect from '../../../core/components/IvaSelect.vue'
import PreventiviRigaComponentiPanel from './PreventiviRigaComponentiPanel.vue'
import ComponentiCreateActionsPanel from '../../_shared/componenti/ComponentiCreateActionsPanel.vue'
import ComponentiDialog from '../../_shared/componenti/ComponentiDialog.vue'
import L2ErrorBanner from '../../_shared/pricing/L2ErrorBanner.vue'
import { useL2SaveFlow } from '../../_shared/pricing/useL2SaveFlow'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useIvaRisolta } from '../../_shared/righe/useIvaRisolta'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { DATE_FORMAT, MANAGE_ICONS } from '../../../core/constants'
import { parseIsoDate, toDateString } from '../../../core/utils/date'

const { t } = useI18n()
const store = usePreventiviStore()
const loading = ref(false)
const notify = useNotify()
const { limiti, load: loadLimiti, L2_ERROR_CODES } = useLimitiPricing()

const props = defineProps({
  preventivoId: { type: Number, required: true },
  // Refactor cascata 2026-05-15: BA del preventivo per popolare il livello
  // categoria_cliente della cascata soglie. Senza, soglia "generica" utente.
  billingAccountId: { type: Number, default: null },
  riga: { type: Object, default: null },
  // La data del documento (ISO, dal dettaglio): il minimo del calendario
  // delle date di consegna. Solo un aiuto: il rifiuto vero e' del DB
  // (`E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE`).
  dataDocumento: { type: String, default: null },
})

// Carica i limiti per il BA corrente. Watch + immediate: lo scatto immediato
// vale anche da `onMounted` (Vue setup esegue immediate prima del mount),
// quindi NON serve un onMounted aggiuntivo — eviterebbe solo doppio fetch
// al primo mount (cache modulo-level dedupa per BA in useLimitiPricing).
// Su errore (BA che non risulta → 404, F-6) i limiti restano a 0 e l'operatore
// lo sa: senza avviso l'hint mostrerebbe la soglia generica come del cliente.
watch(() => props.billingAccountId, (baId) => {
  loadLimiti(baId).catch((err) => {
    notify.warn(extractApiError(err, t('vendite.preventivi.limiti_non_caricati')))
  })
}, { immediate: true })
const {
  ivaOrigine,
  origineLabel: ivaOrigineLabel,
  risolviPer: risolviIvaPer,
  reset: resetIva,
} = useIvaRisolta({ documentoTipo: SORGENTE_CODES.PREVENTIVO, documentoId: () => props.preventivoId })

const emit = defineEmits(['saved', 'cancel', 'componenti-changed'])

const minDataConsegna = computed(() => parseIsoDate(props.dataDocumento))

const form = ref({
  articolo_id: null,
  descrizione: '',
  qta_operativa: 1,
  prezzo_unitario: null,
  sconto_percentuale: 0,
  iva_id: null,
  uom_operativa_id: null,
  ordine: null,
  // La data di consegna RICHIESTA dal cliente (Blocco A del brief modifiche
  // certe): sul preventivo c'e' solo la richiesta — la conferma nasce
  // sull'ordine, e `fn_push_preventivo_a_ordine` porta avanti questa.
  data_consegna_richiesta_cliente: null,
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
  //     Variante "_con_cliente" usata quando il preventivo ha un BA: il
  //     limite e' gia' adattato alla categoria cliente (cascata 2026-05-15)
  //     e il testo lo dichiara esplicitamente per trasparenza UX. Senza BA
  //     (cascata "generica utente") usa il copy base senza riferimento.
  if (!canOverride.value) return t('vendite.preventivi.limiti_prezzo_non_autorizzato')
  if (s === 0 && m === 0) return t('vendite.preventivi.limiti_prezzo_zero_autorizzato')
  const key = props.billingAccountId
    ? 'vendite.preventivi.limiti_prezzo_hint_con_cliente'
    : 'vendite.preventivi.limiti_prezzo_hint'
  return t(key, { sconto: s, maggiorazione: m })
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
const formatCurrencyBaseListino = computed(() =>
  formatCurrency(prezzoBaseResolverNum.value, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
    placeholder: '—',
  }),
)
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

// Cuore riga articolo/composito condiviso con OrdiniRigaForm (B11, regola del
// 2): isEdit/isCasoA/isPadreComposito + wiring UoM + ComponentiDialog +
// submitRiga. Lo strato resolver listino + gate L2 + cella prezzo-listino +
// campo `ordine` qui sotto sono il superset specifico del preventivo.
const {
  isEdit, isCasoA, isPadreComposito,
  uomOptions, uomLoading, uomLabel, caricaUomConPickBase, resetUomOptions,
  componentiDialogVisible, componentiPayload, showComponentiDialog,
  apriComponentiDialog, onComponentiConfirm,
  submitRiga,
  modificato, chiudiConConferma, seguiRiga,
} = useRigaArticoloComposito({
  store,
  parentId: () => props.preventivoId,
  riga: () => props.riga,
  articoloObj,
  form,
})

// State usato da suggerisciPrezzo(): DEVE stare prima del watch `immediate`
// qui sotto, altrimenti il primo fire (sincrono in setup) entra in TDZ su
// `_resolverToken` / `prezzoOrigine` e la POST iniziale del bootstrap viene
// silenziosamente abortita (regressione gia' osservata: il prezzo listino
// non si popolava al primo click su una riga in edit, partiva solo dal
// secondo cambio di selezione quando il watch fa fire fuori da setup).
const prezzoOrigine = ref(null)
let _resolverToken = 0

// Il legame con la riga (fotografia, riga riletta dal server) e' del cuore
// condiviso: qui solo come si popola il form.
seguiRiga((riga) => {
  if (riga) {
    form.value = {
      articolo_id: riga.articolo_id,
      descrizione: riga.descrizione || '',
      qta_operativa: Number(riga.qta_operativa) || 1,
      prezzo_unitario: Number(riga.prezzo_unitario) || null,
      sconto_percentuale: Number(riga.sconto_percentuale) || 0,
      iva_id: riga.iva_id || null,
      uom_operativa_id: riga.uom_operativa_id || null,
      ordine: riga.ordine || null,
      data_consegna_richiesta_cliente: parseIsoDate(riga.data_consegna_richiesta_cliente),
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
    form.value = { articolo_id: null, descrizione: '', qta_operativa: 1, prezzo_unitario: null, sconto_percentuale: 0, iva_id: null, uom_operativa_id: null, ordine: null, data_consegna_richiesta_cliente: null }
    articoloObj.value = null
    _resolverPriceLive.value = null
    resetUomOptions()
  }
})

function onArticoloSelect(item) {
  form.value.articolo_id = item.id
  form.value.descrizione = item.descrizione || ''
  // ⛔ NIENTE PIU' AUTO-FILL DALL'ARTICOLO. Copiare `articolo.iva_id` era una
  // SECONDA risposta alla stessa domanda, e sbagliata in due casi che non danno
  // nessun sintomo: ignora l'uso della fornitura (`config.tipi_utenze`, dove
  // l'articolo tace) e ignora i titoli documentati del cliente — su un
  // esportatore abituale proponeva l'aliquota piena.
  // ⭐ Ora risponde la sede unica (`vendite.fn_resolve_iva_riga`), e il
  // contesto lo deriva il backend dalla testata del documento: e' la stessa che
  // leggera' al salvataggio, quindi cio' che si vede e cio' che viene scritto
  // non possono divergere.
  // ⚠️ Best-effort: se l'anteprima non risponde il campo resta vuoto e
  // l'operatore lo compila — che fino a `I6` e' ancora un suo diritto.
  resetIva()
  risolviIvaPer(form.value, item.id)
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

// Badge origine prezzo: label centralizzate in severity.js
// (`pricingOrigineLabelKey`) per evitare drift con PreventiviRigaComponentiPanel
// post refactor componenti 2026-05-11 (5 valori inclusi CONTRATTO_OVERRIDE +
// MANUALE). La severity (colore) viene dalla stessa fonte.
const prezzoOrigineBadge = computed(() => {
  const code = prezzoOrigine.value
  if (!code) return null
  const key = pricingOrigineLabelKey(code)
  if (!key) return null
  return { key, severity: pricingOrigineSeverity(code) }
})

// Suggerimento prezzo via pricing resolver v5. Trigger: articolo + uom presenti
// e prezzo non gia' valorizzato (rispetta override manuale dell'operatore).
// Token pattern interno (`_resolverToken`, dichiarato prima del watch sopra
// per evitare TDZ sull'immediate fire) per scartare risposte stantie su
// selezioni veloci.
// Skip per righe CASO A (il padre non ha singolo prezzo listino: e' SUM
// componenti). Il resolver per il singolo articolo composito o solleva o
// ritorna un prezzo non rappresentativo — meglio non chiamarlo.
async function suggerisciPrezzo() {
  if (!props.preventivoId) return
  if (!form.value.articolo_id || !form.value.uom_operativa_id) return
  // Skip per articoli compositi (CASO A in EDIT, lookup is_composito in
  // CREATE): il prezzo padre e' SUM componenti via trigger DB, il resolver
  // del singolo articolo non va chiamato — per admin globali solleverebbe
  // E_PREV_VALIDAZIONE su emittente mancante.
  if (isPadreComposito.value) return
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
    const msg = extractApiError(err, t('vendite.preventivi.prezzo_non_risolto'))
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
// di abilitare il save. Backend richiede: articolo, UoM operativa,
// `qta_operativa` diversa da zero (CHECK DB `<> 0`: negativi ammessi; il
// trigger deriva `quantita` base), prezzo non null, IVA. Senza qta scatta il
// guard DB E_QTA_MISSING; senza prezzo o IVA scattano altri trigger DB.
// Bloccando lato UX evitiamo round-trip inutili e diamo feedback immediato.
const canSave = computed(() => {
  const f = form.value
  if (!f.articolo_id) return false
  if (!f.uom_operativa_id) return false
  if (f.qta_operativa == null || Number(f.qta_operativa) === 0) return false
  // Per articoli compositi (CREATE composito o EDIT CASO A) il prezzo
  // padre e' SUM(componenti × coeff_qta) ricalcolato dai trigger DB:
  // non lo richiediamo nel payload e non lo validiamo qui.
  if (!isPadreComposito.value && (f.prezzo_unitario == null || f.prezzo_unitario === '')) return false
  // ⛔ `I6`: l'IVA NON e' piu' un requisito per salvare, e toglierlo e'
  //    obbligatorio — non un ripulisti. Con la casella spenta e
  //    l'auto-fill morto, se l'anteprima non risponde il campo resta
  //    vuoto e la riga non si potrebbe piu' salvare: la creazione si
  //    bloccherebbe DA SOLA, senza che nulla lo spieghi.
  //    A rispondere e' comunque il backend al salvataggio; a fermare
  //    una riga senza aliquota e' il gate all'emissione (`I9`).
  // Modello unificato 2026-05-13: in CREATE su articolo composito,
  // blocca il save finche' la ComponentiDialog non e' stata confermata
  // almeno una volta (componentiPayload != null). Se l'operatore
  // annulla, resta bloccato — deve riaprire e confermare.
  if (showComponentiDialog.value && componentiPayload.value == null) return false
  return true
})

// Scopo: costruisce il payload riga preventivo, opzionalmente con extras
//        (es. richiesta_approvazione=true per workflow L3 Sprint E).
//        Centralizza la build payload usata da handleSave + handleRichiediApprovazione.
function buildRigaPayload(extras = {}) {
  const f = form.value
  // ISO o `null` (DatePicker vuoto): il `null` esplicito AZZERA in PATCH,
  // quindi svuotare il DatePicker toglie la data.
  const dataConsegna = toDateString(f.data_consegna_richiesta_cliente)
  if (isEdit.value) {
    const base = {
      qta_operativa: f.qta_operativa,
      sconto_percentuale: f.sconto_percentuale,
      data_consegna_richiesta_cliente: dataConsegna,
    }
    // Refactor componenti 2026-05-11: per riga CASO A il prezzo padre e'
    // calcolato dai trigger DB come SUM(componenti × coeff_qta). Inviarlo
    // qui scatenerebbe inutilmente il workflow L1/L2 override su un valore
    // che verra' comunque sovrascritto dal trigger. La modifica del prezzo
    // delle CASO A avviene per componente via PreventiviRigaComponentiPanel.
    if (!isCasoA.value) {
      base.prezzo_unitario = f.prezzo_unitario
    }
    return { ...base, ...extras }
  }
  // CREATE: include componenti_overrides quando l'articolo e' composito
  // e l'operatore ha modificato almeno un prezzo (modello unificato
  // 2026-05-13). Il payload Dialog (`componentiPayload`) e' un delta:
  // include solo i prezzi diversi dal suggerito. La composizione BoM e'
  // contratto immutabile (tutti i figli sempre inclusi, default DB
  // attivo=TRUE per tutti) — niente piu' `componenti_attivazioni`.
  const payload = {
    articolo_id: f.articolo_id,
    descrizione: f.descrizione || null,
    qta_operativa: f.qta_operativa,
    sconto_percentuale: f.sconto_percentuale,
    uom_operativa_id: f.uom_operativa_id,
    ordine: f.ordine,
    data_consegna_richiesta_cliente: dataConsegna,
    ...extras,
  }
  // Articolo composito CREATE: il prezzo padre e' SUM(componenti) via
  // trigger DB — non inviarlo (verrebbe sovrascritto). Stesso pattern
  // di EDIT CASO A. Per articoli semplici lo inviamo regolarmente.
  if (!isPadreComposito.value) {
    payload.prezzo_unitario = f.prezzo_unitario
  }
  if (showComponentiDialog.value && componentiPayload.value?.overrides) {
    payload.componenti_overrides = componentiPayload.value.overrides
  }
  return payload
}

// Save + richiedi-approvazione con gate L2 via BB condiviso (B12, regola del 2).
// Banner inline su violazione L2; side-effect di successo (emit 'saved') iniettato.
const { save: handleSave, richiediApprovazione: handleRichiediApprovazione } = useL2SaveFlow({
  persist: submitRiga,
  buildPayload: buildRigaPayload,
  onSuccess: (result) => emit('saved', result),
  messages: {
    success: () => (isEdit.value ? t('vendite.preventivi.riga_salvata') : t('vendite.preventivi.riga_aggiunta')),
    approvalRequested: t('vendite.preventivi.richiesta_approvazione_inviata'),
    error: t('vendite.preventivi.errore_generico'),
  },
  l2Error,
  loading,
  l2ErrorCodes: L2_ERROR_CODES,
})

// ⭐ D-13 (2026-10-03): la fotografia della riga la tiene il cuore comune
//    (`useRigaArticoloComposito`). Il contenitore la legge da qui per chiedere
//    prima di cambiare riga o di uscire dal drawer.
defineExpose({ modificato, chiudiConConferma })
</script>

<template>
  <div class="form-grid">
    <div class="form-field">
      <label>{{ t('vendite.preventivi.riga_articolo') }} <span v-if="!isEdit">*</span></label>
      <ArticoloLookup :model-value="articoloObj" :disabled="isEdit"
        documento="PREVENTIVO" :documento-id="preventivoId"
        :placeholder="t('vendite.preventivi.riga_cerca_articolo')" @select="onArticoloSelect" />
    </div>

    <div class="form-field">
      <label>{{ t('vendite.preventivi.riga_descrizione') }}</label>
      <InputText v-model="form.descrizione" />
    </div>

    <div class="form-grid-3col">
      <div class="form-field">
        <label>{{ t('vendite.preventivi.riga_quantita') }} *</label>
        <InputNumber v-model="form.qta_operativa" :min-fraction-digits="2" :max-fraction-digits="6" />
      </div>
      <div class="form-field">
        <label style="display: flex; align-items: center; gap: 0.5rem;">
          {{ t('vendite.preventivi.riga_prezzo') }} *
          <Tag v-if="prezzoOrigineBadge"
            :severity="prezzoOrigineBadge.severity"
            :value="t(prezzoOrigineBadge.key)"
            v-tooltip.top="t('vendite.preventivi.badge_origine_tooltip', { origine: prezzoOrigine })" />
          <Tag v-if="isPadreComposito"
            severity="secondary"
            :value="t('vendite.preventivi.componenti_padre_calcolato')"
            v-tooltip.top="t('vendite.preventivi.componenti_section_hint')" />
        </label>
        <InputNumber v-model="form.prezzo_unitario" mode="currency" currency="EUR" locale="it-IT"
          :min-fraction-digits="6" :max-fraction-digits="6"
          :disabled="isPadreComposito" />
        <small class="app-text-muted">{{ limitiPricingText }}</small>
      </div>
      <!-- Prezzo listino: cella visibile accanto al prezzo editabile.
           Sorgente: resolver vivo (cambio articolo/uom) o meta denormalizzato.
           Read-only — il bottone undo (visibile solo se il valore attuale
           differisce dal listino e l'operatore puo' fare override) ricopia
           il valore listino nel campo prezzo. Utile dopo un rifiuto: vede
           subito il valore originale per riallineare.
           Nascosta per righe CASO A: il padre non ha un singolo prezzo
           listino (e' SUM componenti); il riferimento listino e' sui singoli
           componenti, mostrato nel pannello sotto. -->
      <div v-if="!isPadreComposito" class="form-field">
        <label style="display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;">
          <span>{{ t('vendite.preventivi.riga_prezzo_listino') }}</span>
          <Button
            v-if="canRipristinaPrezzoListino"
            v-tooltip.top="t('vendite.preventivi.azione_usa_prezzo_listino')"
            :icon="MANAGE_ICONS.RIPRISTINA_LISTINO"
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
        <label>{{ t('vendite.preventivi.riga_sconto') }}</label>
        <InputNumber v-model="form.sconto_percentuale" suffix="%" :min="0" :max="100"
          :min-fraction-digits="2" :max-fraction-digits="2" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.preventivi.riga_iva') }} *</label>
        <!-- ⛔ `I6`: LA CASELLA E' CHIUSA, sempre — anche in creazione.
             L'aliquota la decide il risolutore, e lasciarla modificabile
             riaprirebbe la seconda risposta alla stessa domanda che tutto
             questo cantiere e' servito a togliere. Il campo resta a VIDEO, e
             spento: l'operatore deve poter vedere cosa gli viene applicato.
             ⚠️ Se serve cambiarla, si cambia sull'ARTICOLO — ed e' quello che
             dicono ora i messaggi dei gate all'emissione. -->
        <IvaSelect v-model="form.iva_id"
          :placeholder="t('vendite.preventivi.riga_iva')" disabled />
        <!-- ⭐ IL PERCHE' DI QUEL NUMERO. `I6` sta per togliere all'operatore
             la casella: un'aliquota che non si puo' cambiare E che non viene
             spiegata e' la forma peggiore. La label la compone il composable —
             qui non si costruisce nessun percorso i18n. -->
        <small v-if="ivaOrigine" class="app-field-hint">{{ ivaOrigineLabel }}</small>
      </div>
    </div>

    <div class="form-grid-2col" v-if="!isEdit">
      <div class="form-field">
        <label>{{ t('vendite.preventivi.riga_uom') }} *</label>
        <Select v-model="form.uom_operativa_id"
          :options="uomOptions" :option-label="uomLabel" option-value="uom_id"
          :loading="uomLoading"
          :disabled="!form.articolo_id || uomLoading"
          :placeholder="form.articolo_id
            ? t('vendite.preventivi.riga_uom')
            : t('vendite.promo_articoli.field_uom_articolo_first')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.preventivi.riga_ordine') }}</label>
        <InputNumber v-model="form.ordine" :use-grouping="false" />
      </div>
    </div>

    <!-- La data di consegna richiesta dal cliente (Blocco A): sul preventivo
         solo la richiesta, la conferma nasce sull'ordine. Il push la porta
         avanti: e' il punto in cui il documento cambia natura, e perderla li'
         e' il punto in cui gli utenti smetterebbero di fidarsene. -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.preventivi.riga_data_consegna_richiesta_cliente') }}</label>
        <DatePicker v-model="form.data_consegna_richiesta_cliente"
          :date-format="DATE_FORMAT" :min-date="minDataConsegna" show-icon show-button-bar />
      </div>
    </div>

    <L2ErrorBanner
      :error="l2Error"
      :loading="loading"
      :label="t('vendite.preventivi.richiedi_approvazione')"
      :label-loading="t('vendite.preventivi.richiedi_approvazione_in_corso')"
      :tooltip="t('vendite.preventivi.richiedi_approvazione_tooltip')"
      @richiedi="handleRichiediApprovazione"
    />

    <!-- Sezione componenti BoM CASO A: due rendering distinti.
         (1) EDIT (isCasoA): pannello componenti già persistiti, modifica prezzo
             per singolo componente via PATCH (Panel readonly=false).
         (2) CREATE form atomic 2026-05-12: preview pre-save con tabella
             editabile. Operatore valorizza prezzi mancanti (override
             autorizzato), Save include `componenti_overrides` che la fn DB
             init applica. -->
    <div v-if="isCasoA" class="app-drawer-section" style="margin-top: 1rem;">
      <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem;">
        {{ t('vendite.preventivi.componenti_section_title') }}
      </h4>
      <PreventiviRigaComponentiPanel
        :preventivo-id="preventivoId"
        :riga-id="props.riga.id"
        :readonly="false"
        @changed="emit('componenti-changed')" />
    </div>
    <!-- Modello unificato 2026-05-13: la ComponentiDialog si auto-apre al
         primo set valido (articolo composito + UoM + qta) tramite watcher.
         Per correggere gli override PRIMA del save riga c'e' il bottone
         "Modifica componenti" qui sotto (riapertura manuale). Il summary
         live mostra il numero di componenti coperti dall'ultima conferma.
         Il riepilogo persistito post-save vive nell'expansion della
         DataTable righe (`<ComponentiPanel :initial-data="row.componenti">`
         lato `PreventiviRigheTable`). -->
    <ComponentiCreateActionsPanel
      v-if="!isEdit && articoloObj?.is_composito"
      section-title-key="vendite.preventivi.componenti_section_title"
      :disabled="!form.articolo_id || !form.uom_operativa_id
        || ((form.qta_operativa || 0) <= 0)"
      :componenti-payload="componentiPayload"
      @apri-dialog="apriComponentiDialog"
    />

    <ComponentiDialog
      v-if="showComponentiDialog"
      v-model:visible="componentiDialogVisible"
      :articolo="articoloObj"
      :documento-id="preventivoId"
      :uom-operativa-id="form.uom_operativa_id"
      :quantita="form.qta_operativa"
      :api-preview="previewRigaComponenti"
      :initial-payload="componentiPayload"
      @confirm="onComponentiConfirm"
    />

    <!-- Bottoni Salva/Annulla della riga: sempre visibili quando l'utente
         sta editando la riga. Il ComponentiDialog modale 90vw copre comunque
         la pagina mentre aperto, quindi non c'e' duplicazione visiva con
         i bottoni Conferma/Annulla del Dialog. I bottoni del FormFooter
         testata preventivo invece si nascondono via `formRigaAperto` lato
         PreventiviDrawer (pattern distinta base `ArticoloBomDrawer`). -->
    <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem;">
      <Button :label="t('common.cancel')" severity="secondary" @click="chiudiConConferma(() => emit('cancel'))" />
      <Button :label="t('common.save')" :loading="loading" :disabled="!canSave" @click="handleSave" />
    </div>
  </div>
</template>
