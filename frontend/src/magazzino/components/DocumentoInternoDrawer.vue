<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Il drawer OPERATIVO del documento interno di magazzino — un
//        inventario o una rettifica, UN drawer con la famiglia in prop (Q-1):
//        testata, righe (lista standard + form sotto), e — per l'inventario —
//        il piano.
//
// ⭐ LA BARRA E' DATA, NON CODICE (R-1, dal 2026-09-23). Le transizioni
//    («Conferma», «Riapri», «Annulla») escono da `capabilities.available_
//    actions` via `mapAvailableActionsToDrawerActions`, e «Registra» dalla
//    terna `can_registra` / `_reason` / `_reason_key`. ⛔ Nessun `v-if` su
//    `stato` al loro posto: sarebbe la matrice del guard riscritta una
//    seconda volta (frontend-standards §Azioni Drawer). ⚠️ Anche il
//    pulsante SPENTO si monta, col motivo nel tooltip: «permesso ⇒ nascondi,
//    stato ⇒ disabilita col motivo» (api.md §Capability). La nota dello stato
//    chiuso arriva dallo stesso blob (`stato_info_key`).
//
// ⭐ IL READONLY LO CALCOLA QUESTO DRAWER e lo propaga (`provide(READONLY_KEY)`):
//    permessi d'area (dal provider della vista) + stato del documento — le
//    righe e la testata si scrivono solo in `DRAFT` (guard di famiglia
//    `E_MAG_DOCUMENTO_RIGHE_CONGELATE`; testata readonly a video fuori da
//    DRAFT, Q-2). I figli (lista, form, barra) leggono `useInjectReadonly()` e
//    basta: zero logica locale (§catena readonly).
//
// ⭐ LE RIGHE SONO UNA LISTA STANDARD (`useDrawerTabLista` + `<DrawerTabLista>`,
//    liste 71 e 74): pagine, ricarica, colonne, export. Il form di riga vive
//    SOTTO la lista, mai in un drawer annidato. ⭐ La macchina del
//    master-detail e' il BB `useFormInline` dal 2026-09-28, lo stesso
//    di `DistintaDrawer` e `RigheMasterDetailTable`: il debito dichiarato qui
//    e' chiuso (brief-db-liste-righe-documento L1).
import { computed, provide, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'

import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import { useFooterDocumento } from '../../core/composables/useFooterDocumento'
import AppDrawer from '../../core/components/AppDrawer.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useChiaveGesto } from '../../core/composables/useChiaveGesto'
import { mapAvailableActionsToDrawerActions } from '../../core/composables/useDrawerActions'
import { aspettoAzione } from '../../core/aspettoAzioni'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useDrawerFormPreserve, unisciFotografie } from '../../core/composables/useDrawerFormPreserve'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { useNotify } from '../../core/composables/useNotify'
import { READONLY_KEY, useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useFormInline } from '../../core/composables/useFormInline'
import { DATE_FORMAT, DRAWER_WIDTH, MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate, parseIsoDate, toDateString } from '../../core/utils/date'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { documentoInternoSeverity } from '../../core/utils/severity'
import { exportRighe } from '../api/magazzino'
import { useEtichetteMagazzino } from '../etichette'
import { useDocumentiInterniStore } from '../stores/documentiInterni'
import { useDocumentoRigheStore } from '../stores/documentoRighe'
import { AZIONE_REGISTRA_MAGAZZINO, FAMIGLIE, STATO_DOCUMENTO } from '../vocabolari'
import DocumentoInternoRigaForm from './DocumentoInternoRigaForm.vue'
import InventarioPianoDialog from './InventarioPianoDialog.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  famiglia: { type: String, required: true, validator: (v) => v in FAMIGLIE },
  documentoId: { type: [Number, null], default: null },
  // Il readonly da CONTESTO (split-view): si somma a permessi e stato.
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible'])

