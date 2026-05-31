<script setup>
// Scopo: Sub-drawer gestione righe contratto (modello unificato 2026-05-15)
//        — pattern master-detail inline. Lista paginata sopra (10 righe/pagina),
//        form dettaglio sotto. Click riga = edit, pulsante Nuovo = create,
//        Salva/Annulla sempre in basso.
//
// Refactor modalita 2026-05-15: le righe sono ECCEZIONI tipizzate del listino
// (tipo_eccezione = OVERRIDE / ESCLUSIONE / AGGIUNTA), non piu' "righe di
// modalita C". La forma del contratto e' "con_listino" o "senza_listino",
// derivata dalla testata. Le azioni "Modifica prezzo" (OVERRIDE), "Escludi"
// (ESCLUSIONE), "Aggiungi articolo" (AGGIUNTA) corrispondono ai 3 tipi.
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContrattiStore } from '../stores/contratti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import { useLimitiPricing } from '../composables/useLimitiPricing'
import { FONTE_QUANTITA_ATTESA, PRICING_ACTIONS, TIPO_ECCEZIONE } from '../constants'
import { extractApiError, extractApiErrorCode } from '../../core/utils/apiError'
import { DRAWER_WIDTH, MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { formatCurrency, formatNumber } from '../../core/utils/format'
import { statoContrattoSeverity } from '../../core/utils/severity'
import { useArticoloUomOptions } from '../../core/composables/useArticoloUomOptions'
import {
  previewRigaComponenti,
  listRigaComponenti as listContrattoRigaComponenti,
  updateRigaComponente as updateContrattoRigaComponente,
  deleteRigaComponente as deleteContrattoRigaComponente,
  getContrattoContestoPricing,
} from '../api/contratti'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerContextHeader from '../../core/components/DrawerContextHeader.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import { rowComponenti, hasBundleComponenti } from '../_shared/componenti/rowComponenti'
import ComponentiCreateActionsPanel from '../_shared/componenti/ComponentiCreateActionsPanel.vue'
import ComponentiDialog from '../_shared/componenti/ComponentiDialog.vue'
import { useComponentiDialog } from '../_shared/componenti/useComponentiDialog'
import ComponentiPanel from '../_shared/componenti/ComponentiPanel.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'

const { t } = useI18n()
const store = useContrattiStore()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmDelete, confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()

// L2 autorizzazioni prezzi: codici BE che il drawer intercetta per mostrare
// un banner inline invece del toast standard, con CTA "Richiedi approvazione"
// (workflow L3 cablato 2026-05-19 BE porting gate riga contratti). Riusato
// elenco da `useLimitiPricing` per coerenza col pattern preventivi.
const { L2_ERROR_CODES } = useLimitiPricing()
const l2Error = ref(null)

// Gate L1 azioni di riga "variare prezzi" (label UX): decisione 2026-05-18.
// Codename DB stabile `prezzo_override_manuale`. La gate vale per le azioni
// che mutano il prezzo (Modifica prezzo, Aggiungi articolo). Anche "Escludi"
// e' negoziazione contrattuale e richiede lo stesso permesso: l'esclusione
// modifica il rapporto commerciale col cliente, non e' meno sensibile.
// Senza permesso le azioni sono `visible:false` (UX pulita) e il BE
// re-blocca con 403 retryable (defense-in-depth).
const auth = useAuthStore()
const canVariarePrezzi = computed(() => auth.isActionAllowed(PRICING_ACTIONS.OVERRIDE))

const props = defineProps({
  visible: Boolean,
  contrattoId: { type: Number, required: true },
  // Refactor modalita 2026-05-15: niente piu' modalita A/B/C. La "forma"
  // arriva dal parent (derivata dai campi testata) ed e' "con_listino" o
  // "senza_listino". Default null: il drawer attende il dato dal parent
  // o fallback a `previewMeta.forma` dopo loadPreview (recap §3.2 fix:
  // niente piu' hardcoded 'B' default).
  contrattoForma: { type: String, default: null },
  righeIniziali: { type: Array, default: () => [] },
  // Contesto contratto (per intestazione riepilogativa)
  contrattoNumero: { type: String, default: '' },
  contrattoCliente: { type: String, default: '' },
  contrattoValidoDal: { type: String, default: '' },
  contrattoValidoAl: { type: String, default: null },
  contrattoStatoCodice: { type: String, default: '' },
  contrattoStatoDescrizione: { type: String, default: '' },
})
const emit = defineEmits(['update:visible', 'changed'])

const righe = ref([])

// === Preview righe applicate (refactor modalita 2026-05-15) ===
// previewMeta: testata sintetica (forma, listino, listino_versione_id, variazione)
// previewRighe: lista preview con origine = 'DA_LISTINO' | 'OVERRIDE' |
//   'ESCLUSIONE' | 'AGGIUNTA' (post step 2.4 resolver BE)
const previewMeta = ref(null)
const previewRighe = ref([])
const previewLoading = ref(false)

// Righe espanse nel DataTable (bundle padre → figli annidati). Pattern
// uniforme con preventivi (PreventiviRigheTable.vue). PrimeVue v-model
// espone l'oggetto indicizzato per data-key. Stato locale, non persistito.
const expandedRows = ref({})

// === Contesto pricing contratto (FE 2.2) ===
// Mutuato dal pattern preventivi `getContestoPricing`. Espone forma, listino
// + versione fissata (post-attivazione) o corrente (DRAFT), variazione,
// categoria cliente. Renderizzato come banner informativo nell'header drawer.
const contestoPricing = ref(null)

// Forma effettiva: priorita' al backend (previewMeta.forma o contestoPricing.forma),
// fallback alla prop. None = drawer non ancora inizializzato.
const formaEffettiva = computed(() =>
  previewMeta.value?.forma
  || contestoPricing.value?.forma
  || props.contrattoForma,
)
const isSenzaListino = computed(() => formaEffettiva.value === 'senza_listino')

// Filtro full-text articolo (codice + descrizione, case-insensitive).
// Applicato client-side: la lista preview e' gia' paginata nel DataTable
// e tipicamente sotto le 100-200 righe per listino. Per liste massive
// si potrebbe muovere il filtro server-side (param query string) — per
// ora MVP client.
const filtroArticolo = ref('')

// Lista renderizzata. In A/B arricchiamo con `_row_key` sintetico univoco
// (articolo_id + uom_id): un articolo con piu' UoM nel listino genera
// piu' righe preview con stesso articolo_id, quindi articolo_id da solo
// non e' un dataKey valido per il DataTable (PrimeVue v-model:selection
// confonderebbe le righe). In C il dataKey resta `id` (PK contratti_righe).
const righeView = computed(() => {
  const filtro = (filtroArticolo.value || '').trim().toLowerCase()
  const matchFiltro = (r) => {
    if (!filtro) return true
    const codice = (r.articolo_codice || '').toLowerCase()
    const desc = (r.articolo_descrizione || '').toLowerCase()
    return codice.includes(filtro) || desc.includes(filtro)
  }
  if (isSenzaListino.value) {
    return righe.value.filter(matchFiltro)
  }
  return (previewRighe.value || [])
    .filter(matchFiltro)
    .map(r => ({
      ...r,
      _row_key: `${r.articolo_id}__${r.uom_id ?? 'null'}`,
    }))
})
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: reloadList,
  },
  // Refactor 2026-05-18 (FE 2.2 Opzione C): l'unica azione globale di create
  // diretta dalla toolbar e' "Aggiungi articolo" (tipo_eccezione=AGGIUNTA:
  // articolo fuori-listino). Le azioni OVERRIDE/ESCLUSIONE si fanno
  // contestualmente sulle righe DA_LISTINO via kebab. Gate L1 visibile per
  // simmetria con le azioni di riga: senza permesso `prezzo_override_manuale`
  // non puoi nemmeno aggiungere articoli.
  {
    key: 'aggiungi-articolo',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('contratti.aggiungi_articolo_tooltip'),
    icon: MANAGE_ICONS.ADD,
    visible: canVariarePrezzi.value,
    disabled: formMode.value === 'create' || isReadonly.value,
    command: onAggiungiArticolo,
  },
])

