<script setup>
// Scopo: Drawer crea/modifica ordine di vendita.
// CREATE: form testata con auto-save BOZZA al primo set di campi minimi
//   (cliente) → "edit-evolved" interno (createdId + hasDetail), poi righe inline.
// EDIT: testata + righe + componenti BoM + azioni stato (conferma, push commessa).
// Niente revisioni ne' listino in testata (a differenza di preventivi/offerte):
// state machine semplice DRAFT → CONFERMATO + push singolo a commessa.
import { ref, watch, computed, nextTick, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOrdiniStore } from '../stores/ordini'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useNotify } from '../../../core/composables/useNotify'
import { useInjectReadonly, READONLY_KEY } from '../../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../../core/composables/useDrawerDetailLoad'
import { useDrawerContentReady } from '../../../core/composables/useDrawerContentReady'
import { useEmittenteFiscaleField } from '../../../core/composables/useEmittenteFiscaleField'
import { useUtilityDefaultId } from '../../../core/composables/useUtilityDefaultId'
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { mapAvailableActionsToDrawerActions } from '../../../core/composables/useDrawerActions'
import { statoOrdineSeverity } from '../../../core/utils/severity'
import {
  STATO_ORDINE,
  STATI_ORDINE_EVADIBILI,
} from '../constants'
import EntityPdfButton from '../../../documenti/components/EntityPdfButton.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { displayDate, toDateString } from '../../../core/utils/date'
import { getOrdineFormDefaults } from '../../api/formDefaults'
import { createOrdine } from '../api/ordiniApi'
import { useDrawerAutosaveBozza } from '../../../core/composables/useDrawerAutosaveBozza'
import { getBillingAccountLookupById } from '../../../core/apiCore'
import { DRAWER_WIDTH, MANAGE_ICONS, TAB_ENTITIES } from '../../../core/constants'
import { NAV_ICONS } from '../../../core/navigation'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import FormFooter from '../../../core/components/FormFooter.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../../core/components/DrawerActionsBar.vue'
import RiepilogoIvaTable from '../../../core/components/RiepilogoIvaTable.vue'
import DocumentoIndirizziSection from '../../_shared/indirizzi/DocumentoIndirizziSection.vue'
import LineagePassaggiPanel from '../../_shared/lineage/LineagePassaggiPanel.vue'
import OrdiniForm from './OrdiniForm.vue'
import OrdiniRigheTable from './OrdiniRigheTable.vue'
import OrdineNoteDrawer from './OrdineNoteDrawer.vue'
import OrdineEvasionePanel from './OrdineEvasionePanel.vue'
import OrdineEmissioneDialog from './dialogs/OrdineEmissioneDialog.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'
import Message from 'primevue/message'

const { t, te } = useI18n()
const store = useOrdiniStore()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  ordineId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])
const onClose = useDrawerClose(emit, 'cancelled')
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)
const noteDrawerVisible = ref(false)
// Riepilogo IVA aggregato per aliquota (lettura da `vw_ordini_riepilogo_iva_dettaglio`).
// Auto-popolato a ogni loadDetail e ogni `@changed` delle righe: la vista DB
// e' la single source dei totali documento (regola fiscale DPR 633/72 art. 21).
const riepilogoIva = ref([])
// Pannello visibile quando c'e' almeno una riga aggregata. Il footer della
// RiepilogoIvaTable mostra gia' totale imponibile + imposta + totale documento.
const showRiepilogoIva = computed(
  () => Array.isArray(riepilogoIva.value) && riepilogoIva.value.length > 0,
)

// Auto-save bozza: in CREATE, appena il cliente (BA) e' valorizzato, il drawer
// crea l'ordine in BOZZA e si comporta da "edit-evolved" (righe + azioni stato).
const createdId = ref(null)
// Stato form riga inline: quando si edita/aggiunge una riga, il FormFooter
// testata si nasconde per non duplicare i bottoni di OrdiniRigaForm.
const formRigaAperto = ref(false)
const effectiveOrdineId = computed(() => createdId.value ?? props.ordineId)
const hasDetail = computed(() => detail.value !== null)

