<script setup>
// Scopo: Drawer crea/modifica DDT di vendita.
// CREATE: form testata (cliente) con auto-save BOZZA al primo set di campi
//   minimi (cliente) → "edit-evolved" interno (createdId + hasDetail), poi righe
//   inline + campi trasporto.
// EDIT: testata trasporto + righe + componenti BoM + azioni stato (emetti,
//   spedisci, consegna, reso, annulla, push commessa).
// Macchina a stati DRAFT → EMESSO → SPEDITO → CONSEGNATO (→ RESO) + ANNULLATO,
// data-driven (available_actions dal BE). Numero assegnato a EMESSO dal trigger.
// Clone adattato di OrdiniDrawer (§D-4) + riepilogo IVA, PDF (EntityPdfButton)
// e sezione indirizzi (BB condiviso _shared/indirizzi, UX v2).
import { ref, watch, computed, nextTick, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDdtStore } from '../stores/ddt'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useNotify } from '../../../core/composables/useNotify'
import { useInjectReadonly, READONLY_KEY } from '../../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../../core/composables/useDrawerDetailLoad'
import { useDrawerContentReady } from '../../../core/composables/useDrawerContentReady'
import { useEmittenteFiscaleField } from '../../../core/composables/useEmittenteFiscaleField'
import { useUtilityDefaultId } from '../../../core/composables/useUtilityDefaultId'
import { useBaFormDefaults } from '../../_shared/baDefaults/useBaFormDefaults'
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { mapAvailableActionsToDrawerActions } from '../../../core/composables/useDrawerActions'
import { statoDdtSeverity } from '../../../core/utils/severity'
import { STATO_DDT } from '../constants'
import EntityPdfButton from '../../../documenti/components/EntityPdfButton.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { displayDate, toDateString } from '../../../core/utils/date'
import { createDdt } from '../api/ddtApi'
import { getDdtFormDefaults } from '../../api/formDefaults'
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
import DdtForm from './DdtForm.vue'
import DdtRigheTable from './DdtRigheTable.vue'
import DdtNoteDrawer from './DdtNoteDrawer.vue'
import DdtResoPanel from './DdtResoPanel.vue'
import DdtEmissioneDialog from './dialogs/DdtEmissioneDialog.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'

const { t, te } = useI18n()
const store = useDdtStore()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  ddtId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])
const onClose = useDrawerClose(emit, 'cancelled')
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)

// Riepilogo IVA aggregato per aliquota (lettura da `vw_ddt_riepilogo_iva_dettaglio`).
// Auto-popolato a ogni loadDetail e ogni `@changed` delle righe: la vista DB
// e' la single source (regola fiscale DPR 633/72 art. 21). Le righe con prezzo
// NULL (DDT solo di trasporto) sono escluse in vista: riepilogo vuoto -> nascosto.
const riepilogoIva = ref([])
// Pannello visibile quando c'e' almeno una riga aggregata. Il footer della
// RiepilogoIvaTable mostra gia' totale imponibile + imposta + totale documento.
const showRiepilogoIva = computed(
  () => Array.isArray(riepilogoIva.value) && riepilogoIva.value.length > 0,
)
const noteDrawerVisible = ref(false)
// Avviso emissione: true quando manca l'indirizzo obbligatorio (CON) —
// alimentato dalla sezione indirizzi, mostrato nel dialog di emissione.
const indirizzoObbligatorioMancante = ref(false)

// Auto-save bozza: in CREATE, appena il cliente (BA) e' valorizzato, il drawer
// crea il DDT in BOZZA e si comporta da "edit-evolved" (righe + azioni stato).
const createdId = ref(null)
// Stato form riga inline: quando si edita/aggiunge una riga, il FormFooter
// testata si nasconde per non duplicare i bottoni di DdtRigaForm.
const formRigaAperto = ref(false)
const effectiveDdtId = computed(() => createdId.value ?? props.ddtId)
const hasDetail = computed(() => detail.value !== null)