// Scopo: chiave riga coerente con la `data-key` dinamica del DataTable.
// con_listino usa `_row_key` (preview, niente PK stabile per le righe
// DA_LISTINO); senza_listino usa `id` (riga persistita in contratti_righe).
// Senza questa coerenza l'expansion del ramo senza_listino non funziona
// (key undefined -> no-op).
function rowExpansionKey(row) {
  return isSenzaListino.value ? row?.id : row?._row_key
}

// Scopo: stato espansione corrente della riga. v-model:expandedRows
// PrimeVue indicizza per data-key value.
function isExpanded(row) {
  const key = rowExpansionKey(row)
  if (key == null) return false
  return Object.prototype.hasOwnProperty.call(expandedRows.value, key)
}

// Scopo: toggle espansione di una singola riga. Pattern uniforme con
// PreventiviRigheTable (set/delete chiave nell'oggetto).
function toggleExpansion(row) {
  const key = rowExpansionKey(row)
  if (key == null) return
  const next = { ...expandedRows.value }
  if (Object.prototype.hasOwnProperty.call(next, key)) {
    delete next[key]
  } else {
    next[key] = true
  }
  expandedRows.value = next
}

// Scopo: classe CSS sulla riga DataTable. In readonly (permessi LETTURA o
// contratto post-DRAFT) tutte le righe sono visualmente readonly. In edit
// le righe con origine='DA_LISTINO' restano readonly perche' preview pure
// senza record contratti_righe dietro. Coerente col guard BE Profilo A.
function rowClass(data) {
  if (isReadonly.value) return 'app-row-readonly'
  if (data?.origine === 'DA_LISTINO') return 'app-row-readonly'
  return null
}

async function loadPreview() {
  if (!props.contrattoId) return
  // Forma "senza_listino" (ex-modalita C): nessuna preview da caricare —
  // le righe vivono direttamente in `contratti_righe` (tutte AGGIUNTA).
  if (props.contrattoForma === 'senza_listino') {
    previewMeta.value = { forma: 'senza_listino', righe: [] }
    previewRighe.value = []
    return
  }
  previewLoading.value = true
  try {
    const data = await store.fetchRighePreview(props.contrattoId)
    previewMeta.value = data
    previewRighe.value = data?.righe || []
  } catch {
    previewMeta.value = null
    previewRighe.value = []
  } finally {
    previewLoading.value = false
  }
}

// Carica il contesto pricing per il banner header (FE 2.2). Mutuato dal
// pattern preventivi: best-effort, un fail non blocca il drawer.
async function loadContestoPricing() {
  if (!props.contrattoId) {
    contestoPricing.value = null
    return
  }
  try {
    const res = await getContrattoContestoPricing(props.contrattoId)
    contestoPricing.value = res?.data?.data || null
  } catch (err) {
    contestoPricing.value = null
    console.warn('contratto contesto pricing fetch failed',
      err?.response?.data || err)
  }
}

// Scopo: handler @changed di ComponentiPanel API-driven in EDIT su
//        articolo composito. Dopo PATCH componente, il trigger DB
//        `_z90_ricalcola_padre` ha aggiornato `prezzo_unitario` sulla
//        riga padre. Risincronizza solo quel campo del form (UI mostra
//        SUM aggiornato) senza chiudere/riaprire l'EDIT e senza perdere
//        modifiche pending dell'utente (qty/ordine/ecc.). Forma A/B:
//        refresh locale via `loadPreview()`. Forma senza_listino: la
//        lista vive in `contratti_righe`, viene rinfrescata dal parent
//        via `emit('changed')` → props.righeIniziali → watcher (vedi
//        sotto). Simmetrico a OffertaEccezioniDrawer.reload 2026-05-29.
// Flag attivato quando il refresh `righe` dal parent deve risincronizzare
// `form.prezzo_unitario` (caso senza_listino: il parent ricarica async dopo
// `emit('changed')`, il sync va deferred al watcher props.righeIniziali).
const _componentiPanelChangedPending = ref(false)

async function onComponentiPanelChanged() {
  if (isSenzaListino.value) {
    // Forma senza_listino: la riga vive in `contratti_righe` e arriva via
    // props dal parent (ContrattoDrawer). Il parent ricarica async dopo
    // `emit('changed')` → re-passa `props.righeIniziali` → watcher
    // aggiorna `righe.value`. Il sync `form.prezzo_unitario` viene
    // applicato dal watcher quando il flag pending è true.
    _componentiPanelChangedPending.value = true
    emit('changed')
    return
  }
  emit('changed')
  // Forma A/B: la lista vive in preview, refresh locale via loadPreview.
  await loadPreview()
  if (formMode.value === 'edit' && rigaEditId.value != null) {
    // Match con LO STESSO ordine di `_onEditRigaPersistita` (riga 705):
    // `rigaEditId = r.id ?? r.override_riga_id`. Cascade prezzi:
    // snapshot OVERRIDE → override esplicito → prezzo finale applicato.
    const refreshed = previewRighe.value.find(
      (r) => (r.id ?? r.override_riga_id) === rigaEditId.value,
    )
    if (refreshed) {
      const nuovoPrezzo = refreshed.prezzo_unitario
        ?? refreshed.override_prezzo
        ?? refreshed.prezzo_finale
      if (nuovoPrezzo != null) {
        form.value.prezzo_unitario = Number(nuovoPrezzo)
      }
    }
  }
}

// Reload completo: in modalita' A/B ricarica la preview dal BE; in modalita'
// C la lista contratti_righe viene rinfrescata dal parent (emit changed).
// Usato sia dal pulsante Ricarica sia dallo shortcut F5 globale.
async function reloadList() {
  if (!props.visible) return
  if (isSenzaListino.value) {
    emit('changed')
  } else {
    await loadPreview()
  }
}

// Shortcut F5: ricarica la lista senza reload del browser. Coerente con
// il pattern useSearchTable usato dalle liste main. Attivo solo quando
// il drawer e' visibile (registrato in onMounted, deregistrato in onUnmounted
// — il drawer e' un componente persistente, non viene smontato a chiusura).
function onKeydown(e) {
  if (e.key === 'F5' && props.visible) {
    e.preventDefault()
    reloadList()
  }
}
onMounted(() => { window.addEventListener('keydown', onKeydown) })
onUnmounted(() => { window.removeEventListener('keydown', onKeydown) })

// === Form state ===
// formMode: null (nessun form), 'create', 'edit'
const formMode = ref(null)
const rigaEditId = ref(null)
const form = ref({})
const selectedRow = ref(null)

// Articolo selezionato corrente con flag `is_composito` (dal lookup
// `ArticoloLookup` o ricostruito in `_onEditRigaPersistita` per EDIT). Driver della
// detection auto-apertura ComponentiDialog + visibilita' ComponentiPanel
// (modello unificato BoM 2026-05-13).
const articoloObj = ref(null)

// === ComponentiDialog state (modello unificato BoM 2026-05-13) ===
// Pattern speculare a `PreventiviRigaForm.vue`: in CREATE su articolo
// composito, la Dialog si auto-apre al primo set di (articolo, uom, qta)
// validi; in EDIT lo stato componenti viaggia via `ComponentiPanel` sotto
// il form (lista persistita).
// Orchestrazione ComponentiDialog centralizzata nel BB `useComponentiDialog`
// (estrazione regola-del-2 2026-05-31). In CREATE l'auto-open scatta su
// articolo composito + UoM + qta valida (default `qta_operativa <> 0`); in
// EDIT il flusso e' diverso (panel sotto, no Dialog). isComposito e
// isPadreComposito leggono `articoloObj.is_composito`.
const {
  componentiDialogVisible,
  componentiPayload,
  showComponentiDialog,
  apriComponentiDialog,
  onComponentiConfirm,
  resetComponentiDialog,
} = useComponentiDialog({
  form,
  isCreate: () => formMode.value === 'create',
  isComposito: () => articoloObj.value?.is_composito === true,
  isPadreComposito: () => articoloObj.value?.is_composito === true,
})