// Readonly cumulativo: prop esplicita OR readonly area iniettato dal parent OR
// stato post-DRAFT (modifiche libere solo in bozza). Il gate di stato e' su
// `hasDetail` (NON su `props.mode === 'edit'`): in CREATE "edit-evolved" (bozza
// auto-salvata) un'eventuale transizione che porti fuori DRAFT deve bloccare
// subito il form, anche se il drawer e' tecnicamente in mode='create'. Le
// azioni di stato (conferma/push) restano cliccabili in readonly grazie a
// `app-escape` applicato da DrawerActionsBar. Provide ai sub-componenti (righe).
const parentReadonly = useInjectReadonly()
const isReadonly = computed(
  () => props.readonly
    || parentReadonly.value
    || (detail.value !== null
        && detail.value.stato_codice_interno !== STATO_ORDINE.DRAFT),
)
provide(READONLY_KEY, isReadonly)

// Capability data-driven dal detail BE (script.fn_available_actions_ordine):
// availableActions + can_edit_testata + non_editable_fields. Composable
// centralizzato, uniforme a Preventivi/Contratti (Fase 4.F2).
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })
const availableActions = caps.availableActions
const canEditTestata = caps.canEdit
const canEditTestataEffective = computed(() => !isEdit.value || canEditTestata.value)
const canEditRighe = computed(() => caps.flag('can_edit_righe'))
// Push a commessa: l'azione arriva data-driven in `available_actions` solo
// quando e' eseguibile, quindi da sola sparisce senza spiegare perche'. La
// capability espone anche il motivo: banner informativo, mirror PreventiviDrawer.
const canPushCommessa = computed(() => caps.flag('can_push_commessa'))
const pushCommessaReasonKey = computed(() => detail.value?.can_push_commessa_reason_key || null)

// Campi bloccati lato UX. Una volta che l'ordine esiste (EDIT classico o CREATE
// post auto-save), il cliente NON e' piu' modificabile: il BE deriva
// `soggetto_ruolo_id` dal billing_account solo in create (crea_ordine), mentre
// aggiorna_ordine cambierebbe `billing_account_id` SENZA ri-derivare il
// soggetto_ruolo → incoerenza cliente↔soggetto. Difesa FE allineata a
// PreventiviDrawer (che blocca billing_account_id post-create). Cambiare cliente
// = nuovo ordine, non una modifica della testata.
const nonEditableFields = computed(() => (hasDetail.value ? ['billing_account_id'] : []))

// Readonly PURO (permesso LETTURA / split / readonly forzato) — SENZA il
// lock-di-stato post-DRAFT: l'evasione e' un'azione di processo legittima su un
// ordine CONFERMATO (stato post-DRAFT), come lo smistamento sui preventivi
// ACCETTATI. Serve al pannello evasione per restare interattivo sotto il
// lock-di-stato (app-escape), consuntivo solo in readonly puro.
const isReadonlyPuro = computed(() => props.readonly || parentReadonly.value)

// Pannello evasione (genera DDT) visibile quando l'ordine ha residuo da evadere
// (CONFERMATO o PARZIALMENTE_EVASO). Trigger fatturazione differita
// (SPEDITO/CONSEGNATO) resta lato DB; qui la vista e' data-driven sullo stato.
const showEvasione = computed(
  () => hasDetail.value
    && STATI_ORDINE_EVADIBILI.includes(detail.value?.stato_codice_interno),
)

// Scopo: callback @evaso del pannello — generato un DDT dall'ordine: ricarica il
// detail (lo stato ordine viene proiettato dal BE: CONFERMATO/PARZIALMENTE_EVASO/
// EVASO) e le capability. Il pannello ha gia' notificato il tab DDT.
async function onEvaso() {
  await loadDetail()
}

// Default emittente fiscale: operatore → id profilo; admin globale → null
// (sceglie via EmittenteFiscaleField in modalita' Select).
const { defaultEmittenteId } = useEmittenteFiscaleField()

