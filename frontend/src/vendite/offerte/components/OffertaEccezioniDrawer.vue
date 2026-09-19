<script setup>
// Scopo: Sub-drawer eccezioni offerta commerciale (master-detail inline).
//        Lista paginata + form sotto. Editabile solo se offerta in BOZZA
//        (readonly propagato dal parent + lock locale su stato).
//
// Specchio strutturale di ContrattoRigheDrawer.vue ma versione semplificata:
// niente preview prezzi, niente integrazione BoM, niente componenti
// compositi. Le eccezioni offerta sono il mirror di contratti_righe ma
// in v1 si limitano a tipo + articolo + prezzo/quantita + fonte/erogazione.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Drawer from 'primevue/drawer'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import AttivoTag from '../../../core/components/AttivoTag.vue'
import ToggleSwitch from 'primevue/toggleswitch'

import ArticoloLookup from '../../../core/components/ArticoloLookup.vue'
import DrawerContextHeader from '../../../core/components/DrawerContextHeader.vue'
import FormFooter from '../../../core/components/FormFooter.vue'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ComponentiCreateActionsPanel from '../../_shared/componenti/ComponentiCreateActionsPanel.vue'
import ComponentiDialog from '../../_shared/componenti/ComponentiDialog.vue'
import { useComponentiDialog } from '../../_shared/componenti/useComponentiDialog'
import ComponentiPanel from '../../_shared/componenti/ComponentiPanel.vue'
import L2ErrorBanner from '../../_shared/pricing/L2ErrorBanner.vue'
import { useL2SaveFlow } from '../../_shared/pricing/useL2SaveFlow'
import { useLimitiPricing } from '../../composables/useLimitiPricing'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useArticoloUomOptions } from '../../../core/composables/useArticoloUomOptions'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../../core/composables/useDrawerContentReady'
import { useInjectReadonly } from '../../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS, TAB_ENTITIES } from '../../../core/constants'
import { displayDate } from '../../../core/utils/date'
import { rowComponenti, hasBundleComponenti } from '../../_shared/componenti/rowComponenti'
import { statoOffertaSeverity } from '../../../core/utils/severity'
import { FONTE_QUANTITA_ATTESA, TIPO_ECCEZIONE, TIPO_EROGAZIONE } from '../../constants'
import {
  previewEccezioneComponenti,
  listEccezioneComponenti,
  updateEccezioneComponente,
  deleteEccezioneComponente,
} from '../api/offerteApi'
import { useOfferteStore } from '../stores/offerte'