const { t, te } = useI18n()
const f = FAMIGLIE[props.famiglia]
const store = useDocumentiInterniStore(f.codice)
const storeRighe = useDocumentoRigheStore(f.codice)
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
const { execute, loading: salvando, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()
// ⭐ La key del GESTO «Registra» (`useChiaveGesto`): la conferma si chiude al
//    clic, quindi il reinvio dopo un timeout passa da una conferma nuova — e
//    deve rimandare la stessa key, perche' il posting non si rifa'. Il payload
//    e' il documento: cambiare documento e' un gesto nuovo.
const gestoRegistra = useChiaveGesto()
const notify = useNotify()
const { statoDocumento } = useEtichetteMagazzino()
const parentReadonly = useInjectReadonly()
// ⚠️ Guard anti-race: aprire due documenti in rapida successione farebbe
//    atterrare la risposta piu' lenta DOPO quella piu' recente.
const { tag, isCurrent, invalidate } = useFetchVersion()

const detail = ref(null)
const loading = ref(false)
// ⭐ Il form di riga sotto la lista: la macchina e' il BB (regola del 2). Il
//    click apre la MODIFICA solo se le righe si scrivono.
//    ⚠️ `isReadonly` e' dichiarata piu' sotto: il getter e' letto al click,
//    non adesso.
const {
  formAperto, rigaInModifica, apriRiga, chiudiForm, ancoraForm, azioneNuovaRiga,
} = useFormInline({
  padre: () => (props.visible ? props.documentoId : null),
  puoModificare: () => !isReadonly.value,
  // D-8: cambiare riga col form modificato chiede (letto al clic). ⚠️ Solo la
  //    fotografia della RIGA: cambiare riga non tocca la testata, e l'unione
  //    `documento` chiederebbe per una testata modificata che resta li'.
  confermaCambio: (procedi) =>
    (rigaForm.value ? rigaForm.value.chiudiConConferma(procedi) : procedi()),
})
const pianoVisible = ref(false)

// ── il readonly, calcolato qui e propagato ────────────────────────
// (1) permessi d'area, (2) contesto, (3) stato: fuori da DRAFT niente si scrive.
const isWorkflowLocked = computed(
  () => detail.value != null && detail.value.stato !== STATO_DOCUMENTO.DRAFT,
)
const isReadonly = computed(
  () => parentReadonly.value || props.readonly || isWorkflowLocked.value,
)
provide(READONLY_KEY, isReadonly)
// Il readonly da PERMESSI, da solo: serve a distinguere «non puoi» (si
// nasconde) da «non adesso» (si disabilita col motivo) sulle azioni di riga.
const readonlyPermessi = computed(() => parentReadonly.value || props.readonly)

// ── la testata (form) ─────────────────────────────────────────────
const form = ref(defaultForm())
// La ricarica del dettaglio dopo una riga NON deve cancellare una descrizione
// digitata e non salvata: il BB tiene la baseline e ripristina il pendente.
const { preserva, reset: resetPreserva, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })
// ⭐ D-13 (2026-10-03, analisi-fe-chrome-drawer): testata E riga aperta, una
//    domanda sola — all'uscita e al cambio di riga. La fotografia della riga la
//    tiene il suo form (`DocumentoInternoRigaForm`, `defineExpose`).
const rigaForm = ref(null)
const documento = unisciFotografie({ modificato, chiudiConConferma }, () => rigaForm.value)
// L'ancora del form inline (`useFormInline`) e' il form della riga: il suo
// `ref` serve gia' alla fotografia, quindi l'ancora lo segue invece di
// prendersi un secondo `ref`. ⚠️ `flush: 'sync'`: l'ancora dev'essere legata
// prima del `nextTick` in cui il BB fa scorrere il form in vista.
watch(rigaForm, (el) => ancoraForm(el), { flush: 'sync' })
// Il footer di un documento: la regola e' del BB (D-11), qui come per vendite.
// ⚠️ `presente`: finche' il dettaglio non c'e' (caricamento, errore) niente
//    Annulla/Salva su un form vuoto.
const footerDrawer = useFooterDocumento({
  formRigaAperto: () => formAperto.value,
  modificabile: () => !isReadonly.value,
  presente: () => detail.value != null,
})
const modificatoDocumento = documento.modificato

function defaultForm() {
  return { data: null, descrizione: '' }
}

function populateForm(d) {
  form.value = {
    data: parseIsoDate(d.data),
    descrizione: d.descrizione || '',
  }
}

const canSaveTestata = computed(() => form.value.data != null)