// Default utility globale: il parametro DEFAULT_UTILITY stocca un codice_interno
// (framework FK-surrogata); il composable lo risolve all'id locale. Stesso
// pattern di PreventiviDrawer — proposto in CREATE all'apertura del drawer.
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

// Deferimento contenuto: i LookupSelect/AutoComplete montano dopo l'animazione
// di apertura (pattern feedback_content_ready_after_show).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

function defaultForm() {
  return {
    emittente_fiscale_id: defaultEmittenteId.value ?? null,
    // Utility default dal parameter DEFAULT_UTILITY (come preventivi/contratti).
    utility_id: utilityDefaultId.value ?? null,
    billing_account_id: null,
    // _obj per BillingAccountLookup (pattern restore lookup ricco,
    // memoria feedback_autocomplete_restore).
    billing_account_obj: null,
    valuta_id: null,
    modalita_pagamento_id: null,
    termine_pagamento_id: null,
    fatturazione_trigger: null,
    data: new Date(),
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
  createdId.value = null
  riepilogoIva.value = []
}

// Scopo: Carica il riepilogo IVA aggregato dell'ordine. Best-effort: in caso
//        di errore il pannello resta vuoto, i totali in testata restano
//        comunque visibili (il trigger DB li mantiene coerenti).
async function loadRiepilogoIva(targetId = null) {
  const id = targetId ?? effectiveOrdineId.value
  if (!id) return
  try {
    riepilogoIva.value = await store.loadRiepilogoIva(id)
  } catch {
    riepilogoIva.value = []
  }
}

async function loadDetail(id = null) {
  const targetId = id ?? effectiveOrdineId.value
  if (!targetId) return
  const data = await loadDetailOrClose(() => store.fetchDetail(targetId))
  if (!data) return
  detail.value = data
  form.value = {
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    utility_id: data.utility_id ?? null,
    billing_account_id: data.billing_account_id ?? null,
    billing_account_obj: null,  // popolato sotto via getBillingAccountLookupById
    valuta_id: data.valuta_id ?? null,
    modalita_pagamento_id: data.modalita_pagamento_id ?? null,
    termine_pagamento_id: data.termine_pagamento_id ?? null,
    fatturazione_trigger: data.fatturazione_trigger ?? null,
    data: data.data ? new Date(data.data + 'T00:00:00') : null,
  }
  await nextTick()
  // Restore BillingAccountLookup _obj per visualizzazione ricca. Best-effort.
  if (data.billing_account_id) {
    try {
      const res = await getBillingAccountLookupById(data.billing_account_id)
      const ba = res?.data?.data
      if (ba) form.value.billing_account_obj = ba
    } catch {
      // Resto: l'autocomplete parte vuoto, l'operatore puo' ri-selezionare.
    }
  }
  // Riepilogo IVA: il trigger DB mantiene i totali in sync con le righe a ogni
  // mutazione; qui leggiamo lo stato corrente (best-effort).
  await loadRiepilogoIva(targetId)
}

watch(() => props.visible, async (v) => {
  if (!v) return
  if (isEdit.value) {
    loadDetail()
  } else {
    // CREATE: risolve la utility di default (parameter DEFAULT_UTILITY) PRIMA di
    // resetForm, così defaultForm() la legge. Poi pre-popola la valuta dalla
    // catena EF (resolve_valuta_default lato BE), come preventivi/offerte.
    await loadUtilityDefault()
    resetForm()
    try {
      const res = await getOrdineFormDefaults(null)
      const data = res?.data?.data
      if (data && form.value.valuta_id == null && data.valuta_id != null) {
        form.value.valuta_id = data.valuta_id
      }
    } catch {
      // Best-effort: se l'API e' giu' il drawer si apre comunque (valuta vuota).
    }
  }
})

// Scopo: applica al form i default derivati dall'anagrafica del cliente (BA):
//        valuta (BA-wins, override), modalita/termine pagamento (solo se vuoti,
//        non si calpesta una scelta dell'operatore). Best-effort. Stessa catena
//        dei preventivi (vendite_form_defaults_service + get_cliente_defaults).
async function applyBaDefaults(baId) {
  if (!baId) return
  try {
    const res = await getOrdineFormDefaults(baId)
    const d = res?.data?.data
    if (!d) return
    const f = form.value
    if (d.valuta_id != null) f.valuta_id = d.valuta_id
    if (f.modalita_pagamento_id == null && d.modalita_pagamento_id != null) {
      f.modalita_pagamento_id = d.modalita_pagamento_id
    }
    if (f.termine_pagamento_id == null && d.termine_pagamento_id != null) {
      f.termine_pagamento_id = d.termine_pagamento_id
    }
  } catch {
    // Best-effort: se l'API e' giu' la bozza si crea senza i default cliente.
  }
}

// Auto-save bozza + abbandono bozza orfana via BB condiviso (B13, regola del 2).
// Trigger: cliente (BA) valorizzato in CREATE. Prima di creare applica i default
// da anagrafica cliente (valuta/modalita/termine). `close`/`onVisibleChange`
// usati dal template; createdId resta ref del drawer.
const { close, onVisibleChange } = useDrawerAutosaveBozza({
  emit,
  execute,
  loading,
  createdId,
  isEdit: () => isEdit.value,
  contentReady: () => contentReady.value,
  triggerSources: () => form.value.billing_account_id,
  isReady: (baId) => baId != null,
  createDraftApi: createOrdine,
  buildDraftPayload: async () => {
    await applyBaDefaults(form.value.billing_account_id)
    const f = form.value
    return {
      billing_account_id: f.billing_account_id || null,
      utility_id: f.utility_id || null,
      // Opzionale per BE: se omesso (operatore) il trigger DB lo deriva da GUC.
      emittente_fiscale_id: f.emittente_fiscale_id || null,
      valuta_id: f.valuta_id || null,
      modalita_pagamento_id: f.modalita_pagamento_id || null,
      termine_pagamento_id: f.termine_pagamento_id || null,
      fatturazione_trigger: f.fatturazione_trigger || null,
      data: f.data ? toDateString(f.data) : null,
    }
  },
  tabEntity: TAB_ENTITIES.ORDINE,
  fetchDetail: (id) => loadDetail(id),
  deleteDraft: (id) => store.elimina(id),
  righeCountGetter: () => detail.value?.righe_count ?? 0,
  messages: {
    bozzaCreata: t('vendite.ordini.bozza_creata'),
    abbandonoTitolo: t('vendite.ordini.abbandono_bozza_titolo'),
    abbandonoMessage: t('vendite.ordini.conferma_abbandono_bozza'),
    abbandonoConferma: t('vendite.ordini.abbandono_bozza_conferma'),
    bozzaEliminata: t('vendite.ordini.bozza_eliminata'),
  },
})

const canSave = computed(() => {
  if (isReadonly.value) return false
  return form.value.billing_account_id != null
})

async function handleSave() {
  const f = form.value
  if (isEdit.value || createdId.value !== null) {
    // UPDATE testata (DRAFT). emittente_fiscale_id NON e' aggiornabile (whitelist
    // BE _UPDATE_KEYS_ORDINE). Inviamo la whitelist: il BE normalizza empty→NULL.
    const payload = {
      billing_account_id: f.billing_account_id ?? null,
      utility_id: f.utility_id ?? null,
      valuta_id: f.valuta_id ?? null,
      modalita_pagamento_id: f.modalita_pagamento_id ?? null,
      termine_pagamento_id: f.termine_pagamento_id ?? null,
      fatturazione_trigger: f.fatturazione_trigger ?? null,
      data: f.data ? toDateString(f.data) : null,
    }
    const result = await execute(
      () => store.update(effectiveOrdineId.value, payload),
      { successMessage: t('vendite.ordini.ordine_salvato') }
    )
    if (result !== null) {
      await loadDetail()
      emit('saved', result)
    }
  } else {
    // Fallback CREATE manuale (auto-save non scattato): chiude dopo create.
    const payload = {
      billing_account_id: f.billing_account_id || null,
      utility_id: f.utility_id || null,
      emittente_fiscale_id: f.emittente_fiscale_id || null,
      valuta_id: f.valuta_id || null,
      modalita_pagamento_id: f.modalita_pagamento_id || null,
      termine_pagamento_id: f.termine_pagamento_id || null,
      fatturazione_trigger: f.fatturazione_trigger || null,
      data: f.data ? toDateString(f.data) : null,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('vendite.ordini.ordine_creato') }
    )
    if (result !== null) emit('saved', result)
  }
}