const { t } = useI18n()
const store = useOfferteStore()
const { execute, loading, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()
const parentReadonly = useInjectReadonly()
// Codici L2 centralizzati (mirror contratti): il banner inline + CTA
// "richiedi approvazione" sostituisce il toast standard sul gate prezzo.
const { L2_ERROR_CODES } = useLimitiPricing()
// Banner errore L2 (BB condiviso). `saving` e' il loading del flusso save/
// richiesta-approvazione (la lista/delete usano `loading` di useApiHandler).
const l2Error = ref(null)
const saving = ref(false)

const props = defineProps({
  visible: Boolean,
  offertaId: { type: Number, required: true },
  offertaCodice: { type: String, default: '' },
  offertaStatoCodice: { type: String, default: '' },
  offertaStatoDescrizione: { type: String, default: '' },
  offertaCliente: { type: String, default: '' },
  offertaValiditaDal: { type: String, default: null },
  offertaValiditaAl: { type: String, default: null },
  eccezioniIniziali: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:visible', 'changed'])

// Readonly cumulativo: permesso area + stato non-BOZZA. Niente logica locale
// di workflow nei sub-drawer (frontend-standards §"Drawer di entita' con
// sub-drawer — catena readonly"): qui combiniamo solo il parent readonly
// con la regola di stato locale.
const isReadonly = computed(
  () => parentReadonly.value || props.offertaStatoCodice !== 'BOZZA',
)

const eccezioni = ref([])
const formMode = ref(null) // null | 'create' | 'edit'
const editingId = ref(null)
const selectedRow = ref(null)
const form = ref({})
// Expansion DataTable righe eccezione: chiave = `id` (PK). Mostra
// `ComponentiPanel` data-driven con i figli aggregati dal BE
// (`row.componenti` jsonb). Pattern speculare a `ContrattoRigheDrawer`.
const expandedRows = ref({})

function isExpanded(row) {
  const key = row?.id
  if (key == null) return false
  return Object.prototype.hasOwnProperty.call(expandedRows.value, key)
}

function toggleExpansion(row) {
  const key = row?.id
  if (key == null) return
  const next = { ...expandedRows.value }
  if (Object.prototype.hasOwnProperty.call(next, key)) {
    delete next[key]
  } else {
    next[key] = true
  }
  expandedRows.value = next
}

const {
  uomOptions, uomLoading, loadUomPerArticolo, pickBaseUomId, resetUomOptions,
} = useArticoloUomOptions()

function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('vendite.listini.uom_base_suffix')}` : ''
  return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
}

// Scopo: carica le UoM dell'articolo e, in create, pre-seleziona la base.
async function caricaUomConPickBase(articoloId) {
  const list = await loadUomPerArticolo(articoloId)
  if (formMode.value === 'create' && !form.value.uom_operativa_id) {
    form.value.uom_operativa_id = pickBaseUomId(list)
  }
}

// === ComponentiDialog state (modello unificato BoM, simmetria contratti
// 2026-05-26). Pattern speculare a `ContrattoRigheDrawer`: in CREATE su
// articolo composito la Dialog si auto-apre al primo set di (articolo,
// uom) validi; in EDIT lo stato viaggia via `ComponentiPanel` sotto il
// form (lista persistita).
// Orchestrazione ComponentiDialog centralizzata nel BB `useComponentiDialog`
// (estrazione regola-del-2 2026-05-31). `qtaValida: () => true`: nelle eccezioni
// offerta la qta puo' essere null per fonti CONSUMO/LETTURE e i prezzi unitari
// componente non dipendono dalla qta, quindi l'auto-apertura non richiede qta>0
// (diverso da preventivi/contratti). isComposito/isPadreComposito leggono
// `form.articolo_obj.is_composito`.
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
  // ESCLUSIONE escluso: un articolo escluso non ha prezzo (il DB impone
  // prezzo_unitario NULL) ne' senso di negoziarne i componenti BoM. Niente
  // ComponentiDialog ne' invio `componenti_overrides` per le ESCLUSIONI.
  isComposito: () => form.value?.articolo_obj?.is_composito === true
    && form.value?.tipo_eccezione !== TIPO_ECCEZIONE.ESCLUSIONE,
  isPadreComposito: () => form.value?.articolo_obj?.is_composito === true
    && form.value?.tipo_eccezione !== TIPO_ECCEZIONE.ESCLUSIONE,
  qtaValida: () => true,
})

const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

// --- Enum options ---

const tipoEccezioneOptions = [
  { value: TIPO_ECCEZIONE.OVERRIDE, label: 'OVERRIDE' },
  { value: TIPO_ECCEZIONE.ESCLUSIONE, label: 'ESCLUSIONE' },
  { value: TIPO_ECCEZIONE.AGGIUNTA, label: 'AGGIUNTA' },
]

const tipoErogazioneOptions = [
  { value: TIPO_EROGAZIONE.CANONE, label: t('vendite.offerte.tipo_erogazione_canone') },
  { value: TIPO_EROGAZIONE.UNA_TANTUM, label: t('vendite.offerte.tipo_erogazione_una_tantum') },
  { value: TIPO_EROGAZIONE.CONSUMO, label: t('vendite.offerte.tipo_erogazione_consumo') },
]

// Matrice tipo_erogazione → fonti ammesse (specchio ridotto della logica
// di contratti_righe; il CHECK DB applica gli stessi vincoli su
// offerte_commerciali_eccezioni).
const _FONTI_PER_TIPO = {
  [TIPO_EROGAZIONE.CANONE]: [
    { value: FONTE_QUANTITA_ATTESA.FISSA, default: true },
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
  [TIPO_EROGAZIONE.UNA_TANTUM]: [
    { value: FONTE_QUANTITA_ATTESA.FISSA, default: true },
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
  [TIPO_EROGAZIONE.CONSUMO]: [
    { value: FONTE_QUANTITA_ATTESA.MANUALE },
    { value: FONTE_QUANTITA_ATTESA.LETTURE, default: true },
    { value: FONTE_QUANTITA_ATTESA.DERIVATA_COMPONENTI },
  ],
}

function _fontiPerTipo(tipo) {
  return _FONTI_PER_TIPO[tipo] || []
}

function _defaultFontePerTipo(tipo) {
  return _fontiPerTipo(tipo).find((f) => f.default)?.value ?? null
}

const fonteOptions = computed(() => _fontiPerTipo(form.value?.tipo_erogazione).map((f) => ({
  value: f.value,
  label: f.value,
})))

// --- CRUD ---

async function reload() {
  const list = await store.loadEccezioni(props.offertaId)
  eccezioni.value = list
  // Se siamo in EDIT su un'eccezione composita e ComponentiPanel ha
  // appena modificato un prezzo componente (`@changed="reload"`), il
  // trigger DB `_z90_ricalcola_padre` ha aggiornato `prezzo_unitario`
  // sull'eccezione padre. Risincronizza solo quel campo del form, così
  // il drawer mostra il nuovo SUM senza chiudere/riaprire l'EDIT e
  // senza perdere le altre modifiche pending dell'utente (qty, ordine,
  // ecc.).
  if (formMode.value === 'edit' && editingId.value != null) {
    const refreshed = list.find((r) => r.id === editingId.value)
    if (refreshed && refreshed.prezzo_unitario != null) {
      form.value.prezzo_unitario = Number(refreshed.prezzo_unitario)
    }
  }
  emit('changed')
}

watch(() => props.visible, async (val) => {
  if (!val) {
    formMode.value = null
    editingId.value = null
    selectedRow.value = null
    return
  }
  // All'apertura partiamo dalla snapshot ricevuta dal parent, poi ricarichiamo
  // per coerenza con eventuali modifiche concorrenti.
  eccezioni.value = [...(props.eccezioniIniziali || [])]
  await reload()
})

function newForm() {
  return {
    tipo_eccezione: TIPO_ECCEZIONE.OVERRIDE,
    articolo_id: null,
    articolo_obj: null,
    tipo_erogazione: TIPO_EROGAZIONE.CANONE,
    fonte_quantita_attesa: _defaultFontePerTipo(TIPO_EROGAZIONE.CANONE),
    prezzo_unitario: null,
    qta_operativa: null,
    uom_operativa_id: null,
    attivo: true,
    ordine: null,
  }
}

function fromRow(row) {
  return {
    tipo_eccezione: row.tipo_eccezione,
    articolo_id: row.articolo_id,
    articolo_obj: row.articolo_id
      ? {
          id: row.articolo_id,
          codice: row.articolo_codice || '',
          descrizione: row.articolo_descrizione || '',
          is_composito: row.is_composito === true,
        }
      : null,
    tipo_erogazione: row.tipo_erogazione || TIPO_EROGAZIONE.CANONE,
    fonte_quantita_attesa: row.fonte_quantita_attesa
      || _defaultFontePerTipo(row.tipo_erogazione || TIPO_EROGAZIONE.CANONE),
    prezzo_unitario: row.prezzo_unitario,
    qta_operativa: row.qta_operativa,
    uom_operativa_id: row.uom_operativa_id,
    attivo: row.attivo ?? true,
    ordine: row.ordine ?? null,
  }
}

function _resetComponentiState() {
  resetComponentiDialog()
}

function openCreate() {
  form.value = newForm()
  editingId.value = null
  formMode.value = 'create'
  selectedRow.value = null
  resetUomOptions()
  _resetComponentiState()
}

function onRowSelect(event) {
  if (isReadonly.value) return
  const row = event.data
  selectedRow.value = row
  editingId.value = row.id
  form.value = fromRow(row)
  formMode.value = 'edit'
  _resetComponentiState()
  if (row.articolo_id) {
    // In edit l'articolo e' immutabile (Tag readonly); carichiamo comunque le
    // UoM operative dell'articolo cosi' la Select mostra etichetta coerente
    // per il valore gia' valorizzato. Niente autopick (formMode='edit').
    loadUomPerArticolo(row.articolo_id)
  }
}

function closeForm() {
  formMode.value = null
  editingId.value = null
  selectedRow.value = null
  resetUomOptions()
  _resetComponentiState()
}

watch(() => form.value?.tipo_erogazione, (nuovoTipo) => {
  if (!nuovoTipo || !form.value) return
  const fontiValide = _fontiPerTipo(nuovoTipo).map((f) => f.value)
  if (!fontiValide.includes(form.value.fonte_quantita_attesa)) {
    form.value.fonte_quantita_attesa = _defaultFontePerTipo(nuovoTipo)
  }
})

// Reset banner L2 se l'utente modifica prezzo o articolo: segnale di retry
// con contesto potenzialmente diverso. Pattern identico a ContrattoRigheDrawer.
watch(
  () => [form.value?.prezzo_unitario, form.value?.articolo_id],
  () => { if (l2Error.value) l2Error.value = null },
)

function onArticoloSelected(item) {
  if (!item) {
    form.value.articolo_id = null
    form.value.articolo_obj = null
    form.value.uom_operativa_id = null
    resetUomOptions()
    return
  }
  form.value.articolo_id = item.id
  form.value.articolo_obj = item
  // Cambio articolo: invalida la UoM precedente, carica le UoM operative
  // dell'articolo e (in create) preseleziona la base.
  form.value.uom_operativa_id = null
  // Articolo composito: la ComponentiDialog richiede `quantita > 0` per
  // caricare la preview BoM. Sull'eccezione la qta puo' essere null
  // (fonti CONSUMO/LETTURE): qui poniamo un default `1` per garantire
  // l'apertura della dialog. L'operatore puo' modificarla o azzerarla
  // successivamente in base alla fonte scelta.
  if (item.is_composito === true && !form.value.qta_operativa) {
    form.value.qta_operativa = 1
  }
  caricaUomConPickBase(item.id)
}

const canSave = computed(() => {
  if (isReadonly.value) return false
  const f = form.value
  if (!f) return false
  if (!f.tipo_eccezione) return false
  if (!f.articolo_id) return false
  if (!f.fonte_quantita_attesa) return false
  // Blocco CREATE su articolo composito finche' la ComponentiDialog non
  // ha confermato i prezzi componenti (mirror contratti). In EDIT i
  // componenti viaggiano via ComponentiPanel.
  if (showComponentiDialog.value && componentiPayload.value == null) return false
  return true
})

function buildPayload() {
  const f = form.value
  // Coerenza prezzo_unitario / tipo_eccezione (simmetrico a
  // ContrattoRigheDrawer.buildPayload 2026-05-29 + bugfix 2026-05-29 bis):
  //   - ESCLUSIONE: il prezzo NON ha semantica (DB
  //     `chk_offerte_eccezioni_prezzo_per_tipo_eccezione` impone NULL).
  //     Forza null lato client.
  //   - OVERRIDE / AGGIUNTA (anche su articolo composito): inviare il
  //     valore del form. Per i compositi il form è valorizzato da
  //     `onComponentiConfirm` con `summary.total / qtaPadre` (anteprima
  //     del SUM); al save BE il trigger `_z90_ricalcola_padre` allinea
  //     comunque al SUM canonico. Lo stesso check DB richiede
  //     prezzo_unitario NOT NULL per OVERRIDE/AGGIUNTA quindi NON
  //     possiamo skipparlo (era il bug del fix precedente).
  let prezzoUnitarioPayload = null
  if (f.tipo_eccezione !== TIPO_ECCEZIONE.ESCLUSIONE
      && f.prezzo_unitario != null
      && f.prezzo_unitario !== '') {
    prezzoUnitarioPayload = String(f.prezzo_unitario)
  }
  const payload = {
    tipo_erogazione: f.tipo_erogazione || null,
    fonte_quantita_attesa: f.fonte_quantita_attesa,
    prezzo_unitario: prezzoUnitarioPayload,
    qta_operativa: f.qta_operativa != null && f.qta_operativa !== ''
      ? String(f.qta_operativa) : null,
    uom_operativa_id: f.uom_operativa_id || null,
    attivo: f.attivo,
    ordine: f.ordine,
  }
  return payload
}

// Costruisce il payload completo per create/edit. `extra` permette di
// iniettare il flag opt-in `richiesta_approvazione: true` per il retry L3.
function buildFullPayload(extra = {}) {
  if (formMode.value === 'create') {
    const payload = {
      tipo_eccezione: form.value.tipo_eccezione,
      articolo_id: form.value.articolo_id,
      ...buildPayload(),
      ...extra,
    }
    // Modello unificato BoM: in CREATE su articolo composito include i
    // `componenti_overrides` (delta prezzi vs suggeriti) confermati dalla
    // ComponentiDialog. La fn DB init applica gli override; gli altri
    // componenti vengono valorizzati dal resolver bundle-aware.
    if (showComponentiDialog.value && componentiPayload.value?.overrides) {
      payload.componenti_overrides = componentiPayload.value.overrides
    }
    return payload
  }
  return { ...buildPayload(), ...extra }
}

// Esegue la persistenza (create o update). Store action gia'-unwrappata →
// chiamata diretta (no useApiHandler.execute) per poter intercettare il
// codice errore L2 nel catch del chiamante ([[feedback_useapihandler_solo_axios]]).
function persistEccezione(payload) {
  return formMode.value === 'create'
    ? store.addEccezione(props.offertaId, payload)
    : store.aggiornaEccezione(props.offertaId, editingId.value, payload)
}

// Save + richiedi-approvazione con gate L2 via BB condiviso (B12, regola del 2).
// Side-effect di successo: reload lista eccezioni + close. Mirror contratti.
const { save: handleSave, richiediApprovazione: onRichiediApprovazione } = useL2SaveFlow({
  persist: persistEccezione,
  buildPayload: buildFullPayload,
  onSuccess: async () => {
    await reload()
    closeForm()
  },
  messages: {
    success: () => (formMode.value === 'create'
      ? t('vendite.offerte.eccezione_creata')
      : t('vendite.offerte.eccezione_aggiornata')),
    approvalRequested: t('vendite.offerte.richiesta_approvazione_inviata'),
    error: t('vendite.offerte.errore_generico'),
  },
  l2Error,
  loading: saving,
  l2ErrorCodes: L2_ERROR_CODES,
})

function onDeleteRow(row, event) {
  event?.stopPropagation?.()
  if (isReadonly.value) return
  confirmAction({
    header: t('vendite.offerte.eccezione_elimina_titolo'),
    message: t('vendite.offerte.eccezione_elimina_messaggio'),
    danger: true,
    onAccept: async () => {
      const result = await execute(
        () => store.eliminaEccezione(props.offertaId, row.id),
        { successMessage: t('vendite.offerte.eccezione_eliminata') },
      )
      if (result !== null) {
        if (editingId.value === row.id) closeForm()
        await reload()
      }
    },
  })
}

const pageActions = computed(() => [
  {
    // Label standard "Nuovo" (`common.new`), allineata a tutte le toolbar
    // del progetto (PageActionsBar). Il contesto eccezione e' gia' chiaro
    // dal drawer; usare "Nuova eccezione" rompe lo standard cross-dominio.
    key: 'nuova',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('vendite.offerte.eccezione_nuova'),
    icon: MANAGE_ICONS.ADD,
    disabled: isReadonly.value || formMode.value === 'create',
    hideWhenReadonly: true,
    command: openCreate,
  },
])

const onClose = useDrawerClose(emit)
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE_PLUS }"
    :dismissable="true"
    @update:visible="(val) => emit('update:visible', val)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :title="t('vendite.offerte.eccezioni_titolo')"
        :icon="MANAGE_ICONS.RIGHE"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">

        <!-- Intestazione contesto offerta (BB DrawerContextHeader): allinea
             al pattern uniformato 2026-05-29 con ContrattoRigheDrawer
             (drawer di figli/eccezioni con contesto padre). -->
        <DrawerContextHeader
          :tag-value="props.offertaCodice"
          :items="[
            { label: t('vendite.offerte.col_cliente'), value: props.offertaCliente },
            { label: t('vendite.offerte.col_validita_dal'), value: props.offertaValiditaDal ? displayDate(props.offertaValiditaDal) : null },
            { label: t('vendite.offerte.col_validita_al'), value: props.offertaValiditaAl ? displayDate(props.offertaValiditaAl) : null, fallback: '∞' },
          ]">
          <template #status>
            <Tag
              :value="props.offertaStatoDescrizione"
              :severity="statoOffertaSeverity(props.offertaStatoCodice)"
            />
          </template>
        </DrawerContextHeader>

        <div class="app-page-toolbar">
          <div class="app-page-filters" />
          <PageActionsBar :actions="pageActions" />
        </div>

        <!-- DataTable in-memory (lista eccezioni gia' caricata via reload()).
             Pattern allineato a `ContrattoRigheDrawer` per le tabelle inner:
             niente `scrollable` / `scroll-height="flex"` (servono solo lazy);
             colonne `sortable` + `sort-field` su una colonna esistente,
             altrimenti PrimeVue Aura genera artefatti grafici nell'header
             (doppia underline sotto le label) quando paginator-position=top
             si combina con un thead senza alcun sort-state attivo. -->
        <DataTable
          :value="eccezioni"
          :loading="loading"
          paginator
          :rows="10"
          :rows-per-page-options="[10, 25]"
          paginator-position="top"
          striped-rows
          removable-sort
          sort-field="tipo_eccezione"
          :sort-order="1"
          class="app-datatable app-datatable--inner"
          selection-mode="single"
          v-model:selection="selectedRow"
          v-model:expanded-rows="expandedRows"
          data-key="id"
          @row-select="onRowSelect"
        >
          <!-- Expander custom per articoli compositi: chevron solo dove la
               riga e' padre composito con figli persistiti. Click.stop evita
               che il click apra anche il form di edit. -->
          <Column style="width: 2.5rem;" :exportable="false">
            <template #body="{ data }">
              <Button v-if="hasBundleComponenti(data)"
                :icon="isExpanded(data) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"
                text rounded size="small"
                @click.stop="toggleExpansion(data)" />
            </template>
          </Column>
          <Column
            field="tipo_eccezione"
            :header="t('vendite.offerte.col_tipo_eccezione')"
            sortable
            style="width: 130px;"
          >
            <template #body="{ data }">
              <Tag :value="data.tipo_eccezione" severity="info" />
            </template>
          </Column>
          <Column
            field="articolo_codice"
            :header="t('vendite.offerte.col_articolo')"
            sortable
            style="min-width: 180px;"
          >
            <template #body="{ data }">{{
              data.articolo_codice
                ? `${data.articolo_codice}${data.articolo_descrizione ? ' — ' + data.articolo_descrizione : ''}`
                : data.articolo_id
            }}</template>
          </Column>
          <Column
            field="tipo_erogazione"
            :header="t('vendite.offerte.col_tipo_erogazione')"
            sortable
            style="width: 130px;"
          />
          <Column
            field="prezzo_unitario"
            :header="t('vendite.offerte.col_prezzo_unitario')"
            sortable
            style="width: 120px;"
          />
          <Column
            field="qta_operativa"
            :header="t('vendite.offerte.col_quantita')"
            sortable
            style="width: 100px;"
          />
          <Column
            field="attivo"
            :header="t('vendite.offerte.col_attivo')"
            sortable
            style="width: 90px;"
          >
            <template #body="{ data }">
              <AttivoTag :active="data.attivo" />
            </template>
          </Column>
          <Column
            :header="t('common.col_azioni')"
            class="app-col-actions"
            :exportable="false"
            style="width: 70px;"
          >
            <template #body="{ data }">
              <Button
                :icon="MANAGE_ICONS.DELETE"
                text
                rounded
                size="small"
                class="app-delete-btn"
                :disabled="isReadonly"
                @click="(event) => onDeleteRow(data, event)"
              />
            </template>
          </Column>
          <!-- Expansion BoM: ComponentiPanel data-driven con i figli
               aggregati dal BE (`data.componenti` jsonb). Pattern speculare
               a `ContrattoRigheDrawer`. -->
          <template #expansion="{ data }">
            <div style="padding: 0.25rem 0 0.5rem 2rem; background: var(--app-table-stripe-bg);">
              <ComponentiPanel
                :initial-data="rowComponenti(data)"
                i18n-prefix="vendite.componenti.panel"
              />
            </div>
          </template>
        </DataTable>

        <!-- Form dettaglio (create/edit). -->
        <template v-if="formMode">
          <div class="app-drawer-section">
            <h4>
              {{ formMode === 'create'
                ? t('vendite.offerte.eccezione_nuova')
                : t('vendite.offerte.eccezione_modifica') }}
            </h4>
          </div>

          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_tipo_eccezione') }} *</label>
              <Select
                v-model="form.tipo_eccezione"
                :options="tipoEccezioneOptions"
                option-label="label"
                option-value="value"
                :disabled="formMode === 'edit'"
                :invalid="campiErrati.includes('tipo_eccezione')"
              />
            </div>
            <div class="form-field">
              <label>
                {{ t('vendite.offerte.field_articolo') }}
                <span v-if="formMode === 'create'">*</span>
              </label>
              <ArticoloLookup
                :model-value="form.articolo_obj"
                :disabled="formMode === 'edit'"
                @update:model-value="onArticoloSelected"
              />
            </div>
          </div>

          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_tipo_erogazione') }}</label>
              <Select
                v-model="form.tipo_erogazione"
                :options="tipoErogazioneOptions"
                option-label="label"
                option-value="value"
                show-clear
              />
            </div>
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_fonte_quantita') }} *</label>
              <Select
                v-model="form.fonte_quantita_attesa"
                :options="fonteOptions"
                option-label="label"
                option-value="value"
              />
            </div>
          </div>

          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_prezzo_unitario') }}</label>
              <InputNumber
                v-model="form.prezzo_unitario"
                :disabled="form.articolo_obj?.is_composito === true
                           || form.tipo_eccezione === TIPO_ECCEZIONE.ESCLUSIONE"
                :min-fraction-digits="0"
                :max-fraction-digits="6"
              />
            </div>
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_quantita') }}</label>
              <InputNumber
                v-model="form.qta_operativa"
                :min-fraction-digits="0"
                :max-fraction-digits="6"
              />
            </div>
          </div>

          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_uom_operativa') }}</label>
              <Select
                v-model="form.uom_operativa_id"
                :options="uomOptions"
                :option-label="uomLabel"
                option-value="uom_id"
                :loading="uomLoading"
                :disabled="!form.articolo_id || uomLoading"
                :placeholder="form.articolo_id
                  ? t('vendite.offerte.field_uom_operativa')
                  : t('vendite.promo_articoli.field_uom_articolo_first')"
              />
            </div>
            <div class="form-field">
              <label>{{ t('vendite.offerte.field_ordine') }}</label>
              <InputNumber v-model="form.ordine" :min="0"
                :invalid="campiErrati.includes('ordine')"
              />
            </div>
          </div>

          <div class="form-field">
            <label style="display: inline-flex; gap: 0.5rem; align-items: center;">
              <ToggleSwitch v-model="form.attivo"
                :invalid="campiErrati.includes('attivo')"
              />
              {{ t('vendite.offerte.field_attivo') }}
            </label>
          </div>

          <!-- Sezione componenti BoM (modello unificato, simmetria preventivi).
               CREATE: la ComponentiDialog si auto-apre al primo set valido
               (articolo composito + uom + qta) tramite watcher; il payload
               confermato viaggia col save eccezione (`componenti_overrides`).
               Niente bottone manuale: l'apertura e' automatica, l'eventuale
               revisione passa dall'expansion della lista eccezioni post-save.
               EDIT: ComponentiPanel carica i componenti persistiti e li
               espone editabili (PATCH per componente). -->
          <template v-if="form.articolo_obj?.is_composito && formMode === 'edit'">
            <div class="app-drawer-section">
              <h4>{{ t('vendite.componenti.panel.section_title') }}</h4>
            </div>
            <ComponentiPanel
              :documento-id="props.offertaId"
              :riga-id="editingId"
              :readonly="isReadonly"
              :api-list="listEccezioneComponenti"
              :api-update="updateEccezioneComponente"
              :api-delete="deleteEccezioneComponente"
              :tab-entity="TAB_ENTITIES.OFFERTA_COMMERCIALE"
              i18n-prefix="vendite.componenti.panel"
              @changed="reload"
            />
          </template>

          <!-- CREATE su composito: bottone "Modifica componenti" per
               correggere gli override del Dialog prima del save eccezione.
               Pattern allineato a contratti/preventivi via BB
               `ComponentiCreateActionsPanel`. Niente check qta nel
               `disabled`: l'auto-open scatta per CONSUMO/LETTURE senza
               qta, quindi il bottone "riapri" deve restare cliccabile. -->
          <ComponentiCreateActionsPanel
            v-if="form.articolo_obj?.is_composito && formMode === 'create'"
            :disabled="!form.articolo_id || !form.uom_operativa_id"
            :componenti-payload="componentiPayload"
            @apri-dialog="apriComponentiDialog"
          />

          <!-- Banner inline L2 (BB condiviso): violazione soglia prezzo →
               CTA "Richiedi approvazione" che retry-a il save con
               `richiesta_approvazione=true` (workflow L3). Mirror contratti. -->
          <L2ErrorBanner
            :error="l2Error"
            :loading="saving"
            :label="t('vendite.offerte.richiedi_approvazione')"
            :label-loading="t('vendite.offerte.richiedi_approvazione_in_corso')"
            :tooltip="t('vendite.offerte.richiedi_approvazione_tooltip')"
            @richiedi="onRichiediApprovazione"
          />

          <FormFooter
            :loading="saving"
            :disabled="!canSave"
            @save="handleSave"
            @cancel="closeForm"
          />
        </template>

        <FormFooter v-else close-only @cancel="onClose" />
      </template>
    </div>

    <!-- ComponentiDialog modale: pre-popola i prezzi BoM PRIMA del save
         di una eccezione padre composita. La conferma alimenta
         `componentiPayload`; il save include `componenti_overrides`. -->
    <ComponentiDialog
      v-model:visible="componentiDialogVisible"
      :articolo="form.articolo_obj"
      :documento-id="props.offertaId"
      :uom-operativa-id="form.uom_operativa_id"
      :quantita="form.qta_operativa"
      :api-preview="previewEccezioneComponenti"
      :initial-payload="componentiPayload"
      @confirm="onComponentiConfirm"
    />
  </Drawer>
</template>