async function onSalvaTestata() {
  const payload = { data: toDateString(form.value.data) }
  if (f.conDescrizione) payload.descrizione = form.value.descrizione?.trim() || null
  const esito = await execute(
    () => store.aggiorna(props.documentoId, payload),
    { successMessage: t('magazzino.documenti_interni.testata_salvata') },
  )
  if (esito !== null) {
    resetPreserva()
    await loadDetail()
  }
}

// ── la barra ──────────────────────────────────────────────────────
// Il blob della capability: `{}` finche' il dettaglio non c'e', cosi' i
// computed qui sotto non guardano mai dentro un `null`.
const capabilities = computed(() => detail.value?.capabilities ?? {})

// Le transizioni di stato, dalla matrice che il guard fa rispettare. ⛔ Il
// `readonly` che si passa al mapper e' quello PURO (permessi + contesto), non
// `isReadonly`: quest'ultimo include il lock di stato, e un documento
// confermato ha il form bloccato ma deve comunque mostrare «Riapri».
const stateActions = computed(() => mapAvailableActionsToDrawerActions({
  availableActions: capabilities.value.available_actions ?? [],
  t,
  te,
  readonly: readonlyPermessi.value,
  onAction: (action) => onCambiaStato(action),
}))

// Scopo: chiede la transizione. `requires_confirm` lo dice il DATO (oggi solo
//        l'annullamento, che e' terminale), non un `if` sul codice dello stato.
function onCambiaStato(action) {
  const esegui = async () => {
    const esito = await execute(
      () => store.cambiaStato(props.documentoId, action.target_state),
      { successMessage: t('magazzino.documenti_interni.stato_cambiato') },
    )
    if (esito === null) return
    ricarica()
    // ⭐ Q-5 (D-L2-n): dopo un CONFIRM riuscito il piano si apre DA SOLO,
    //    sempre — e' la fotografia contro cui si registrera', con le
    //    `NON_CONTATA` evidenziate, e la si vede una volta. Non e' un `v-if`
    //    sullo stato del documento: e' la reazione a QUESTA transizione, che
    //    l'operatore ha appena chiesto.
    if (f.haPiano && action.target_state === STATO_DOCUMENTO.CONFIRM) pianoVisible.value = true
  }
  if (!action.requires_confirm) { esegui(); return }
  confirmAction({
    header: t(action.label_key),
    // ⚠️ L'etichetta entra CITATA, non coniugata: «Vuoi annulla…» non e'
    //    italiano, e un verbo all'infinito per ogni azione sarebbe un secondo
    //    vocabolario accanto alle `label_key` del blob.
    message: t('magazzino.documenti_interni.conferma_transizione', {
      azione: t(action.label_key),
    }),
    // ⚠️ `danger` da solo porterebbe la coppia «Elimina» + cestino: qui il
    //    gesto e' un annullamento, non una cancellazione, e label e icona
    //    vengono dal verbo della capability (lo stesso aspetto del pulsante).
    acceptLabel: t(action.label_key),
    acceptIcon: aspettoAzione(action.key).icona,
    danger: aspettoAzione(action.key).severity === 'danger',
    onAccept: esegui,
  })
}

// Scopo: il verbo irreversibile. ⭐ Lo stato del pulsante NON si calcola qui:
//        `can_registra` e il suo motivo vengono dalla stessa check che le due
//        `fn_posta_*` chiamano per rifiutare — il pulsante non puo' promettere
//        cio' che il database rifiutera'.
function onRegistra() {
  const riepilogo = detail.value?.piano_riepilogo
  const righe = [t('magazzino.documenti_interni.registra.irreversibile')]
  if (f.haPiano && riepilogo) {
    righe.push(t('magazzino.documenti_interni.registra.riepilogo_piano', {
      con_delta: riepilogo.n_con_delta ?? 0,
      non_contate: riepilogo.n_non_contate ?? 0,
    }))
  }
  confirmAction({
    header: t('magazzino.documenti_interni.registra.titolo'),
    // Spazio, non '\n': il messaggio del ConfirmDialog non e' `pre-line`, e
    //    le frasi finiscono gia' col punto.
    message: righe.join(' '),
    acceptLabel: t('magazzino.documenti_interni.registra.conferma'),
    acceptIcon: NAV_ICONS.MOVIMENTI,
    danger: true,
    onAccept: async () => {
      const documentoId = props.documentoId
      const esito = await execute(() => gestoRegistra.invia(
        { famiglia: f.codice, documentoId },
        (config) => store.registra(documentoId, config),
      ))
      if (esito !== null) {
        notify.success(t('magazzino.documenti_interni.registra.fatto', { n: esito.n_movimenti ?? 0 }))
        ricarica()
      }
    },
  })
}