// --- Azioni stato ---

// Dialog emissione ordine: aperto quando l'azione di stato 'conferma' porta a
// CONFERMATO. Sostituisce il confirmAction generico perche' la conferma
// orchestra atomic state + genera documento + allegati lato BE (/emetti/,
// ApiOrdineEmetti, §6 brief-ordini-stampa.md). Mirror del flusso preventivo.
const emissioneDialogVisible = ref(false)
const emissioneLoading = ref(false)

function onConferma() {
  emissioneDialogVisible.value = true
}

// Scopo: callback @confirm di OrdineEmissioneDialog. Riceve i file staged
// dall'utente e chiama store.emetti (POST multipart /emetti/). Se la
// generazione fallisce il BE annulla la conferma (stato resta DRAFT).
async function handleEmissioneConferma({ files }) {
  emissioneLoading.value = true
  const result = await execute(
    () => store.emetti(effectiveOrdineId.value, { allegati: files || [] }),
    { successMessage: t('vendite.ordini.ordine_confermato') },
  )
  emissioneLoading.value = false
  if (result !== null) {
    emissioneDialogVisible.value = false
    await loadDetail()
    emit('saved', result)
  }
}

// Push singolo a commessa. Toast differenziato per `report.stato` (l'orchestrator
// risponde 200 anche con esito PARZIALE/ERRORE per riga — gemello preventivi).
function onPush() {
  confirmAction({
    message: t('vendite.ordini.push_commessa_messaggio'),
    onAccept: async () => {
      const result = await execute(() => store.push(effectiveOrdineId.value))
      if (result === null) return  // errore HTTP gia' gestito da useApiHandler

      const stato = result?.stato
      const pushLogId = result?.push_log_id
      const righe = result?.handlers?.reduce(
        (acc, h) => acc + (h?.created ?? 0) + (h?.updated ?? 0),
        0,
      ) ?? result?.righe_pushable ?? 0

      if (stato === 'COMPLETATO') {
        notify.success(t('vendite.ordini.push_commessa_ok', { righe, push_log_id: pushLogId }))
      } else if (stato === 'PARZIALE') {
        notify.warn(t('vendite.ordini.push_commessa_parziale', { righe, push_log_id: pushLogId }))
      } else if (stato === 'ERRORE') {
        const firstError = result?.handlers?.[0]?.errors?.[0] || t('common.generic_error')
        notify.error(t('vendite.ordini.push_commessa_errore', { primo_errore: firstError }))
      } else if (stato === 'SKIPPED') {
        notify.warn(t('vendite.ordini.push_commessa_skipped'))
      } else {
        notify.success(t('vendite.ordini.push_commessa_ok_generico'))
      }

      if (stato === 'COMPLETATO' || stato === 'PARZIALE') {
        await loadDetail()
        emit('saved', result)
      }
    },
  })
}