// Readonly cumulativo: prop esplicita OR readonly area iniettato dal parent OR
// stato post-DRAFT (modifiche libere solo in bozza). Gate di stato su
// `hasDetail` (NON su mode==='edit'): in CREATE "edit-evolved" un'eventuale
// transizione fuori DRAFT deve bloccare subito il form. Le azioni di stato
// restano cliccabili in readonly grazie a `app-escape` di DrawerActionsBar.
const parentReadonly = useInjectReadonly()
const isReadonly = computed(
  () => props.readonly
    || parentReadonly.value
    || (detail.value !== null
        && detail.value.stato_codice_interno !== STATO_DDT.DRAFT),
)
provide(READONLY_KEY, isReadonly)

// Pannello "Crea reso": solo su DDT CONSEGNATO (l'azione manuale «Reso» e'
// stata rimossa dalla matrice — il flip a RESO e' automatico alla conferma di
// un reso totale; questo pannello e' il percorso per aprire il reso).
const showResoPanel = computed(
  () => detail.value?.stato_codice_interno === STATO_DDT.CONSEGNATO,
)

// Capability data-driven dal detail BE (script.fn_available_actions_ddt):
// availableActions + can_edit_testata + non_editable_fields. Composable
// centralizzato, uniforme a Ordini/Preventivi/Contratti.
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })
const availableActions = caps.availableActions
const canEditTestata = caps.canEdit
const canEditTestataEffective = computed(() => !isEdit.value || canEditTestata.value)
const canEditRighe = computed(() => caps.flag('can_edit_righe'))

// Campi bloccati lato UX. Una volta che il DDT esiste, il cliente NON e' piu'
// modificabile: il BE deriva il destinatario_soggetto_ruolo dal billing_account
// solo in create; un cambio BA lascerebbe il destinatario stantio → incoerenza
// (E_DDT_CLIENTE_IMMUTABILE lato service). Cambiare cliente = nuovo DDT.
const nonEditableFields = computed(() => (hasDetail.value ? ['billing_account_id'] : []))

// Default emittente fiscale: operatore → id profilo; admin globale → null
// (sceglie via EmittenteFiscaleField in modalita' Select). Uniformato a
// ordini/preventivi (decisione Tid 2026-07-13): l'emittente e' legato allo
// USER; il fallback dal BA in trgfn_ddt_normalize resta rete di sicurezza.
const { defaultEmittenteId } = useEmittenteFiscaleField()

// Default utility globale (parameter DEFAULT_UTILITY): proposto in CREATE.
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

// Deferimento contenuto: i LookupSelect/AutoComplete montano dopo l'animazione
// di apertura (pattern feedback_content_ready_after_show).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