const drawerActions = computed(() => {
  if (!detail.value) return []
  const azioni = [...stateActions.value]
  // ⚠️ «Registra» c'e' ANCHE spento, col motivo nel tooltip: e' lo stato, e
  //    puo' cambiare. Sparisce solo senza permessi d'area (`hideWhenReadonly`)
  //    o senza l'azione di processo (`action`, che il BE presidia davvero).
  // ⭐ In BOZZA c'e', spento col motivo `non_confermato` (brief 2-bis: «Registra
  //    spento su una bozza»): dice all'operatore qual e' il passo che manca.
  // ⛔ Sparisce sul documento CHIUSO (POSTED, CANCEL): li' non c'e' piu' niente
  //    da registrare, e un pulsante grigio in fondo a un documento chiuso e'
  //    rumore — la nota di stato dice gia' la strada. «Chiuso» lo dice la
  //    MATRICE (`can_change_state`: nessuna transizione da qui), non un
  //    confronto su `stato_codice` scritto a mano.
  if (capabilities.value.can_change_state) {
    const motivo = capabilities.value.can_registra_reason_key
    azioni.push({
      key: 'registra',
      kind: 'primary',
      label: t('magazzino.documenti_interni.registra.azione'),
      icon: NAV_ICONS.MOVIMENTI,
      severity: 'warn',
      hideWhenReadonly: true,
      action: AZIONE_REGISTRA_MAGAZZINO,
      disabled: !capabilities.value.can_registra,
      tooltip: capabilities.value.can_registra
        ? undefined
        : labelOrCode(t, te, motivo, capabilities.value.can_registra_reason || ''),
      command: onRegistra,
    })
  }
  if (f.haPiano) {
    azioni.push({
      key: 'piano',
      kind: 'manage',
      label: t('magazzino.piano.apri'),
      icon: MANAGE_ICONS.LIST,
      badge: detail.value.piano_riepilogo?.n_con_delta ?? undefined,
      command: () => { pianoVisible.value = true },
    })
  }
  return azioni
})

// ── la lista delle righe ──────────────────────────────────────────
// ⚠️ `parentId` porta l'id SOLO a drawer aperto: il `null` alla chiusura dice
//    allo scaffolding di resettare lo store — le righe del documento
//    precedente non lampeggiano sotto il prossimo.
// ⭐ «Nuova riga» entra nella barra della lista come azione del caller
//    (`extraActions`): ha una CONDIZIONE (solo in DRAFT, non mentre il form e'
//    aperto) che l'azione standard «Nuovo» non sa.
const azioniRighe = computed(() => [
  azioneNuovaRiga({ label: t('magazzino.documenti_interni.riga.nuova') }),
])

const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm, reloadAll,
} = useDrawerTabLista(storeRighe, {
  parentId: () => (props.visible ? props.documentoId : null),
  parentField: 'documentoId',
  exportFn: (params) => exportRighe(f.codice, props.documentoId, params),
  getExportParams: (formato) => ({ formato, ...storeRighe.paramsFiltro() }),
  extraActions: () => azioniRighe.value,
  // «Ricarica» della barra ricarica anche la TESTATA: `righe_count` e il
  // riepilogo del piano dipendono dalle righe.
  fetchExtra: () => loadDetail(),
})

// ── azioni di riga ────────────────────────────────────────────────
// «Permesso ⇒ nascondi, stato ⇒ disabilita col motivo»: senza permesso
// niente; fuori da DRAFT il cestino c'e' ma spento, col motivo — e' lo stato,
// puo' cambiare (CONFIRM → DRAFT riapre le righe).
function buildRowActions(riga) {
  if (readonlyPermessi.value) return []
  const congelate = isWorkflowLocked.value
  return [
    {
      key: 'elimina',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      disabled: congelate,
      tooltip: congelate ? t('magazzino.documenti_interni.righe_congelate') : undefined,
      command: () => onEliminaRiga(riga),
    },
  ]
}