// Componenti della riga sorgente cliccata, in shape preview (jsonb dalla fn
// DB). Popolato quando si apre il form OVERRIDE da una riga DA_LISTINO
// composita: i suoi componenti vivono nel listino (non in
// contratti_righe_componenti), quindi l'`api-list` del ComponentiPanel
// sarebbe vuota. Li mostriamo read-only inline (data-driven) cosi' l'operatore
// vede subito la composizione, come nell'OffertaEccezioniDrawer. Vuoto per
// "Aggiungi articolo" (nessuna riga sorgente).
const selectedRowComponenti = ref([])

// Reset banner L2 se l'utente modifica prezzo o articolo: segnale di retry
// con contesto potenzialmente diverso. Pattern identico a PreventiviRigaForm.
watch(
  () => [form.value.prezzo_unitario, form.value.articolo_id],
  () => { if (l2Error.value) l2Error.value = null },
)

// === UoM operative dell'articolo selezionato ===
// Composable centralizzato (Fase 4.F1). Autopick base se il form e' attivo
// (create OR edit con UoM mancante) — replica l'esatto criterio originale.
const {
  uomOptions, uomLoading, loadUomPerArticolo, pickBaseUomId, resetUomOptions,
} = useArticoloUomOptions()

function uomLabel(item) {
  return item.is_base ? `${item.uom_codice} (base)` : item.uom_codice
}

async function caricaUomConPickBase(articoloId) {
  const list = await loadUomPerArticolo(articoloId)
  if (formMode.value && !form.value.uom_operativa_id) {
    form.value.uom_operativa_id = pickBaseUomId(list)
  }
}

// === Options ===
const tipoErogazioneOptions = computed(() => [
  { value: 'CANONE', label: t('contratti.tipo_erogazione_canone') },
  { value: 'CONSUMO', label: t('contratti.tipo_erogazione_consumo') },
  { value: 'UNA_TANTUM', label: t('contratti.tipo_erogazione_una_tantum') },
])