function defaultForm() {
  return {
    emittente_fiscale_id: defaultEmittenteId.value ?? null,
    utility_id: utilityDefaultId.value ?? null,
    billing_account_id: null,
    // _obj per BillingAccountLookup (pattern restore lookup ricco).
    billing_account_obj: null,
    valuta_id: null,
    data: new Date(),
    // Trasporto
    causale_trasporto_id: null,
    aspetto_bene_id: null,
    modalita_addebito_trasporto_id: null,
    vettore_soggetto_ruolo_id: null,
    vettore_obj: null,
    mittente_soggetto_ruolo_id: null,
    mittente_obj: null,
    num_colli: null,
    peso_lordo: null,
    peso_netto: null,
    volume: null,
    targa: null,
    autista: null,
    tracking_code: null,
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
  createdId.value = null
}

async function loadDetail(id = null) {
  const targetId = id ?? effectiveDdtId.value
  if (!targetId) return
  const data = await loadDetailOrClose(() => store.fetchDetail(targetId))
  if (!data) return
  detail.value = data
  form.value = {
    // Emittente fiscale memorizzato (denormalizzato dal detail BE: ragione
    // sociale soggetto + codice via EmittenteFiscaleField :record).
    // Immutabile post-create (whitelist BE update lo esclude).
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    utility_id: data.utility_id ?? null,
    billing_account_id: data.billing_account_id ?? null,
    billing_account_obj: null,  // popolato sotto via getBillingAccountLookupById
    valuta_id: data.valuta_id ?? null,
    data: data.data ? new Date(data.data + 'T00:00:00') : null,
    // Trasporto
    causale_trasporto_id: data.causale_trasporto_id ?? null,
    aspetto_bene_id: data.aspetto_bene_id ?? null,
    modalita_addebito_trasporto_id: data.modalita_addebito_trasporto_id ?? null,
    // Restore ricco mittente/vettore dalle denominazioni denormalizzate della
    // vista (SoggettoRuoloLookup mostra ragione_sociale_completa senza round-trip).
    vettore_soggetto_ruolo_id: data.vettore_soggetto_ruolo_id ?? null,
    vettore_obj: data.vettore_soggetto_ruolo_id
      ? { soggetto_ruolo_id: data.vettore_soggetto_ruolo_id, ragione_sociale_completa: data.vettore_denominazione }
      : null,
    mittente_soggetto_ruolo_id: data.mittente_soggetto_ruolo_id ?? null,
    mittente_obj: data.mittente_soggetto_ruolo_id
      ? { soggetto_ruolo_id: data.mittente_soggetto_ruolo_id, ragione_sociale_completa: data.mittente_denominazione }
      : null,
    num_colli: data.num_colli ?? null,
    peso_lordo: data.peso_lordo != null ? Number(data.peso_lordo) : null,
    peso_netto: data.peso_netto != null ? Number(data.peso_netto) : null,
    volume: data.volume != null ? Number(data.volume) : null,
    targa: data.targa ?? null,
    autista: data.autista ?? null,
    tracking_code: data.tracking_code ?? null,
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
  // Riepilogo IVA: la vista DB ricalcola dalle righe attive valorizzate a ogni
  // mutazione; qui leggiamo lo stato corrente (best-effort).
  await loadRiepilogoIva(targetId)
}

// Scopo: Carica il riepilogo IVA aggregato (best-effort: in caso di errore il
//        pannello resta vuoto/nascosto, il resto del drawer non e' impattato).
async function loadRiepilogoIva(targetId = null) {
  const id = targetId ?? effectiveDdtId.value
  if (!id) return
  try {
    riepilogoIva.value = await store.loadRiepilogoIva(id)
  } catch {
    riepilogoIva.value = []
  }
}

watch(() => props.visible, async (v) => {
  if (!v) return
  if (isEdit.value) {
    loadDetail()
  } else {
    // CREATE: risolve la utility di default (parameter DEFAULT_UTILITY) PRIMA di
    // resetForm, così defaultForm() la legge. Poi pre-popola la valuta dalla
    // catena EF (resolve_valuta_default lato BE), come ordini/preventivi.
    await loadUtilityDefault()
    resetForm()
    try {
      const res = await getDdtFormDefaults(null)
      const data = res?.data?.data
      if (data && form.value.valuta_id == null && data.valuta_id != null) {
        form.value.valuta_id = data.valuta_id
      }
    } catch {
      // Best-effort: se l'API e' giu' il drawer si apre comunque (valuta vuota).
    }
  }
})

// Al cambio BA in CREATE applica la valuta BA-derived (BA-wins) via BB
// condiviso useBaFormDefaults (guard latest-wins anti-race, come preventivi/
// offerte). Il DDT non ha termini/modalita di pagamento in testata: nessun
// `apply` extra. Se la risposta arriva dopo l'auto-save bozza, il trigger DB
// ha comunque gia' risolto la valuta sul record (fn_get_valuta_id).
useBaFormDefaults({ form, isEdit, fetchDefaults: getDdtFormDefaults })

// Costruisce il payload testata (create/update). Numeri e stringhe vuote → null:
// il BE normalizza empty→NULL (empty_to_none). billing_account_id/
// emittente_fiscale_id/data solo in create (immutabili/whitelist BE); qui
// componiamo la whitelist comune.
function buildTestataPayload({ includeBa = false } = {}) {
  const f = form.value
  const payload = {
    utility_id: f.utility_id || null,
    valuta_id: f.valuta_id || null,
    data: f.data ? toDateString(f.data) : null,
    causale_trasporto_id: f.causale_trasporto_id || null,
    aspetto_bene_id: f.aspetto_bene_id || null,
    modalita_addebito_trasporto_id: f.modalita_addebito_trasporto_id || null,
    mittente_soggetto_ruolo_id: f.mittente_soggetto_ruolo_id || null,
    vettore_soggetto_ruolo_id: f.vettore_soggetto_ruolo_id || null,
    num_colli: f.num_colli ?? null,
    peso_lordo: f.peso_lordo ?? null,
    peso_netto: f.peso_netto ?? null,
    volume: f.volume ?? null,
    targa: f.targa || null,
    autista: f.autista || null,
    tracking_code: f.tracking_code || null,
  }
  if (includeBa) {
    payload.billing_account_id = f.billing_account_id || null
    // Opzionale per BE: se omesso (es. admin globale che non sceglie) il
    // trigger DB fa fallback dal billing_account.
    payload.emittente_fiscale_id = f.emittente_fiscale_id || null
  }
  return payload
}

// Auto-save bozza + abbandono bozza orfana via BB condiviso (B13, regola del 2).
// Trigger: cliente (BA) valorizzato in CREATE. `close`/`onVisibleChange` usati
// dal template; createdId resta ref del drawer.
const { close, onVisibleChange } = useDrawerAutosaveBozza({
  emit,
  execute,
  loading,
  createdId,
  isEdit: () => isEdit.value,
  contentReady: () => contentReady.value,
  triggerSources: () => form.value.billing_account_id,
  isReady: (baId) => baId != null,
  createDraftApi: createDdt,
  buildDraftPayload: async () => buildTestataPayload({ includeBa: true }),
  tabEntity: TAB_ENTITIES.DDT,
  fetchDetail: (id) => loadDetail(id),
  deleteDraft: (id) => store.elimina(id),
  righeCountGetter: () => detail.value?.righe_count ?? 0,
  messages: {
    bozzaCreata: t('vendite.ddt.bozza_creata'),
    abbandonoTitolo: t('vendite.ddt.abbandono_bozza_titolo'),
    abbandonoMessage: t('vendite.ddt.conferma_abbandono_bozza'),
    abbandonoConferma: t('vendite.ddt.abbandono_bozza_conferma'),
    bozzaEliminata: t('vendite.ddt.bozza_eliminata'),
  },
})

const canSave = computed(() => {
  if (isReadonly.value) return false
  return form.value.billing_account_id != null
})

async function handleSave() {
  if (isEdit.value || createdId.value !== null) {
    // UPDATE testata (DRAFT). billing_account_id NON aggiornabile (whitelist BE).
    const result = await execute(
      () => store.update(effectiveDdtId.value, buildTestataPayload()),
      { successMessage: t('vendite.ddt.ddt_salvato') },
    )
    if (result !== null) {
      await loadDetail()
      emit('saved', result)
    }
  } else {
    // Fallback CREATE manuale (auto-save non scattato): chiude dopo create.
    const result = await execute(
      () => store.create(buildTestataPayload({ includeBa: true })),
      { successMessage: t('vendite.ddt.ddt_creato') },
    )
    if (result !== null) emit('saved', result)
  }
}

// --- Azioni stato ---

// Dialog emissione DDT: aperto quando l'azione 'emetti' porta a EMESSO
// (assegna numero, gate componenti). Anteprima PDF accompagnatorio + allegati
// via BB DocumentoEmissioneDialog (mirror ordini).
const emissioneDialogVisible = ref(false)
const emissioneLoading = ref(false)

function onEmetti() {
  emissioneDialogVisible.value = true
}

// Scopo: callback @confirm di DdtEmissioneDialog. Riceve i file staged
// dall'utente e chiama store.emetti (POST multipart /emetti/). Se la
// generazione del documento fallisce il BE annulla l'emissione (stato resta
// DRAFT, numero non consumato).
async function handleEmissioneConferma({ files }) {
  emissioneLoading.value = true
  const result = await execute(
    () => store.emetti(effectiveDdtId.value, { allegati: files || [] }),
    { successMessage: t('vendite.ddt.ddt_emesso') },
  )
  emissioneLoading.value = false
  if (result !== null) {
    emissioneDialogVisible.value = false
    await loadDetail()
    emit('saved', result)
  }
}

// Push singolo a commessa. Toast differenziato per `report.stato` (l'orchestrator
// risponde 200 anche con esito PARZIALE/ERRORE per riga — gemello ordini).
function onPush() {
  confirmAction({
    message: t('vendite.ddt.push_commessa_messaggio'),
    onAccept: async () => {
      const result = await execute(() => store.push(effectiveDdtId.value))
      if (result === null) return  // errore HTTP gia' gestito da useApiHandler

      const stato = result?.stato
      const pushLogId = result?.push_log_id
      const righe = result?.handlers?.reduce(
        (acc, h) => acc + (h?.created ?? 0) + (h?.updated ?? 0),
        0,
      ) ?? result?.righe_pushable ?? 0

      if (stato === 'COMPLETATO') {
        notify.success(t('vendite.ddt.push_commessa_ok', { righe, push_log_id: pushLogId }))
      } else if (stato === 'PARZIALE') {
        notify.warn(t('vendite.ddt.push_commessa_parziale', { righe, push_log_id: pushLogId }))
      } else if (stato === 'ERRORE') {
        const firstError = result?.handlers?.[0]?.errors?.[0] || t('common.generic_error')
        notify.error(t('vendite.ddt.push_commessa_errore', { primo_errore: firstError }))
      } else if (stato === 'SKIPPED') {
        notify.warn(t('vendite.ddt.push_commessa_skipped'))
      } else {
        notify.success(t('vendite.ddt.push_commessa_ok_generico'))
      }

      if (stato === 'COMPLETATO' || stato === 'PARZIALE') {
        await loadDetail()
        emit('saved', result)
      }
    },
  })
}

// Smista le azioni data-driven (`available_actions`) ai relativi handler.
// emetti/push_commessa hanno flussi dedicati; le altre transizioni
// (spedisci/consegna/reso/annulla) passano dal cambio stato generico.
function onAction(action) {
  if (action.key === 'emetti') { onEmetti(); return }
  if (action.key === 'push_commessa') { onPush(); return }
  if (action.requires_confirm) {
    confirmAction({
      message: t('vendite.ddt.conferma_cambio_stato', { stato: t(action.label_key) }),
      onAccept: () => eseguiCambioStato(action),
    })
  } else {
    eseguiCambioStato(action)
  }
}

// Transizione di stato generica (target_state dell'azione). Il trigger DB valida
// l'ammissibilita'; qui orchestriamo chiamata + refresh detail.
async function eseguiCambioStato(action) {
  const result = await execute(
    () => store.cambiaStato(effectiveDdtId.value, action.target_state),
    { successMessage: t('vendite.ddt.stato_cambiato') },
  )
  if (result !== null) {
    await loadDetail()
    emit('saved', result)
  }
}

// Azioni del drawer DDT consumate da DrawerActionsBar. Le transizioni di stato
// arrivano data-driven da fn_available_actions_ddt (mapper condiviso); in
// readonly puro (LETTURA/split) sono nascoste.
const drawerActions = computed(() => {
  if (!hasDetail.value) return []
  const readonlyPuro = props.readonly || parentReadonly.value
  const stateActions = mapAvailableActionsToDrawerActions({
    availableActions: availableActions.value,
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
      label: t('vendite.ddt.gestisci_note'),
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
        :title="t('vendite.ddt.ddt')"
        :icon="NAV_ICONS.DDT"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- Header info: visibile in EDIT classico e in CREATE post auto-save. -->
      <template v-if="hasDetail">
        <DrawerEntityHeader>
          <!-- Numero: "—" finche' il DDT e' in DRAFT (assegnato solo a EMESSO). -->
          <Tag :value="detail.numero || '—'" severity="secondary" />
          <span v-if="detail.data" class="app-drawer-header-muted font-bold">
            {{ displayDate(detail.data) }}
          </span>
          <!-- Provenienza: chip read-only quando il DDT nasce da un ordine
               (evasione). Mostra il numero dell'ordine di origine. -->
          <Tag
            v-if="detail.ordine_origine_numero"
            :value="t('vendite.ddt.origine_chip', { numero: detail.ordine_origine_numero })"
            severity="info"
            icon="pi pi-link"
            v-tooltip.bottom="t('vendite.ddt.origine_chip_tooltip')"
          />

          <template #status>
            <Tag
              :value="detail.stato_descrizione"
              :severity="statoDdtSeverity(detail.stato_codice_interno)"
            />
          </template>
        </DrawerEntityHeader>

        <DrawerActionsBar :actions="drawerActions">
          <template #suffix>
            <!-- Stampa DDT accompagnatorio: anteprima in bozza, gestione
                 documenti generati post-emissione. BB EntityPdfButton 1:1. -->
            <EntityPdfButton
              :sorgente-code="SORGENTE_CODES.DDT"
              :entity-id="effectiveDdtId"
              :pdf="detail.pdf"
              i18n-prefix="vendite.ddt.pdf"
              :dialog-title="detail.numero
                ? t('vendite.ddt.pdf.dialog_title', { numero: detail.numero })
                : ''"
            />
          </template>
        </DrawerActionsBar>
      </template>

      <Divider v-if="hasDetail" />

      <!-- Form testata: monta dopo l'animazione drawer per evitare rimbalzo lookup. -->
      <DdtForm v-if="contentReady"
        :form="form" :is-modificabile="canEditTestataEffective && !isReadonly"
        :non-editable-fields="nonEditableFields"
        :record="detail"
        :is-edit="isEdit || createdId !== null" />

      <!-- Righe: visibili appena c'e' detail (EDIT classico o CREATE post auto-save). -->
      <template v-if="contentReady && hasDetail">
        <!-- Sezione indirizzi (UX v2, BB condiviso): solo il default CON,
             avviso se mancante (obbligatorio all'emissione, guard DB),
             pulsante "Indirizzi" che apre il drawer di gestione. -->
        <DocumentoIndirizziSection
          dominio="ddt"
          :doc-id="effectiveDdtId"
          :soggetto-ruolo-id="detail?.destinatario_soggetto_ruolo_id ?? null"
          :istanza-utility-id="detail?.istanza_utility_id ?? null"
          :readonly="!(canEditTestataEffective && !isReadonly)"
          @state="(s) => { indirizzoObbligatorioMancante = s.obbligatorioMancante }" />

        <Divider />
        <DdtRigheTable
          :ddt-id="effectiveDdtId"
          :is-modificabile="canEditRighe && !isReadonly"
          @changed="loadDetail()"
          @form-aperto="(v) => { formRigaAperto = v }" />

        <!-- Riepilogo IVA aggregato (regola fiscale DPR 633/72 art. 21).
             Visibile con almeno una riga valorizzata (righe prezzo NULL escluse
             in vista: DDT solo di trasporto -> pannello nascosto). Componente
             riusabile cross-dominio condiviso con preventivi/ordini. -->
        <template v-if="showRiepilogoIva">
          <Divider />
          <RiepilogoIvaTable :items="riepilogoIva" :show-subtitle="true" />
        </template>

        <!-- Crea reso (slice resi): righe consegnate con residuo rendibile.
             Il reso nasce DRAFT nel tab Resi; alla sua CONFERMA il BE riapre
             il residuo ordine e, se reso totale, flippa questo DDT a RESO.
             In CONSEGNATO il contenuto e' `app-readonly` (lock-di-stato) ma la
             creazione reso e' un'azione di processo legittima → `app-escape`
             la mantiene cliccabile (mirror pannello evasione ordini). In
             readonly PURO il pannello e' consuntivo (niente azioni). -->
        <template v-if="showResoPanel">
          <Divider />
          <div class="app-escape">
            <DdtResoPanel
              :ddt-id="effectiveDdtId"
              :readonly="props.readonly || parentReadonly"
              @reso-creato="loadDetail()" />
          </div>
        </template>

        <!-- Genealogia/lineage (pannello "Passaggi", BB condiviso lazy:
             fetch al primo expand; app-escape interno per la consultazione
             in readonly di stato). -->
        <Divider />
        <LineagePassaggiPanel
          base-path="/vendite/ddt"
          :doc-id="effectiveDdtId" />

      </template>

      <FormFooter v-if="canEditTestataEffective && !isReadonly && !formRigaAperto"
        :loading="loading" :disabled="!canSave"
        @save="handleSave" @cancel="close" />
      <FormFooter v-else-if="hasDetail && !formRigaAperto" close-only @cancel="close" />
    </div>
  </Drawer>

  <!-- Sub-drawer note: cablato sull'id effettivo del DDT. -->
  <DdtNoteDrawer
    v-if="effectiveDdtId"
    v-model:visible="noteDrawerVisible"
    :ddt-id="effectiveDdtId"
  />

  <!-- Dialog emissione DDT (transizione DRAFT → EMESSO, assegna numero). -->
  <DdtEmissioneDialog
    v-model:visible="emissioneDialogVisible"
    :ddt="detail"
    :loading="emissioneLoading"
    @confirm="handleEmissioneConferma"
    :indirizzo-mancante="indirizzoObbligatorioMancante"
  />
</template>