// Smista le azioni data-driven (`available_actions`) ai relativi handler.
// conferma/push hanno flussi dedicati (dialog/toast differenziati); le altre
// transizioni (es. annulla) passano dal cambio stato generico.
function onAction(action) {
  if (action.key === 'conferma') { onConferma(); return }
  if (action.key === 'push_commessa') { onPush(); return }
  if (action.requires_confirm) {
    confirmAction({
      message: t('vendite.ordini.conferma_cambio_stato', { stato: t(action.label_key) }),
      onAccept: () => eseguiCambioStato(action),
    })
  } else {
    eseguiCambioStato(action)
  }
}

// Transizione di stato generica (es. annulla DRAFT->ANNULLATO). Il trigger DB
// valida l'ammissibilita'; qui orchestriamo chiamata + refresh detail.
async function eseguiCambioStato(action) {
  const result = await execute(
    () => store.cambiaStato(effectiveOrdineId.value, action.target_state),
    { successMessage: t('vendite.ordini.stato_cambiato') },
  )
  if (result !== null) {
    await loadDetail()
    emit('saved', result)
  }
}

// Azioni del drawer ordine consumate da DrawerActionsBar. Le transizioni di
// stato arrivano data-driven da fn_available_actions_ordine (mapper condiviso
// con preventivi/contratti); in readonly puro (LETTURA/split) sono nascoste.
const drawerActions = computed(() => {
  if (!hasDetail.value) return []
  const readonlyPuro = isReadonlyPuro.value
  // `genera_ddt` (evasione) vive nel pannello OrdineEvasionePanel nel contenuto
  // del drawer (selezione righe + quantita'): un bottone header duplicherebbe il
  // percorso — filtrato a monte (come i preventivi con genera_ordine). Difensivo:
  // la fn ordini non espone ancora quest'azione, ma il filtro previene doppioni
  // quando arrivera' data-driven.
  const availableActionsHeader = (availableActions.value || [])
    .filter(a => a.key !== 'genera_ddt')
  const stateActions = mapAvailableActionsToDrawerActions({
    availableActions: availableActionsHeader,
    t,
    te,
    onAction,
    readonly: readonlyPuro,
  })
  return [
    ...stateActions,
    {
      key: 'manage-note',
      kind: 'manage',
      label: t('vendite.ordini.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => { noteDrawerVisible.value = true },
    },
  ]
})
</script>

<template>
  <Drawer :visible="visible" @update:visible="onVisibleChange"
    @after-show="onAfterShow"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE_PLUS }" :dismissable="true">
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('vendite.ordini.ordine')"
        :icon="NAV_ICONS.ORDINI"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- Header info: visibile in EDIT classico e in CREATE post auto-save. -->
      <template v-if="hasDetail">
        <DrawerEntityHeader>
          <Tag :value="detail.numero" severity="secondary" />
          <span v-if="detail.data" class="app-drawer-header-muted font-bold">
            {{ displayDate(detail.data) }}
          </span>
          <!-- Provenienza upstream (A1): chip read-only quando l'ordine nasce da
               un preventivo/offerta. Lo scheletro non valorizza queste colonne
               (le usera' la conversione upstream), ma il drawer le mostra. -->
          <Tag
            v-if="detail.documento_origine_tipo"
            :value="t('vendite.ordini.origine_chip', {
              tipo: detail.documento_origine_tipo,
              codice: detail.documento_origine_codice || detail.documento_origine_id,
            })"
            severity="info"
            icon="pi pi-link"
            v-tooltip.bottom="t('vendite.ordini.origine_chip_tooltip')"
          />

          <template #status>
            <Tag
              :value="detail.stato_descrizione"
              :severity="statoOrdineSeverity(detail.stato_codice_interno)"
            />
          </template>
        </DrawerEntityHeader>

        <DrawerActionsBar :actions="drawerActions">
          <template #suffix>
            <!-- Stampa conferma d'ordine: anteprima PDF on-demand
                 (ristampabile, §12.4(a)). BB EntityPdfButton riusato 1:1. -->
            <EntityPdfButton
              :sorgente-code="SORGENTE_CODES.ORDINE_VENDITA"
              :entity-id="effectiveOrdineId"
              :pdf="detail.pdf"
              i18n-prefix="vendite.ordini.pdf"
              :dialog-title="detail.numero
                ? t('vendite.ordini.pdf.dialog_title', { numero: detail.numero })
                : ''"
            />
          </template>
        </DrawerActionsBar>

        <!-- Motivo per cui "Invia a commessa" non e' offerto (gia' inviato,
             gia' fatturato, ordine non confermato, fatturazione da DDT):
             senza questo il pulsante sparisce e basta. -->
        <Message v-if="!canPushCommessa && pushCommessaReasonKey && te(pushCommessaReasonKey)"
          severity="info" :closable="false" class="mt-1">
          {{ t(pushCommessaReasonKey) }}
        </Message>
      </template>

      <Divider v-if="hasDetail" />

      <!-- Form testata: monta dopo l'animazione drawer per evitare rimbalzo lookup. -->
      <OrdiniForm v-if="contentReady"
        :form="form" :is-modificabile="canEditTestataEffective && !isReadonly"
        :non-editable-fields="nonEditableFields"
        :is-edit="isEdit || createdId !== null"
        :record="detail" />

      <!-- Righe: visibili appena c'e' detail (EDIT classico o CREATE post auto-save). -->
      <template v-if="contentReady && hasDetail">
        <!-- Sezione indirizzi (UX v2, BB condiviso): solo il default CON,
             contatore "+N altri", pulsante "Indirizzi" che apre il drawer
             di gestione. -->
        <DocumentoIndirizziSection
          dominio="ordini"
          :doc-id="effectiveOrdineId"
          :soggetto-ruolo-id="detail?.soggetto_ruolo_id ?? null"
          :istanza-utility-id="detail?.istanza_utility_id ?? null"
          :readonly="!(canEditTestataEffective && !isReadonly)" />

        <Divider />
        <OrdiniRigheTable
          :ordine-id="effectiveOrdineId"
          :is-modificabile="canEditRighe && !isReadonly"
          @changed="loadDetail()"
          @form-aperto="(v) => { formRigaAperto = v }" />

        <!-- Riepilogo IVA aggregato (regola fiscale DPR 633/72 art. 21).
             Visibile con almeno una riga. Il footer mostra gia' totale
             imponibile + imposta + totale documento. Componente riusabile
             cross-dominio condiviso con preventivi (regola del 2). -->
        <template v-if="showRiepilogoIva">
          <Divider />
          <RiepilogoIvaTable :items="riepilogoIva" :show-subtitle="true" />
        </template>
      </template>

      <!-- Pannello evasione "Genera DDT": visibile quando l'ordine ha residuo
           (CONFERMATO / PARZIALMENTE_EVASO). In stato post-DRAFT il contenuto e'
           `app-readonly` (lock-di-stato) ma l'evasione e' un'azione di processo
           legittima → `app-escape` la mantiene cliccabile. In readonly PURO
           (LETTURA/split/forzato) il pannello e' consuntivo (niente azioni). -->
      <template v-if="contentReady && showEvasione">
        <Divider />
        <div class="app-escape">
          <OrdineEvasionePanel
            :ordine-id="effectiveOrdineId"
            :readonly="isReadonlyPuro"
            @evaso="onEvaso" />
        </div>
      </template>

      <!-- Genealogia/lineage (pannello "Passaggi", BB condiviso lazy: fetch
           al primo expand; app-escape interno per la consultazione in
           readonly di stato). -->
      <template v-if="contentReady && hasDetail">
        <Divider />
        <LineagePassaggiPanel
          base-path="/vendite/ordini"
          :doc-id="effectiveOrdineId" />
      </template>

      <FormFooter v-if="canEditTestataEffective && !isReadonly && !formRigaAperto"
        :loading="loading" :disabled="!canSave"
        @save="handleSave" @cancel="close" />
      <FormFooter v-else-if="hasDetail && !formRigaAperto" close-only @cancel="close" />
    </div>
  </Drawer>

  <!-- Sub-drawer note: cablato sull'id effettivo dell'ordine. -->
  <OrdineNoteDrawer
    v-if="effectiveOrdineId"
    v-model:visible="noteDrawerVisible"
    :ordine-id="effectiveOrdineId"
  />

  <!-- Dialog emissione ordine (transizione DRAFT → CONFERMATO). Wrapper sul
       building block DocumentoEmissioneDialog: anteprima PDF + allegati,
       conferma orchestra atomic state + genera + allegati via /emetti/. -->
  <OrdineEmissioneDialog
    v-model:visible="emissioneDialogVisible"
    :ordine="detail"
    :loading="emissioneLoading"
    @confirm="handleEmissioneConferma"
  />
</template>