// Refactor 2026-05-19: matrice (tipo_erogazione × fonte_quantita_attesa).
// Le fonti vietate (CHECK chk_contrighe_coerenza_fonte_erogazione, migration
// 20260519-05) NON appaiono nelle liste — il Select e' filtrato per tipo.
// severity: 'warn' = uso atipico (🟡 nella matrice), undefined = valida.
// default: true = scelta predefinita pre-compilata in CREATE.
// TIMESHEET commentato finche' il modulo rendicontazione ore non esistera'.
// Riferimento: docs/it/dev/work-done/refactor-contratti-fonte-quantita.md §3.
const FONTI_PER_TIPO_EROGAZIONE = {
  CANONE: [
    { value: FONTE_QUANTITA_ATTESA.FISSA, default: true },
    { value: FONTE_QUANTITA_ATTESA.MANUALE, severity: 'warn' },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
  UNA_TANTUM: [
    { value: FONTE_QUANTITA_ATTESA.FISSA, default: true },
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
  ORARIO: [
    { value: FONTE_QUANTITA_ATTESA.FISSA, severity: 'warn' },
    { value: FONTE_QUANTITA_ATTESA.MANUALE, default: true },
    // { value: FONTE_QUANTITA_ATTESA.TIMESHEET },  // attivare quando il modulo timesheet esistera'
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI, severity: 'warn' },
  ],
  CONSUMO: [
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.LETTURE, default: true },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
}

function _fontiPerTipo(tipo) {
  return FONTI_PER_TIPO_EROGAZIONE[tipo] || []
}

function _defaultFontePerTipo(tipo) {
  return _fontiPerTipo(tipo).find(f => f.default)?.value ?? null
}

const fonteQuantitaOptions = computed(() => _fontiPerTipo(form.value?.tipo_erogazione).map(f => ({
  value: f.value,
  label: t(`contratti.fonte_quantita_value_${f.value.toLowerCase()}`),
  severity: f.severity,
})))

const fonteCorrente = computed(() => fonteQuantitaOptions.value.find(f => f.value === form.value?.fonte_quantita_attesa) || null)

// Q.ta operativa visibile/obbligatoria solo per fonte FISSA. Per le altre
// 4 fonti il valore vero nasce downstream (manuale sul documento / timesheet
// / letture / derivato dai componenti via trigger DB z90_propaga_qta_componenti).
const showQtaOperativa = computed(() => form.value?.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA)

// Refactor 2026-05-18 (FE 2.2 Opzione C): il tipo_eccezione non e' piu' una
// scelta dell'operatore via Select, ma e' DERIVATO dall'azione che ha aperto
// il form:
//   - toolbar "Aggiungi articolo"     -> AGGIUNTA (articolo libero)
//   - kebab riga DA_LISTINO "Mod.prezzo" -> OVERRIDE (articolo precompilato)
//   - kebab riga DA_LISTINO "Escludi"  -> ESCLUSIONE (one-click, salvataggio diretto)
// Il form mostra il tipo come Tag readonly (sia CREATE che EDIT), niente
// piu' ambiguita' "che tipo voglio creare?". Default AGGIUNTA: l'azione
// toolbar e' il punto di ingresso piu' generico.
function defaultForm(overrides = {}) {
  const tipo = overrides.tipo_erogazione || 'CANONE'
  return {
    articolo_id: null,
    articolo_obj: null,
    tipo_eccezione: 'AGGIUNTA',
    tipo_erogazione: tipo,
    // Refactor 2026-05-19: fonte derivata dalla matrice in base al tipo
    // (default = FISSA per CANONE/UNA_TANTUM). Il BE applica lo stesso
    // default se assente (defense-in-depth), ma pre-compilare in UI
    // rende esplicita la scelta predefinita all'utente.
    fonte_quantita_attesa: _defaultFontePerTipo(tipo),
    prezzo_unitario: null,
    qta_operativa: 1,
    uom_operativa_id: null,
    ordine: 10,
    ...overrides,
  }
}

// Reset stato componenti BoM: chiamato da `closeForm` e dagli ingressi
// CREATE (`onAggiungiArticolo`, `onModificaPrezzo`).
// Tiene insieme `articoloObj` + Dialog state per evitare drift.
function resetComponentiState() {
  articoloObj.value = null
  resetComponentiDialog()
  selectedRowComponenti.value = []
}

// === Lifecycle ===
watch(() => props.visible, (v) => {
  if (v) {
    righe.value = [...(props.righeIniziali || [])]
    closeForm()
    loadPreview()
    loadContestoPricing()
  } else {
    contestoPricing.value = null
  }
})

watch(() => props.righeIniziali, (v) => {
  righe.value = [...(v || [])]
  // Se il refresh arriva dal flusso ComponentiPanel @changed in
  // senza_listino, ri-sincronizza `form.prezzo_unitario` dalla riga
  // aggiornata (il trigger DB `_z90_ricalcola_padre` ha appena scritto
  // il nuovo SUM). Senza questo handler il drawer mostrava il prezzo
  // stantio mentre la lista in alto era già aggiornata (bug osservato
  // 2026-05-29). Si reset comunque il flag a fine ciclo per non lasciare
  // sync residui su refresh successivi (es. save eccezione altra).
  if (_componentiPanelChangedPending.value
      && formMode.value === 'edit'
      && rigaEditId.value != null) {
    const refreshed = (v || []).find((r) => r.id === rigaEditId.value)
    if (refreshed?.prezzo_unitario != null) {
      form.value.prezzo_unitario = Number(refreshed.prezzo_unitario)
    }
    _componentiPanelChangedPending.value = false
  }
}, { deep: true })

// Refactor 2026-05-19: reset di `fonte_quantita_attesa` al cambio
// `tipo_erogazione` SOLO se la combo nuova diventa vietata
// (decisione 3 della sessione 2026-05-19, speculare al trigger DB
// trg_contratti_righe_a10_default_fonte_qta_ins_upd).
// Preserva la scelta utente quando possibile, applica il default
// del nuovo tipo solo quando necessario.
watch(() => form.value?.tipo_erogazione, (nuovoTipo, vecchioTipo) => {
  if (!nuovoTipo || nuovoTipo === vecchioTipo) return
  const fontiValide = _fontiPerTipo(nuovoTipo).map(f => f.value)
  if (!fontiValide.includes(form.value.fonte_quantita_attesa)) {
    form.value.fonte_quantita_attesa = _defaultFontePerTipo(nuovoTipo)
  }
})

// === Azioni ===

// Scopo: ingresso CREATE "Aggiungi articolo" (azione toolbar). Articolo
//        libero (autocomplete), tipo_eccezione=AGGIUNTA (articolo fuori-listino).
function onAggiungiArticolo() {
  form.value = defaultForm({ tipo_eccezione: 'AGGIUNTA' })
  formMode.value = 'create'
  rigaEditId.value = null
  selectedRow.value = null
  resetUomOptions()
  // resetComponentiState azzera anche selectedRowComponenti: articolo nuovo
  // fuori-listino, nessuna composizione sorgente da mostrare. Se composito,
  // i componenti si definiscono via ComponentiDialog (bottone).
  resetComponentiState()
}

// Scopo: ingresso CREATE "Modifica prezzo" da kebab di una riga DA_LISTINO
//        della preview. Pre-compila articolo (immutabile), UoM e prezzo dal
//        listino: l'operatore deve solo cambiare il prezzo. tipo_eccezione
//        derivato = OVERRIDE.
function onModificaPrezzo(row) {
  form.value = defaultForm({
    tipo_eccezione: 'OVERRIDE',
    articolo_id: row.articolo_id,
    articolo_obj: {
      id: row.articolo_id,
      codice: row.articolo_codice,
      descrizione: row.articolo_descrizione,
      is_composito: row.is_composito === true,
      _display: `${row.articolo_codice} — ${row.articolo_descrizione}`,
    },
    // Prezzo iniziale = prezzo listino corrente. L'operatore lo modifica.
    // Number() per InputNumber (Decimal raw potrebbe arrivare come stringa).
    prezzo_unitario: row.prezzo_listino != null ? Number(row.prezzo_listino) : null,
    uom_operativa_id: row.uom_id ?? null,
    qta_operativa: row.qta_operativa != null ? Number(row.qta_operativa) : 1,
  })
  // articoloObj fuori dal form per i computed `isCompositoCorrente` & co.
  articoloObj.value = form.value.articolo_obj
  formMode.value = 'create'
  rigaEditId.value = null
  selectedRow.value = null
  // Carica le UoM operative dell'articolo per popolare uomOptions: senza
  // fetch il Select UoM mostrerebbe vuoto anche con uom_operativa_id
  // pre-selezionato (PrimeVue richiede che il valore sia nelle options).
  // Pattern identico a `_onEditRigaPersistita` per righe OVERRIDE gia' esistenti.
  resetComponentiState()
  // Composizione del bundle DA_LISTINO da mostrare read-only inline (i figli
  // del listino non sono persistiti in contratti_righe_componenti, quindi
  // l'api-list del ComponentiPanel sarebbe vuota). DOPO resetComponentiState
  // che azzera selectedRowComponenti. `resetComponentiState` azzera anche
  // articoloObj: per onModificaPrezzo questo e' voluto (impedisce l'auto-open
  // della ComponentiDialog), e il blocco read-only si basa su
  // selectedRowComponenti, non su articoloObj.
  selectedRowComponenti.value = rowComponenti(row)
  loadUomPerArticolo(row.articolo_id)
}

// Scopo: azione one-click "Escludi" da kebab di una riga DA_LISTINO. Dialog
//        di conferma + salvataggio diretto come ESCLUSIONE (prezzo NULL,
//        UoM dal listino). Niente form: la sola scelta dell'operatore e' SI/NO.
function onEscludi(row) {
  const label = row.articolo_codice
    ? `${row.articolo_codice} — ${row.articolo_descrizione}`
    : row.articolo_descrizione
  confirmAction({
    header: t('contratti.escludi_dialog_titolo'),
    message: t('contratti.escludi_dialog_messaggio', { articolo: label }),
    acceptLabel: t('contratti.escludi_dialog_conferma'),
    danger: true,
    onAccept: async () => {
      const payload = {
        articolo_id: row.articolo_id,
        tipo_eccezione: 'ESCLUSIONE',
        prezzo_unitario: null,  // vincolo BE
        uom_operativa_id: row.uom_id ?? null,
        qta_operativa: '1',
        tipo_erogazione: null,
      }
      const result = await execute(
        () => store.addRiga(props.contrattoId, payload),
        { successMessage: t('contratti.articolo_escluso') },
      )
      if (result !== null) {
        if (!isSenzaListino.value) await loadPreview()
        emit('changed')
      }
    },
  })
}

// Scopo: handler unificato click di riga (allineamento UX standard del progetto
//        — frontend-standards §"Pattern lista": modifica = click riga, kebab
//        riservato ad azioni secondarie).
//        - readonly: no-op
//        - riga DA_LISTINO (preview): apre il form pre-compilato come OVERRIDE
//          (delega a onModificaPrezzo, ex-azione "matita" rimossa dal kebab)
//        - riga persistita (OVERRIDE/AGGIUNTA/ESCLUSIONE): apre edit normale
//        Inoltre auto-espande la riga corrente se composita, cosi' l'operatore
//        vede subito la composizione BoM inline durante l'edit (simmetria con
//        PreventiviRigheTable).
function onRowClick(event) {
  const r = event.data
  if (isReadonly.value) return
  // Auto-expand inline se la riga e' un bundle composito: nessun click extra
  // sul chevron, il dettaglio componenti diventa subito visibile.
  if (hasBundleComponenti(r) && !isExpanded(r)) {
    toggleExpansion(r)
  }
  // DA_LISTINO: pre-compila il form come OVERRIDE (era il vecchio "Modifica prezzo").
  if (r.origine === 'DA_LISTINO') {
    onModificaPrezzo(r)
    return
  }
  _onEditRigaPersistita(r)
}

// Scopo: apertura form EDIT per righe persistite (override/aggiunta/esclusione).
//        Estratto da onRowClick per non duplicare la logica di restore form.
function _onEditRigaPersistita(r) {
  // ID dipende dalla modalita': in A/B usa override_riga_id (preview),
  // in C usa r.id (riga contratto persistita).
  const rigaId = r.id ?? r.override_riga_id
  form.value = {
    articolo_id: r.articolo_id,
    articolo_obj: { id: r.articolo_id, codice: r.articolo_codice, descrizione: r.articolo_descrizione, _display: `${r.articolo_codice} — ${r.articolo_descrizione}` },
    // tipo_eccezione: immutabile in EDIT (refactor 2026-05-15). Mostrato
    // come Tag readonly nel template form. Fallback OVERRIDE per righe
    // legacy che non avevano ancora il campo (transitorio).
    tipo_eccezione: r.tipo_eccezione || 'OVERRIDE',
    tipo_erogazione: r.tipo_erogazione || 'CANONE',
    // Refactor 2026-05-19: fonte_quantita_attesa NOT NULL post-migration
    // 20260519-05. Fallback dal default della matrice solo per righe legacy
    // che non avessero ancora il campo (transitorio, non dovrebbe accadere).
    fonte_quantita_attesa: r.fonte_quantita_attesa
      || _defaultFontePerTipo(r.tipo_erogazione || 'CANONE'),
    prezzo_unitario: (r.prezzo_unitario ?? r.override_prezzo) != null
      ? Number(r.prezzo_unitario ?? r.override_prezzo)
      : null,
    qta_operativa: r.qta_operativa != null ? Number(r.qta_operativa) : 1,
    uom_operativa_id: r.uom_operativa_id ?? r.uom_id,
    ordine: r.ordine || 10,
  }
  // Modello unificato BoM 2026-05-13: in EDIT articoloObj porta is_composito
  // se disponibile dalla riga (proiezione BE denormalizzata; fallback false
  // se non esposto). Driver visibilita' ComponentiPanel sotto il form.
  articoloObj.value = {
    id: r.articolo_id,
    codice: r.articolo_codice,
    descrizione: r.articolo_descrizione,
    is_composito: r.is_composito === true,
  }
  // EDIT: chiudi ogni Dialog stantia, il pannello sotto e' l'entrypoint
  // per modificare i componenti persistiti (no Dialog).
  resetComponentiDialog()
  // EDIT riga persistita: i componenti arrivano dal ComponentiPanel via
  // api-list (persistiti). Niente blocco read-only da preview.
  selectedRowComponenti.value = []
  formMode.value = 'edit'
  rigaEditId.value = rigaId
  // Edit con UoM pre-popolata dalla riga: niente autopick, solo fetch.
  loadUomPerArticolo(r.articolo_id)
}

function onArticoloSelected(item) {
  form.value.articolo_id = item?.id || null
  form.value.uom_operativa_id = null
  // Modello unificato BoM 2026-05-13: snapshot articolo (incluso flag
  // `is_composito` esposto dal lookup) per detection ComponentiDialog
  // post pickBase UoM nel watch sopra.
  articoloObj.value = item || null
  // Cambio articolo: reset stato Dialog (payload + key auto-open) per
  // consentire la riapertura sul nuovo articolo.
  resetComponentiDialog()
  // Cambio articolo in form aperto: autopick base.
  caricaUomConPickBase(item?.id)
}

function closeForm() {
  formMode.value = null
  rigaEditId.value = null
  form.value = {}
  selectedRow.value = null
  resetUomOptions()
  resetComponentiState()
}

// === Validazione ===
const canSave = computed(() => {
  if (isReadonly.value) return false
  if (!formMode.value) return false
  if (!form.value.articolo_id) return false
  if (!form.value.uom_operativa_id) return false
  // Refactor 2026-05-19: fonte_quantita_attesa NOT NULL (CHECK DB).
  // Per FISSA serve qta_operativa valorizzata e diversa da zero (CHECK DB
  // `qta_operativa <> 0`: negativi ammessi, es. resi/note credito); per le
  // altre 4 fonti la quantita arriva downstream (manuale/timesheet/letture)
  // o dal trigger DB (derivata_componenti).
  if (!form.value.fonte_quantita_attesa) return false
  if (form.value.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA
      && (form.value.qta_operativa == null || Number(form.value.qta_operativa) === 0)) {
    return false
  }
  // Refactor modalita 2026-05-15: coerenza prezzo_unitario / tipo_eccezione
  // (specchio del check BE _build_data_riga):
  //   - ESCLUSIONE: prezzo NULL ammesso (l'articolo non e' disponibile)
  //   - OVERRIDE / AGGIUNTA: prezzo obbligatorio (e' il prezzo finale),
  //     EXCEPT articoli compositi dove il prezzo padre = SUM(componenti)
  //     viene popolato dal trigger DB post-init.
  const tipo = form.value.tipo_eccezione
  const prezzoMancante = form.value.prezzo_unitario == null
    || form.value.prezzo_unitario === ''
  if (tipo !== 'ESCLUSIONE'
      && !articoloObj.value?.is_composito
      && prezzoMancante) return false
  // Modello unificato BoM 2026-05-13: in CREATE su articolo composito,
  // blocca il save finche' la ComponentiDialog non e' stata confermata
  // almeno una volta (componentiPayload != null). Se l'operatore annulla
  // resta bloccato — deve riaprire e confermare.
  if (showComponentiDialog.value && componentiPayload.value == null) return false
  return true
})

const formTitle = computed(() => {
  if (formMode.value === 'create') return t('contratti.nuova_riga')
  if (formMode.value === 'edit') return t('contratti.modifica_riga')
  return ''
})

// === Salvataggio ===

// Scopo: centralizza la costruzione del payload usato da onSave e da
//        onRichiediApprovazione. `extra` permette di iniettare il flag
//        opt-in `richiesta_approvazione: true` per il retry workflow L3
//        senza duplicare la build.
function buildRigaPayload(extra = {}) {
  const f = form.value
  // Refactor 2026-05-19: `qta_operativa` inviata solo per fonte FISSA.
  // Per le altre fonti (downstream o derivata) il BE forza NULL via
  // `_apply_fonte_quantita_logic`; inviare un valore qui sarebbe
  // semanticamente fuorviante (la fonte e' il driver).
  const isFissa = f.fonte_quantita_attesa === FONTE_QUANTITA_ATTESA.FISSA
  const payload = {
    tipo_erogazione: f.tipo_erogazione || null,
    fonte_quantita_attesa: f.fonte_quantita_attesa || null,
    prezzo_unitario: f.prezzo_unitario != null ? String(f.prezzo_unitario) : null,
    qta_operativa: (isFissa && f.qta_operativa != null) ? String(f.qta_operativa) : null,
    uom_operativa_id: f.uom_operativa_id || null,
    ordine: f.ordine != null ? Number(f.ordine) : null,
    ...extra,
  }
  if (formMode.value === 'create') {
    payload.articolo_id = f.articolo_id
    payload.tipo_eccezione = f.tipo_eccezione || 'OVERRIDE'
    // ESCLUSIONE: BE rifiuta prezzo non-null. Forziamo null per safety.
    if (payload.tipo_eccezione === 'ESCLUSIONE') {
      payload.prezzo_unitario = null
    }
    // Modello unificato BoM 2026-05-13: includi `componenti_overrides`
    // se l'articolo e' composito e la Dialog ha prodotto overrides delta.
    if (articoloObj.value?.is_composito === true
        && componentiPayload.value?.overrides) {
      payload.componenti_overrides = componentiPayload.value.overrides
    }
  }
  return payload
}

function submitRiga(payload) {
  return formMode.value === 'create'
    ? store.addRiga(props.contrattoId, payload)
    : store.updateRiga(props.contrattoId, rigaEditId.value, payload)
}

// Scopo: salva riga intercettando specificamente i codici L2
//        (E_PRICING_SCONTO_ECCESSIVO / E_PRICING_MAGGIORAZIONE_ECCESSIVA)
//        per mostrare un banner inline con CTA "Richiedi approvazione"
//        (workflow L3 cablato 2026-05-19) invece del toast standard.
//        Tutti gli altri errori passano per il pattern standard.
async function onSave() {
  l2Error.value = null
  const successMessage = formMode.value === 'create'
    ? t('contratti.riga_creata') : t('contratti.riga_salvata')

  loading.value = true
  try {
    await submitRiga(buildRigaPayload())
    notify.success(successMessage)
    if (!isSenzaListino.value) await loadPreview()
    emit('changed')
    closeForm()
  } catch (err) {
    const code = extractApiErrorCode(err)
    if (L2_ERROR_CODES.includes(code)) {
      l2Error.value = {
        code,
        message: extractApiError(err, t('contratti.errore_generico')),
        detail: err?.response?.data?.error?.detail || '',
      }
    } else {
      notify.error(extractApiError(err, t('contratti.errore_generico')))
    }
  } finally {
    loading.value = false
  }
}

// Scopo: ri-tenta il save aggiungendo flag richiesta_approvazione=true
//        (workflow L3). Il BE crea pratica APPROVAZIONE_PREZZO e salva la
//        riga in PENDING invece di sollevare. Toast esplicito.
async function onRichiediApprovazione() {
  l2Error.value = null
  loading.value = true
  try {
    await submitRiga(buildRigaPayload({ richiesta_approvazione: true }))
    notify.success(t('contratti.richiesta_approvazione_inviata'))
    if (!isSenzaListino.value) await loadPreview()
    emit('changed')
    closeForm()
  } catch (err) {
    notify.error(extractApiError(err, t('contratti.errore_generico')))
  } finally {
    loading.value = false
  }
}

function onDelete(r) {
  // ID contratti_righe: in C sta in r.id, in B (preview) sta in r.override_riga_id.
  const rigaId = r.id ?? r.override_riga_id
  const label = r.articolo_codice || r.articolo_descrizione || `#${rigaId}`
  confirmDelete(label, async () => {
    const result = await execute(
      () => store.deleteRiga(props.contrattoId, rigaId),
      { successMessage: t('contratti.riga_eliminata') }
    )
    if (result !== null) {
      // Se stavo editando questa riga, chiudi il form.
      if (rigaEditId.value === rigaId) closeForm()
      // In A/B la preview va ricaricata; in C il parent rilegge dalle righe.
      if (!isSenzaListino.value) await loadPreview()
      emit('changed')
    }
  })
}

// Scopo: ripristino eccezione (refactor UX 2026-05-19). Stessa azione DB di
//        onDelete (cancella la riga `contratti_righe`), ma con messaggio
//        parlante che spieghi il vero effetto: l'articolo non viene rimosso
//        dal contratto, torna al comportamento del listino. Riusato sia per
//        OVERRIDE ("Ripristina prezzo di listino") sia per ESCLUSIONE
//        ("Ripristina articolo nel contratto"): il backend e' identico, la
//        differenza e' solo il testo del confirm.
function onRipristina(r, origine) {
  const rigaId = r.id ?? r.override_riga_id
  const articoloLabel = r.articolo_codice
    ? `${r.articolo_codice} — ${r.articolo_descrizione}`
    : r.articolo_descrizione
  const prefix = origine === TIPO_ECCEZIONE.OVERRIDE
    ? 'ripristina_listino'
    : 'ripristina_articolo'
  confirmAction({
    header: t(`contratti.${prefix}_dialog_titolo`),
    message: t(`contratti.${prefix}_dialog_messaggio`, { articolo: articoloLabel }),
    acceptLabel: t(`contratti.${prefix}_dialog_conferma`),
    danger: false,
    onAccept: async () => {
      const result = await execute(
        () => store.deleteRiga(props.contrattoId, rigaId),
        { successMessage: t('contratti.riga_ripristinata') }
      )
      if (result !== null) {
        if (rigaEditId.value === rigaId) closeForm()
        if (!isSenzaListino.value) await loadPreview()
        emit('changed')
      }
    },
  })
}

const onClose = useDrawerClose(emit)

// Scopo: azioni di riga del master-detail. Differenziate per origine.
//        Allineamento UX standard del progetto (frontend-standards §"Pattern
//        lista"): la modifica avviene per click di riga, il kebab espone
//        solo azioni SECONDARIE distinte dall'edit.
//   - DA_LISTINO (preview puro): "Escludi" (one-click ESCLUSIONE con conferma).
//     La modifica prezzo arriva da onRowClick → onModificaPrezzo, niente matita.
//   - OVERRIDE: "Ripristina prezzo di listino" (DELETE → l'articolo torna
//     DA_LISTINO al prezzo originale). Refactor UX 2026-05-19.
//   - ESCLUSIONE: "Ripristina articolo nel contratto" (DELETE → l'articolo
//     torna disponibile al prezzo di listino). Refactor UX 2026-05-19.
//   - AGGIUNTA: "Rimuovi dal contratto" (DELETE → l'articolo sparisce; non
//     era nel listino, "elimina" semanticamente corretto).
function buildRigaActions(data) {
  if (data.origine === 'DA_LISTINO') {
    return [
      {
        key: 'escludi',
        label: t('contratti.azione_escludi'),
        icon: 'pi pi-ban',
        severity: 'warn',
        visible: !isReadonly.value && canVariarePrezzi.value,
        command: () => onEscludi(data),
      },
    ]
  }
  if (data.origine === TIPO_ECCEZIONE.OVERRIDE) {
    return [
      {
        key: 'ripristina-listino',
        label: t('contratti.azione_ripristina_listino'),
        icon: 'pi pi-replay',
        severity: 'secondary',
        visible: !isReadonly.value,
        command: () => onRipristina(data, TIPO_ECCEZIONE.OVERRIDE),
      },
    ]
  }
  if (data.origine === TIPO_ECCEZIONE.ESCLUSIONE) {
    return [
      {
        key: 'ripristina-articolo',
        label: t('contratti.azione_ripristina_articolo'),
        icon: 'pi pi-replay',
        severity: 'secondary',
        visible: !isReadonly.value,
        command: () => onRipristina(data, TIPO_ECCEZIONE.ESCLUSIONE),
      },
    ]
  }
  // AGGIUNTA: "Elimina" semanticamente corretto — l'articolo non e' nel
  // listino, sparisce davvero dal contratto.
  return [
    {
      key: 'rimuovi-aggiunta',
      label: t('contratti.azione_rimuovi_aggiunta'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: !isReadonly.value,
      command: () => onDelete(data),
    },
  ]
}

// Scopo: severity Tag per origine riga. Distinzione visiva delle 4 origini
// nella tabella righe: DA_LISTINO neutra (preview), OVERRIDE info (prezzo
// personalizzato), AGGIUNTA success (articolo aggiunto al contratto),
// ESCLUSIONE warn (articolo rimosso dal listino).
function origineSeverity(origine) {
  if (origine === TIPO_ECCEZIONE.OVERRIDE) return 'info'
  if (origine === TIPO_ECCEZIONE.AGGIUNTA) return 'success'
  if (origine === TIPO_ECCEZIONE.ESCLUSIONE) return 'warn'
  if (origine === TIPO_ECCEZIONE.DA_LISTINO) return 'secondary'
  return null
}
</script>

<template>
  <Drawer
    :visible="props.visible"
    @update:visible="val => emit('update:visible', val)"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE_PLUS }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle :title="t('contratti.drawer_righe_titolo')" :icon="MANAGE_ICONS.RIGHE" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- === Intestazione contesto contratto (BB DrawerContextHeader) === -->
      <DrawerContextHeader
        :tag-value="contrattoNumero"
        :items="[
          { label: t('contratti.col_ba'),         value: contrattoCliente },
          { label: t('contratti.col_valido_dal'), value: displayDate(contrattoValidoDal) },
          { label: t('contratti.col_valido_al'),  value: contrattoValidoAl ? displayDate(contrattoValidoAl) : '—' },
        ]">
        <template #status>
          <Tag v-if="contrattoStatoCodice"
            :value="contrattoStatoDescrizione"
            :severity="statoContrattoSeverity(contrattoStatoCodice)" />
        </template>
      </DrawerContextHeader>

      <!-- Banner contesto pricing (refactor modalita 2026-05-15, FE 2.2):
           mostra forma derivata + listino + versione fissata (post-attivazione)
           o corrente (DRAFT) + categoria cliente. Mutuato dal pattern preventivi. -->
      <Message v-if="contestoPricing"
        :severity="isSenzaListino ? 'warn' : 'info'"
        :closable="false" size="small">
        <div>
          <strong>{{ t(`contratti.forma_${formaEffettiva}_descrizione`) }}</strong>
        </div>
        <div v-if="contestoPricing.listino_codice" class="text-sm">
          {{ t('contratti.contesto_listino', {
            codice: contestoPricing.listino_codice,
            versione: contestoPricing.listino_versione_codice || '—',
          }) }}
          <Tag v-if="contestoPricing.listino_versione_fissata"
               :value="t('contratti.contesto_versione_fissata')"
               severity="success" class="ml-1" />
          <!-- Drift warning: il contratto e' fissato a una versione listino
               diversa da quella attualmente ATTIVA sul listino. Tag
               informativo, no blocco: i prezzi restano calcolati sulla
               fissata per design (snapshot post-attivazione). -->
          <Tag v-if="contestoPricing.drift_versione_listino"
               :value="t('contratti.contesto_drift_versione', {
                 versione_corrente: contestoPricing.listino_versione_corrente_codice,
               })"
               severity="warn" class="ml-1"
               v-tooltip.top="t('contratti.contesto_drift_versione_tooltip', {
                 versione_corrente: contestoPricing.listino_versione_corrente_codice,
                 versione_fissata: contestoPricing.listino_versione_codice,
               })" />
        </div>
        <div v-if="contestoPricing.tipo_variazione_globale" class="text-sm">
          {{ t('contratti.contesto_variazione', {
            tipo: contestoPricing.tipo_variazione_globale,
            valore: contestoPricing.valore_variazione_globale,
          }) }}
        </div>
        <div v-if="contestoPricing.categoria_cliente_codice" class="text-sm">
          {{ t('contratti.contesto_categoria', {
            codice: contestoPricing.categoria_cliente_codice,
          }) }}
        </div>
      </Message>

      <!-- Avviso "senza_listino": tutte le righe AGGIUNTA, prezzo obbligatorio. -->
      <Message v-if="isSenzaListino && !contestoPricing"
               severity="warn" :closable="false" size="small">
        {{ t('contratti.righe_senza_listino_warn') }}
      </Message>

      <!-- Avviso: listino associato ma senza versione operativa oggi.
           La preview e` vuota legittimamente, l'operatore deve attivare
           una versione del listino prima che il pricing sia calcolato. -->
      <Message v-if="previewMeta?.listino_senza_versione_oggi"
        severity="warn" :closable="false" size="small">
        {{ t('contratti.preview_listino_senza_versione', {
          codice: previewMeta.listino_codice || ''
        }) }}
      </Message>

      <!-- === MASTER: toolbar + lista paginata === -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="filtroArticolo"
            :placeholder="t('contratti.filtro_articolo_placeholder')"
            style="min-width: 240px;" />
        </div>
        <PageActionsBar :actions="pageActions" />
      </div>

      <DataTable
        :value="righeView"
        v-model:selection="selectedRow"
        v-model:expanded-rows="expandedRows"
        :loading="previewLoading"
        selection-mode="single"
        :data-key="isSenzaListino ? 'id' : '_row_key'"
        :row-class="rowClass"
        class="app-datatable app-datatable--inner"
        striped-rows
        paginator
        :rows="10"
        :rows-per-page-options="[10, 25, 50]"
        paginator-position="top"
        sort-field="articolo_descrizione"
        :sort-order="1"
        removable-sort
        @row-click="onRowClick"
      >
        <!-- Expander custom per bundle BoM: chevron visibile solo dove la
             riga è padre composito con figli (componenti JSONB non vuoto).
             @click.stop evita che il click apra anche il form di edit.
             Presente in ENTRAMBE le forme: con_listino (componenti dalla
             preview DB) e senza_listino (componenti aggregati da list_righe,
             ramo AGGIUNTA bundle persistite). -->
        <Column style="width: 2.5rem;" :exportable="false">
          <template #body="{ data }">
            <Button v-if="hasBundleComponenti(data)"
              :icon="isExpanded(data) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"
              text rounded size="small"
              v-tooltip.top="t('contratti.componenti_bundle_tooltip')"
              @click.stop="toggleExpansion(data)" />
          </template>
        </Column>
        <Column field="articolo_codice" :header="t('contratti.col_articolo')" sortable style="width: 150px;" />
        <Column field="articolo_descrizione" :header="t('contratti.col_descrizione')" sortable />
        <Column :header="t('contratti.col_uom')" style="width: 80px;">
          <template #body="{ data }">{{ data.uom_codice ?? '—' }}</template>
        </Column>
        <!-- Modalita' C: prezzo singolo. A/B: prezzo listino + prezzo finale + origine. -->
        <template v-if="isSenzaListino">
          <Column field="prezzo_unitario" :header="t('contratti.col_prezzo')" style="width: 90px;">
            <template #body="{ data }">
              {{ formatCurrency(data.prezzo_unitario, { placeholder: '—', maximumFractionDigits: 2 }) }}
            </template>
          </Column>
          <Column field="qta_operativa" :header="t('contratti.col_qta')" style="width: 70px;">
            <template #body="{ data }">
              {{ formatNumber(data.qta_operativa, { placeholder: '—', minimumFractionDigits: 0, maximumFractionDigits: 4 }) }}
            </template>
          </Column>
          <Column field="tipo_erogazione" :header="t('contratti.col_tipo_erogazione')" style="width: 100px;" />
        </template>
        <template v-else>
          <Column :header="t('contratti.col_prezzo_listino')" style="width: 110px;">
            <template #body="{ data }">
              {{ formatCurrency(data.prezzo_listino, { placeholder: '—', maximumFractionDigits: 2 }) }}
            </template>
          </Column>
          <Column :header="t('contratti.col_prezzo_finale')" style="width: 110px;">
            <template #body="{ data }">
              <span class="font-bold">
                {{ formatCurrency(data.prezzo_finale, { placeholder: '—', maximumFractionDigits: 2 }) }}
              </span>
            </template>
          </Column>
          <Column :header="t('contratti.col_origine')" style="width: 110px;">
            <template #body="{ data }">
              <Tag :value="t(`contratti.origine_${data.origine?.toLowerCase()}`)"
                :severity="origineSeverity(data.origine)" />
            </template>
          </Column>
        </template>
        <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
          <template #body="{ data }">
            <RowActionsMenu :row="data" :actions="buildRigaActions(data)" />
          </template>
        </Column>
        <!-- Sub-tabella componenti BoM: padre + figli annidati.
             `ComponentiPanel` in modalita' data-driven (prop `initialData`):
             salta la fetch, normalizza shape JSONB (`prezzo`/`coeff_qta`
             dalla fn DB) sullo shape persistito e auto-nasconde le colonne
             metadata (origine/approvazione/IVA) assenti nel preview.
             I figli arrivano gia' aggregati nel JSONB `componenti` da
             `fn_contratto_righe_preview` tanto per righe DA_LISTINO bundle
             (figli in `listini_righe_componenti`) quanto per AGGIUNTA-bundle
             persistite. Il coerce JSONB->Array e' interno al pannello. -->
        <template #expansion="{ data }">
          <div style="padding: 0.25rem 0 0.5rem 2rem; background: var(--app-table-stripe-bg);">
            <ComponentiPanel
              :initial-data="rowComponenti(data)"
              i18n-prefix="vendite.componenti.panel" />
          </div>
        </template>
      </DataTable>

      <!-- === DETAIL: form inserimento/modifica === -->
      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formTitle }}</h4>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('contratti.field_articolo') }} *</label>
            <!-- Refactor FE 2.2 Opzione C (2026-05-18): l'articolo e' libero
                 SOLO per "Aggiungi articolo" (AGGIUNTA fuori-listino). Per
                 "Modifica prezzo" (OVERRIDE) e in EDIT e' precompilato e
                 immutabile — il flusso ha gia' identificato l'articolo via
                 click sulla riga DA_LISTINO. -->
            <ArticoloLookup
              v-model="form.articolo_obj"
              @update:modelValue="onArticoloSelected"
              :disabled="formMode === 'edit' || form.tipo_eccezione !== 'AGGIUNTA'"
              :filtri="{ soloComponenti: 'escludi' }"
              :placeholder="t('contratti.select_articolo')"
            />
          </div>
          <div class="form-field">
            <!-- Refactor FE 2.2 Opzione C (2026-05-18): tipo_eccezione non
                 e' piu' una scelta utente. Deriva dall'azione che ha aperto
                 il form: toolbar->AGGIUNTA, kebab "Modifica prezzo"->OVERRIDE.
                 ESCLUSIONE non passa dal form (one-click via kebab+conferma).
                 Mostrato come Tag readonly sia CREATE che EDIT per
                 trasparenza UX. -->
            <label>{{ t('contratti.field_tipo_eccezione') }}</label>
            <div>
              <Tag :value="t(`contratti.tipo_eccezione_${form.tipo_eccezione}`)"
                severity="secondary" />
            </div>
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('contratti.field_uom') }} *</label>
            <Select v-model="form.uom_operativa_id"
              :options="uomOptions"
              option-value="uom_id"
              :option-label="uomLabel"
              :placeholder="form.articolo_id ? t('contratti.select_uom') : t('contratti.uom_select_articolo_first')"
              :disabled="!form.articolo_id || uomLoading"
              :loading="uomLoading"
              class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('contratti.field_tipo_erogazione') }}</label>
            <Select v-model="form.tipo_erogazione" :options="tipoErogazioneOptions"
              option-label="label" option-value="value" class="w-full" />
          </div>
        </div>

        <!-- Refactor 2026-05-19: Select fonte_quantita_attesa.
             Le 5 fonti sono filtrate per tipo_erogazione (CHECK DB
             chk_contrighe_coerenza_fonte_erogazione vieta le 7 combinazioni
             incoerenti — non appaiono nelle opzioni). Tooltip "uso atipico"
             sulle combinazioni rare (🟡 nella matrice). -->
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('contratti.field_fonte_quantita_attesa') }} *</label>
            <Select v-model="form.fonte_quantita_attesa"
              :options="fonteQuantitaOptions"
              option-label="label" option-value="value"
              :placeholder="t('contratti.select_fonte_quantita')"
              class="w-full" />
            <small v-if="fonteCorrente?.severity === 'warn'" class="contratti-fonte-uso-atipico">
              <i class="pi pi-info-circle" /> {{ t('contratti.fonte_quantita_uso_atipico') }}
            </small>
          </div>
          <div class="form-field">
            <label>
              {{ t('contratti.field_prezzo_unitario') }}
              <!-- Obbligatorio per OVERRIDE/AGGIUNTA (default tipo) non
                   composito. ESCLUSIONE = prezzo NULL. -->
              <span v-if="form.tipo_eccezione !== 'ESCLUSIONE' && !articoloObj?.is_composito">*</span>
              <Tag v-if="form.tipo_eccezione === 'ESCLUSIONE'"
                severity="warn"
                :value="t('contratti.prezzo_esclusione_n_a')" />
              <Tag v-else-if="articoloObj?.is_composito"
                severity="info"
                :value="t('vendite.componenti.panel.padre_calcolato')"
                v-tooltip.top="t('vendite.componenti.panel.padre_calcolato_tooltip')"
                class="contratti-componenti-padre-tag" />
            </label>
            <InputNumber v-model="form.prezzo_unitario" class="w-full"
              :disabled="articoloObj?.is_composito === true
                         || form.tipo_eccezione === 'ESCLUSIONE'"
              :min-fraction-digits="2" :max-fraction-digits="4" showButtons />
          </div>
        </div>

        <!-- Refactor 2026-05-19: Q.ta operativa visibile/obbligatoria solo
             per fonte FISSA. Per le altre 4 fonti il valore vero arriva
             downstream (manuale/timesheet/letture) o e' derivato dal
             trigger DB z90_propaga_qta_componenti (DERIVATA_COMPONENTI).
             Mostriamo un Tag readonly per chiarire all'utente da dove
             arrivera' il valore. -->
        <div class="form-grid-2col">
          <div class="form-field" v-if="showQtaOperativa">
            <label>{{ t('contratti.field_qta_operativa_fissa') }} *</label>
            <InputNumber v-model="form.qta_operativa" class="w-full"
              :min="0.0001" :min-fraction-digits="0" :max-fraction-digits="4" showButtons />
          </div>
          <div class="form-field" v-else-if="form.fonte_quantita_attesa">
            <label>{{ t('contratti.field_qta_operativa') }}</label>
            <Tag severity="info"
              :value="t(`contratti.fonte_quantita_tag_${form.fonte_quantita_attesa.toLowerCase()}`)"
              v-tooltip.top="t('contratti.fonte_quantita_tag_tooltip')" />
          </div>
          <div class="form-field">
            <label>{{ t('contratti.field_ordine') }}</label>
            <InputNumber v-model="form.ordine" class="w-full" :min="0" />
          </div>
        </div>

        <!-- Sezione componenti BoM (modello unificato 2026-05-13).
             CREATE: il payload Dialog viaggia col save riga
             (componenti_overrides). Mostra bottone "Modifica componenti"
             + summary live. EDIT: ComponentiPanel carica i componenti
             persistiti e li espone editabili. -->
        <template v-if="articoloObj?.is_composito">
          <ComponentiCreateActionsPanel
            v-if="formMode === 'create'"
            :disabled="!form.articolo_id || !form.uom_operativa_id
              || (showQtaOperativa && (form.qta_operativa || 0) <= 0)"
            :componenti-payload="componentiPayload"
            @apri-dialog="apriComponentiDialog"
          />
          <template v-else>
            <div class="app-drawer-section">
              <h4>{{ t('vendite.componenti.panel.section_title') }}</h4>
            </div>
            <ComponentiPanel
              :documento-id="props.contrattoId"
              :riga-id="rigaEditId"
              :readonly="isReadonly || formMode !== 'edit'"
              :api-list="listContrattoRigaComponenti"
              :api-update="updateContrattoRigaComponente"
              :api-delete="deleteContrattoRigaComponente"
              :tab-entity="TAB_ENTITIES.CONTRATTO"
              @changed="onComponentiPanelChanged" />
          </template>
        </template>

        <!-- Composizione bundle DA_LISTINO (read-only). Mostrata quando si
             apre il form OVERRIDE da una riga preview composita: i figli
             vivono nel listino, non in contratti_righe_componenti, quindi
             l'api-list del pannello sopra sarebbe vuota. Li esponiamo
             data-driven dai dati gia' caricati nella riga, come nelle offerte.
             Indipendente dal blocco `articoloObj?.is_composito` (che in
             onModificaPrezzo resta null per non auto-aprire la Dialog). -->
        <template v-if="selectedRowComponenti.length">
          <div class="app-drawer-section">
            <h4>{{ t('vendite.componenti.panel.section_title') }}</h4>
          </div>
          <ComponentiPanel
            :initial-data="selectedRowComponenti"
            readonly
            i18n-prefix="vendite.componenti.panel" />
        </template>

        <!-- Banner inline L2: visibile quando il save ha sollevato un codice
             E_PRICING_SCONTO_ECCESSIVO / E_PRICING_MAGGIORAZIONE_ECCESSIVA.
             Mostra il messaggio BE + CTA "Richiedi approvazione" che retry
             il save con `richiesta_approvazione=true` (workflow L3 cablato
             2026-05-19). Pattern identico a PreventiviRigaForm. -->
        <Message v-if="l2Error" severity="warn" :closable="false">
          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <strong>{{ l2Error.message }}</strong>
            <small v-if="l2Error.detail">{{ l2Error.detail }}</small>
            <div>
              <Button
                :label="loading
                  ? t('contratti.richiedi_approvazione_in_corso')
                  : t('contratti.richiedi_approvazione')"
                icon="pi pi-send"
                size="small"
                severity="secondary"
                :loading="loading"
                v-tooltip.bottom="t('contratti.richiedi_approvazione_tooltip')"
                @click="onRichiediApprovazione"
              />
            </div>
          </div>
        </Message>

        <div class="app-form-footer">
          <Button :label="t('common.cancel')" severity="secondary" @click="closeForm" />
          <Button :label="t('common.save')" :disabled="!canSave || loading" :loading="loading" @click="onSave" />
        </div>
      </template>

      <FormFooter v-if="!formMode" close-only @cancel="onClose" />
    </div>

    <!-- ComponentiDialog modale: pre-popola i prezzi dei componenti BoM
         prima del save di una riga padre composita. La conferma alimenta
         `componentiPayload`; il save include `componenti_overrides`. -->
    <ComponentiDialog
      v-model:visible="componentiDialogVisible"
      :articolo="articoloObj"
      :documento-id="props.contrattoId"
      :uom-operativa-id="form.uom_operativa_id"
      :quantita="form.qta_operativa"
      :api-preview="previewRigaComponenti"
      :initial-payload="componentiPayload"
      @confirm="onComponentiConfirm" />
  </Drawer>
</template>

<style scoped>
.contratti-componenti-padre-tag {
  font-size: 0.65rem;
  margin-left: 0.4rem;
  padding: 0.05rem 0.3rem;
}
.contratti-componenti-create {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.contratti-componenti-summary {
  color: var(--app-text-muted);
}
.contratti-fonte-uso-atipico {
  display: block;
  margin-top: 0.25rem;
  /* PrimeVue yellow-700 hex come fallback: ne' --app-text-warn ne'
     --p-yellow-700 sono definite nel tema custom; usiamo il pattern
     dei componenti core (var + fallback hex esplicito). */
  color: var(--p-yellow-700, #b45309);
  font-size: 0.8rem;
}

</style>
