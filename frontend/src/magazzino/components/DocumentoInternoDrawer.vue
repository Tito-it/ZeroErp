<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Il drawer OPERATIVO del documento interno di magazzino — un
//        inventario o una rettifica, UN drawer con la famiglia in prop (Q-1):
//        testata, righe (lista standard + form sotto), e — per l'inventario —
//        il piano.
//
// ⏳ SENZA LA BARRA DELLE AZIONI DI STATO (R-1 del brief 2-bis, passo 7 del
//    piano). Le transizioni («Conferma», «Riapri», «Annulla») e «Registra» si
//    montano da `capabilities.available_actions` con
//    `mapAvailableActionsToDrawerActions` — che il backend NON emette finche'
//    `fn_available_actions_*` non esiste a DB. ⛔ Niente `v-if` su `stato`
//    scritto a mano al loro posto: sarebbe la matrice del guard riscritta una
//    seconda volta (frontend-standards §Azioni Drawer). Quando R-1 arriva, le
//    azioni entrano qui, in `drawerActions`, e basta. La barra oggi porta le
//    sole azioni che non dipendono dalla matrice: «Piano» e l'export delle
//    righe, piu' la nota di stato (`stato_info_key`, che oggi e' `null`).
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
//    SOTTO la lista, mai in un drawer annidato. 🔵 Debito dichiarato che
//    RESTA, lo stesso di `DistintaDrawer`: la macchina a stati del
//    master-detail (`formMode`) e' scritta qui invece di passare da
//    `RigheMasterDetailTable`.
import { computed, provide, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DatePicker from 'primevue/datepicker'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'

import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { READONLY_KEY, useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DATE_FORMAT, DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate, parseIsoDate, toDateString } from '../../core/utils/date'
import { documentoInternoSeverity } from '../../core/utils/severity'
import { exportRighe } from '../api/magazzino'
import { useEtichetteMagazzino } from '../etichette'
import { useDocumentiInterniStore } from '../stores/documentiInterni'
import { useDocumentoRigheStore } from '../stores/documentoRighe'
import { FAMIGLIE, STATO_DOCUMENTO } from '../vocabolari'
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

const { t } = useI18n()
const f = FAMIGLIE[props.famiglia]
const store = useDocumentiInterniStore(f.codice)
const storeRighe = useDocumentoRigheStore(f.codice)
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const { execute, loading: salvando, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()
const { statoDocumento } = useEtichetteMagazzino()
const parentReadonly = useInjectReadonly()
// ⚠️ Guard anti-race: aprire due documenti in rapida successione farebbe
//    atterrare la risposta piu' lenta DOPO quella piu' recente.
const { tag, isCurrent, invalidate } = useFetchVersion()

const detail = ref(null)
const loading = ref(false)
// `null` = elenco · `'create'` · `'edit'` (pattern master-detail inline).
const formMode = ref(null)
const rigaInModifica = ref(null)
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
const { preserva, reset: resetPreserva } = useDrawerFormPreserve(form)

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
// ⏳ R-1: qui entreranno `mapAvailableActionsToDrawerActions(capabilities.
//    available_actions)` (kind `state`) e «Registra» (kind `primary`, terna
//    `can_registra*`). Oggi le sole azioni che non dipendono dalla matrice.
const drawerActions = computed(() => {
  if (!detail.value) return []
  const azioni = []
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
  {
    key: 'nuova-riga',
    kind: 'primary',
    label: t('magazzino.documenti_interni.riga.nuova'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    visible: formMode.value === null,
    command: () => { rigaInModifica.value = null; formMode.value = 'create' },
  },
])

const {
  onPage, onSort, paginatorProps, tablePage,
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

// Il click sulla riga apre la MODIFICA solo se le righe si scrivono.
function onRigaClick(riga) {
  if (isReadonly.value) return
  rigaInModifica.value = riga
  formMode.value = 'edit'
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
  formMode.value = null
  rigaInModifica.value = null
  reloadAll()
}

// ⚠️ Il CARICAMENTO non sta qui: lo fa il watch dello scaffolding della lista
//    (`fetchExtra`) al cambio di documento. Qui restano il reset del form
//    all'apertura e la pulizia alla chiusura.
watch(
  () => [props.visible, props.documentoId],
  ([vis]) => {
    if (vis && props.documentoId) {
      formMode.value = null
      rigaInModifica.value = null
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
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    @update:visible="(v) => emit('update:visible', v)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :title="t(`${f.i18n}.titolo_singolare`)"
        :icon="f.haPiano ? NAV_ICONS.INVENTARI : NAV_ICONS.RETTIFICHE"
      />
    </template>

    <div class="app-drawer-content">
      <div v-if="loading && !detail" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="contentReady && detail">
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

        <!-- La nota di stato arriva dal BE (`stato_info_key`): qui nessun
             `v-if` sullo stato. Oggi e' `null` (R-1). -->
        <DrawerActionsBar
          :actions="drawerActions"
          :info-key="detail.stato_info_key || ''"
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
        <!-- Il Salva della testata: `FormFooter` nasconde da se' il pulsante
             in readonly (inject), e sta FUORI dal pannello protect. ⚠️ Solo a
             form di riga chiuso: in form mode il Salva della riga e' l'unico
             a video, e «Chiudi» spingerebbe il form sotto il fold. -->
        <FormFooter
          v-if="!formMode"
          :loading="salvando"
          :disabled="!canSaveTestata"
          :cancel-label="t('common.close')"
          @save="onSalvaTestata"
          @cancel="onClose"
        />

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
          {{ t('magazzino.documenti_interni.righe_non_lette') }}
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
          @page="onPage"
          @sort="onSort"
          @row-click="onRigaClick"
          @config-loaded="onConfigLoaded"
        >
          <template #empty>
            <div v-if="!storeRighe.erroreCaricamento" class="app-empty-state">
              <i class="pi pi-list" />
              <p>{{ t(`${f.i18n}.nessuna_riga`) }}</p>
            </div>
          </template>

          <template #actions="{ data }">
            <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
          </template>
        </DrawerTabLista>

        <!-- Master-detail inline: il form vive SOTTO la lista. -->
        <DocumentoInternoRigaForm
          v-if="formMode"
          :famiglia="famiglia"
          :documento="detail"
          :riga="rigaInModifica"
          @salvata="ricarica"
          @annulla="formMode = null; rigaInModifica = null"
        />
      </template>
    </div>

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
  </Drawer>
</template>