function onEliminaRiga(riga) {
  confirmAction({
    header: t('confirm.delete_title'),
    message: t('magazzino.documenti_interni.riga.conferma_elimina', {
      articolo: riga.articolo_codice || riga.id,
    }),
    danger: true,
    onAccept: async () => {
      const esito = await execute(
        () => store.eliminaRiga(props.documentoId, riga.id),
        { successMessage: t('magazzino.documenti_interni.riga.eliminata') },
      )
      if (esito !== null) ricarica()
    },
  })
}

// ── caricamento ───────────────────────────────────────────────────
async function loadDetail() {
  if (!props.documentoId) return
  const mio = tag()
  loading.value = true
  // PRIMA del fetch: fissa la baseline del form e cattura il pendente.
  const applica = preserva()
  try {
    const d = await loadDetailOrClose(() => store.fetchDetail(props.documentoId))
    if (!isCurrent(mio)) return
    if (d == null) return
    detail.value = d
    populateForm(d)
    applica()
  } finally {
    if (isCurrent(mio)) loading.value = false
  }
}

// Scopo: ricarica dopo un gesto su una riga — testata E righe. La lista dei
//        documenti (che mostra `righe_count`) si ricarica da sola: il verbo
//        dello store ha emesso l'evento della famiglia.
function ricarica() {
  chiudiForm()
  reloadAll()
}

// ⚠️ Il CARICAMENTO non sta qui: lo fa il watch dello scaffolding della lista
//    (`fetchExtra`) al cambio di documento, e il form lo chiude il BB del
//    master-detail. Qui restano il reset del piano all'apertura e la pulizia
//    alla chiusura.
watch(
  () => [props.visible, props.documentoId],
  ([vis]) => {
    if (vis && props.documentoId) {
      pianoVisible.value = false
    } else if (!vis) {
      detail.value = null
      form.value = defaultForm()
      resetPreserva()
      invalidate()
    }
  },
  { immediate: true },
)
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <!-- Il Salva della testata e' il footer del drawer, IN FONDO dopo la lista
       (standard master-detail, punto 12); `FormFooter` nasconde da se' il
       pulsante in readonly. ⚠️ Solo a form di riga chiuso: in form mode il
       Salva della riga e' l'unico a video. `proteggi-corpo` spento: la sola
       lettura protegge il solo pannello della testata, non la lista. -->
  <AppDrawer
    :visible="visible"
    :title="t(`${f.i18n}.titolo_singolare`)"
    :icon="f.haPiano ? NAV_ICONS.INVENTARI : NAV_ICONS.RETTIFICHE"
    :width="DRAWER_WIDTH.WIDE"
    :proteggi-corpo="false"
    :modificato="modificatoDocumento"
    :conferma-uscita="documento.chiudiConConferma"
    :footer="footerDrawer"
    :loading="salvando"
    :save-disabled="!canSaveTestata"
    :cancel-label="t('common.close')"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSalvaTestata"
  >
    <div v-if="loading && !detail" class="app-loading">
      <i :class="STATUS_ICONS.CARICAMENTO" />
    </div>

    <template v-if="detail">
      <DrawerEntityHeader>
        <Tag :value="`#${detail.id}`" severity="secondary" />
        <span>
          {{ detail.magazzino_codice }}
          <span v-if="detail.magazzino_descrizione" class="app-drawer-header-muted">
            · {{ detail.magazzino_descrizione }}
          </span>
        </span>
        <span class="app-drawer-header-muted">
          {{ t('magazzino.documenti_interni.del_data', { data: displayDate(detail.data) }) }}
        </span>
        <!-- Il magazzino a UBICAZIONI lo si dice in testata: decide se la riga
             chiede l'ubicazione. -->
        <Tag
          v-if="detail.magazzino_usa_ubicazioni"
          :value="t('magazzino.documenti_interni.usa_ubicazioni')"
          severity="info"
        />

        <template #status>
          <Tag
            :value="statoDocumento(detail.stato)"
            :severity="documentoInternoSeverity(detail.stato)"
          />
        </template>
      </DrawerEntityHeader>

      <!-- La nota di stato arriva dal blob (`capabilities.stato_info_key`): qui nessun
           `v-if` sullo stato. Oggi e' `null` (R-1). -->
      <DrawerActionsBar
        :actions="drawerActions"
        :info-key="capabilities.stato_info_key || ''"
      />

      <!-- ══ La testata ══ -->
      <div class="app-drawer-section">
        <h4>{{ t('magazzino.documenti_interni.sezione_testata') }}</h4>
      </div>
      <div :class="{ 'app-readonly': isReadonly }">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('magazzino.documenti_interni.campo_data') }} *</label>
            <DatePicker
              v-model="form.data"
              :date-format="DATE_FORMAT"
              show-icon
              :invalid="campiErrati.includes('data')"
            />
            <small class="app-text-muted">
              {{ t('magazzino.documenti_interni.data_aiuto') }}
            </small>
          </div>
          <div v-if="f.conDescrizione" class="form-field">
            <label>{{ t('magazzino.documenti_interni.campo_descrizione') }}</label>
            <InputText
              v-model="form.descrizione"
              maxlength="500"
              :invalid="campiErrati.includes('descrizione')"
            />
          </div>
        </div>
      </div>

      <!-- ══ Le righe ══ -->
      <div class="app-drawer-section">
        <h4>
          {{ t('magazzino.documenti_interni.sezione_righe') }}
          <span class="app-text-muted">({{ detail.righe_count ?? 0 }})</span>
        </h4>
      </div>

      <!-- Fuori da DRAFT le righe sono congelate: lo si DICE, o l'assenza di
           «Nuova riga» si legge come un difetto. -->
      <Message
        v-if="isWorkflowLocked && !readonlyPermessi"
        severity="info"
        :closable="false"
        size="small"
      >
        {{ t('magazzino.documenti_interni.righe_congelate') }}
      </Message>

      <!-- ⛔ «Non sono riuscito a leggere le righe» non e' «non ce ne sono». -->
      <Message
        v-if="storeRighe.erroreCaricamento"
        severity="warn"
        :closable="false"
        size="small"
      >
        {{ t('common.righe_non_lette') }}
      </Message>

      <DrawerTabLista
        ref="listaRef"
        :codice="f.listaRigheCodice"
        :store="storeRighe"
        :rows="storeRighe.items"
        :total="storeRighe.totalRecords"
        :loading="storeRighe.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        :page-actions="pageActions"
        :dirty="dirty"
        :perimetro-bloccato="perimetroBloccato"
        :riga-attiva="rigaInModifica?.id ?? null"
        :righe-cliccabili="!isReadonly"
        @page="onPage"
        @sort="onSort"
        @row-click="apriRiga"
        @config-loaded="onConfigLoaded"
      >
        <!-- La ricerca: le colonne le decide il catalogo della famiglia
             (`ricerca_full`), il placeholder non le elenca. Sotto 3 caratteri
             il termine non filtra; l'export porta la stessa `search`
             (`paramsFiltro`). -->
        <template #filtri-sempre>
          <InputText
            v-model="searchText"
            class="app-filter-w-lg"
            :placeholder="t('common.search')"
          />
        </template>

        <template #empty>
          <div v-if="!storeRighe.erroreCaricamento" class="app-empty-state">
            <i :class="STATUS_ICONS.VUOTO" />
            <p>{{ t(`${f.i18n}.nessuna_riga`) }}</p>
          </div>
        </template>

        <template #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </DrawerTabLista>

      <!-- Master-detail inline: il form vive SOTTO la lista. -->
      <DocumentoInternoRigaForm
        v-if="formAperto"
        ref="rigaForm"
        :famiglia="famiglia"
        :documento="detail"
        :riga="rigaInModifica"
        @salvata="ricarica"
        @annulla="chiudiForm"
      />
    </template>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />

    <InventarioPianoDialog
      v-if="f.haPiano"
      v-model:visible="pianoVisible"
      :inventario-id="documentoId"
      :riepilogo="detail?.piano_riepilogo ?? null"
    />
  </AppDrawer>
</template>
