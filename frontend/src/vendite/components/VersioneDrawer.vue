<script setup>
// Scopo: Sub-drawer dettaglio versione listino con righe prezzo — pattern
//        master-detail inline (frontend-standards §"Master-Detail inline").
//        Lista paginata server-side sopra, form dettaglio sotto.
//        Click riga = edit, pulsante Nuovo = create. Salva/Annulla sempre
//        in basso sotto il form. Articolo immutabile in edit.
//        Solo righe in versione BOZZA sono modificabili/eliminabili.
//
//        Lista convertita a <ListaConfigurabile> (config DB
//        `vendite.listini_righe`, ui.lista_definizione id 37 — 7° lotto,
//        2026-08-03): possibile da quando righe standalone e compositi
//        arrivano dallo STESSO endpoint paginato (UNION lato BE, decisione
//        Tid 2026-08-02) e `total` li conta entrambi. Click riga discrimina:
//        composito apre ComponentiDialog, standalone apre form edit inline.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useFormInline } from '../../core/composables/useFormInline'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { displayDate } from '../../core/utils/date'
import { formatIvaLabel, formatNumber } from '../../core/utils/format'
import { statoVersioneListinoSeverity } from '../../core/utils/severity'
import {
  createRiga,
  updateRiga,
  deleteRiga,
  previewBundleComponenti,
  saveBundleComponenti,
  deleteBundleComponenti,
} from '../api/listini'
import ComponentiDialog from '../_shared/componenti/ComponentiDialog.vue'
import { useArticoloUomOptions } from '../../catalogo/composables/useArticoloUomOptions'
import { useListiniRigheStore } from '../stores/listiniRighe'
import { STATO_VERSIONE_LISTINO } from '../constants'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import ArticoloLookup from '../../catalogo/components/ArticoloLookup.vue'
import AttivoTag from '../../core/components/AttivoTag.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import ApplicaVariazioneDialog from './ApplicaVariazioneDialog.vue'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import FiltriLista from '../../core/components/FiltriLista.vue'

const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()
const { confirmDelete } = useConfirmAction()
const isReadonly = useInjectReadonly()
const store = useListiniRigheStore()

const props = defineProps({
  visible: Boolean,
  listinoId: { type: [Number, null], required: true },
  listinoCodice: { type: String, default: '' },
  listinoDescrizione: { type: String, default: '' },
  listinoUtilityId: { type: [Number, null], default: null },
  versione: { type: Object, required: true }
})

const emit = defineEmits(['update:visible'])

// Scaffolding lista configurabile: search/sort/page + azioni pagina standard
// (Ricarica + Personalizza) + le azioni di dominio via `extraActions` (lazy:
// il closure legge isBozza/formMode definiti sotto solo alla valutazione del
// computed pageActions). Niente exportFn/onNew standard: la "Nuovo" ha
// visibilita'/disable di dominio e viaggia fra le extra.
const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  onReload: reloadAll,
  extraActions: () => [
    {
      key: 'variazione',
      kind: 'utility',
      label: t('vendite.listini.variazione_short'),
      tooltip: t('vendite.listini.variazione_pct_titolo'),
      icon: MANAGE_ICONS.VARIAZIONE_PREZZO,
      showLabel: true,
      visible: isBozza.value,
      command: () => { showVariazioneDialog.value = true },
    },
    // ⚠️ A form aperto «Nuovo» sparisce (regola del BB `useFormInline`):
    //    prima restava attivo durante la modifica di una riga, e un clic
    //    buttava via la modifica in corso.
    azioneNuovaRiga({
      key: 'new',
      label: t('common.new'),
      tooltip: t('vendite.listini.aggiungi_prezzo_hint'),
      visible: () => isBozza.value,
      command: onNew,
    }),
  ],
  searchTableOptions: {
    defaultSortField: 'articolo_descrizione',
    defaultSortOrder: 'asc',
  },
})

// Stato master-detail inline
// formMode: null (nessun form visibile), 'create', 'edit' — la macchina e' il
// BB core `useFormInline` (sede unica, ok Tid 2026-09-28); qui restano i verbi
// che ci aggiungono il form del prezzo. Il click apre la modifica solo in
// BOZZA (getter letto al click: `isBozza` e' dichiarata piu' sotto).
const {
  formMode, formAperto, rigaInModifica, nuovaRiga, apriRiga, chiudiForm, ancoraForm, azioneNuovaRiga,
} = useFormInline({
  puoModificare: () => isBozza.value,
  // D-8: cambiare riga col form modificato chiede (il getter e' letto al clic).
  confermaCambio: (p) => inline.chiudiConConferma(p),
})
const form = ref({})
// Modifiche non salvate del form inline: conferma alla chiusura del drawer e
// all'Annulla del form, scritta arancio nel titolo.
const inline = useDrawerFormPreserve(form, {
  visibile: () => props.visible && formAperto.value,
})
const modificato = inline.modificato

// UoM operative dell'articolo selezionato (pattern ContrattoRigheDrawer).
// Composable centralizzato (Fase 4.F1): autopick base solo in create.
const {
  uomOptions, uomLoading, loadUomPerArticolo, pickBaseUomId, resetUomOptions,
} = useArticoloUomOptions()

function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('vendite.listini.uom_base_suffix')}` : ''
  return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
}

// Scopo: carica le UoM e in create pre-seleziona la base.
async function caricaUomConPickBase(articoloId) {
  const list = await loadUomPerArticolo(articoloId)
  if (formMode.value === 'create' && !form.value.uom_id) {
    form.value.uom_id = pickBaseUomId(list)
  }
}

function defaultForm() {
  return {
    articolo_id: null,
    articolo_obj: null,
    uom_id: null,
    prezzo: null,
  }
}

// Watch apertura/chiusura drawer e cambio versione: configura contesto store.
watch(
  () => [props.visible, props.versione?.id],
  ([v, vid]) => {
    if (v && vid) {
      store.setContext(props.listinoId, vid)
      searchText.value = ''
      store.fetchList()
      closeForm()
    } else {
      store.clearContext()
      bundleDialogVisible.value = false
      bundlePadreCorrente.value = null
    }
  },
  { immediate: true },
)

const isBozza = computed(() => props.versione?.stato === STATO_VERSIONE_LISTINO.BOZZA)

// Scopo: ricarica la lista. Dal 2026-08-03 i compositi arrivano dallo STESSO
// endpoint paginato delle righe standalone (UNION lato BE), quindi una fetch
// sola basta: prima ne servivano due e il totale non teneva conto dei compositi.
async function reloadAll() {
  await store.fetchList()
}

// === Azioni master ===
function onNew() {
  form.value = defaultForm()
  nuovaRiga()
  resetUomOptions()
  inline.fissa()
}

// Scopo: click riga (pattern standard liste = interazione principale).
//        Composito → ComponentiDialog (i prezzi vivono in
//        `listini_righe_componenti`); standalone in BOZZA → form edit inline;
//        versioni non BOZZA → sola lettura, nessun form.
// ⚠️ Il composito NON passa da `apriRiga` (non ha un form inline: i suoi
//    prezzi si danno nel dialog), quindi la conferma di D-8 la chiede qui
//    (2026-10-03, rilievo di Tid in collaudo): il dialog e' un'altra riga, e
//    con il form di quella aperta e modificato lo si lasciava sotto, con le
//    modifiche in sospeso, senza chiedere. Dopo il si' il form si chiude — si
//    e' lasciata quella riga —, come quando nel form si sceglie un composito.
function onRowClick(r) {
  if (r?.is_composito) {
    const apriBundle = () => openBundleDialog({
      id: r.articolo_id,
      codice: r.articolo_codice,
      descrizione: r.articolo_descrizione,
      is_composito: true,
    })
    if (!formAperto.value) {
      apriBundle()
      return
    }
    inline.chiudiConConferma(() => {
      closeForm()
      apriBundle()
    })
    return
  }
  apriRiga(r, () => {
    form.value = {
      articolo_id: r.articolo_id,
      articolo_obj: {
        id: r.articolo_id,
        codice: r.articolo_codice,
        descrizione: r.articolo_descrizione,
        _display: `${r.articolo_codice} — ${r.articolo_descrizione}`,
      },
      uom_id: r.uom_id,
      prezzo: r.prezzo != null ? Number(r.prezzo) : null,
    }
    inline.fissa()
    // Edit: UoM gia' nel form, no autopick.
    loadUomPerArticolo(r.articolo_id)
  })
}

function onArticoloSelected(item) {
  // Porta unica "Nuovo": il lookup ammette sia articoli semplici sia padri
  // compositi. Branching sulla selezione:
  //   - composito → chiudo il form inline (non ammesso in `listini_righe`,
  //     trigger DB `E_LISTINO_RIGA_COMPOSITO_VIETATO`) e apro il
  //     ComponentiDialog dei prezzi bundle (`listini_righe_componenti`).
  //   - semplice → form prezzo+UoM standard.
  if (item?.is_composito) {
    closeForm()
    openBundleDialog({
      id: item.id,
      codice: item.codice,
      descrizione: item.descrizione,
      is_composito: true,
    })
    return
  }
  form.value.articolo_id = item?.id || null
  form.value.uom_id = null
  // Create: autopick base.
  caricaUomConPickBase(item?.id)
}

// ── Bundle compositi (modello unificato 2026-05-13) ──
// Lista articoli compositi con almeno 1 prezzo bundle definito + Dialog
// per editing. Refresh dopo ogni save bundle.
const bundleDialogVisible = ref(false)
// Padre composito corrente: oggetto { id, codice, descrizione,
// is_composito } passato come prop `articolo` al Dialog.
const bundlePadreCorrente = ref(null)
// Cache della preview corrente (lista BoM + prezzi gia' definiti) per
// poter risolvere il mapping {componente_id -> articolo_componente_id}
// al confirm della Dialog senza un secondo fetch.
let _bundlePreviewCache = []

// Callback `apiPreview` del Dialog: fetch BoM + prezzi gia' definiti.
// La firma standard del building block e' (documentoId, params) →
// Promise<axiosResponse>; per il listino bundle `documentoId` =
// versione_id e l'articolo_padre arriva da params.articolo_id.
async function bundleApiPreview(versioneId, params) {
  const res = await previewBundleComponenti(
    props.listinoId,
    versioneId,
    params.articolo_id,
  )
  _bundlePreviewCache = res.data?.data ?? []
  return res
}

function openBundleDialog(padre) {
  if (!isBozza.value || isReadonly.value) {
    // Versione non BOZZA: bundle in sola lettura (apertura Dialog ammessa
    // per visualizzare i prezzi, ma il save FE/BE solleva guard BOZZA-only).
    // Per ora limitiamo: avviso lieve via notify se l'admin tenta su
    // versione attiva. Future: aprire Dialog in readonly.
    return
  }
  bundlePadreCorrente.value = padre
  bundleDialogVisible.value = true
}

async function onBundleConfirm({ overrides }) {
  if (!bundlePadreCorrente.value?.id) return
  // Costruisco le rows dal mapping {componente_id: prezzo} del Dialog
  // + dati di contesto dalla preview cached (articolo_componente_id =
  // BoM row id, articolo_figlio_id, iva_id).
  const rows = []
  for (const c of _bundlePreviewCache) {
    const prezzo = overrides?.[c.componente_id]
    if (prezzo == null) continue
    rows.push({
      articolo_componente_id: c.articolo_componente_id,
      articolo_figlio_id: c.componente_id,
      prezzo: String(prezzo),
      iva_id: c.iva_id,
    })
  }
  const result = await execute(
    () => saveBundleComponenti(
      props.listinoId, props.versione.id, bundlePadreCorrente.value.id, rows,
    ),
    { successMessage: t('vendite.listini.bundle_salvato') },
  )
  if (result !== null) {
        await reloadAll()
    bundleDialogVisible.value = false
    bundlePadreCorrente.value = null
  }
}

function closeForm() {
  chiudiForm()
  form.value = {}
  resetUomOptions()
}

function formatPrezzoListino(value) {
  return formatNumber(value, {
    placeholder: '—',
    minimumFractionDigits: 6,
    maximumFractionDigits: 6,
  })
}

// === Validazione form ===
const canSave = computed(() => {
  if (isReadonly.value) return false
  if (!formMode.value) return false
  if (!form.value.articolo_id) return false
  if (!form.value.uom_id) return false
  if (form.value.prezzo == null || form.value.prezzo === '') return false
  return true
})

const formTitle = computed(() => {
  if (formMode.value === 'create') return t('vendite.listini.nuova_riga')
  if (formMode.value === 'edit') return t('vendite.listini.modifica_riga')
  return ''
})

// === Salvataggio ===
async function onSave() {
  const f = form.value
  const payload = {
    prezzo: f.prezzo,
  }
  if (formMode.value === 'create') {
    payload.articolo_id = f.articolo_id
    payload.uom_id = f.uom_id
    const result = await execute(
      () => createRiga(props.listinoId, props.versione.id, payload),
      { successMessage: t('vendite.listini.riga_creata') }
    )
    if (result !== null) {
      await store.fetchList()
      closeForm()
    }
  } else {
    const result = await execute(
      () => updateRiga(props.listinoId, props.versione.id, rigaInModifica.value?.id, payload),
      { successMessage: t('vendite.listini.riga_salvata') }
    )
    if (result !== null) {
      await store.fetchList()
      closeForm()
    }
  }
}

// === Eliminazione riga (con conferma) ===
// Branching:
//   - Riga standalone (`is_composito=false`): DELETE su `listini_righe`.
//   - Riga composito: DELETE dedicato su /bundle/<padre>/ → tabula rasa
//     idempotente lato BE (soft-delete tutte le righe
//     `listini_righe_componenti` del padre per la versione). Endpoint REST
//     semanticamente corretto sostituisce il vecchio workaround
//     `saveBundleComponenti(rows=[])`.
function onDelete(row) {
  const label = row.articolo_codice || row.articolo_descrizione || `#${row.id}`
  confirmDelete(label, async () => {
    if (row.is_composito) {
      const result = await execute(
        () => deleteBundleComponenti(
          props.listinoId, props.versione.id, row.articolo_id,
        ),
        { successMessage: t('vendite.listini.composito_eliminato') },
      )
      if (result !== null) {
        await reloadAll()
      }
      return
    }
    const result = await execute(
      () => deleteRiga(props.listinoId, props.versione.id, row.id),
      { successMessage: t('vendite.listini.riga_eliminata') },
    )
    if (result !== null) {
      // Se stavo editando questa riga, chiudi il form.
      if (rigaInModifica.value?.id === row.id) closeForm()
      await store.fetchList()
    }
  })
}

// Scopo: azioni di riga — solo elimina. La modifica avviene via click
// riga (pattern standard liste, vedi frontend-standards): per righe
// standalone apre form edit inline, per righe composito apre il Dialog.
// Per i compositi, elimina = `saveBundleComponenti(rows=[])` (tabula
// rasa idempotente lato BE), allineato al pattern delete delle righe
// standalone.
function buildRigaActions(row) {
  return [
    {
      key: 'elimina-riga',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: isBozza.value && !isReadonly.value,
      command: () => onDelete(row),
    },
  ]
}

// Righe standalone e compositi bundle sono UNA lista sola (decisione Tid
// 2026-08-02) e arrivano insieme dallo stesso endpoint paginato: il BE le
// unisce con una UNION e `total` le conta entrambe. E' cio' che ha reso
// possibile la conversione a `<ListaConfigurabile>` (prima i compositi
// venivano concatenati QUI dopo la paginazione, e conteggio/pagine mentivano).
//
// Il BE proietta `is_composito` (discriminatore) e `row_key` (chiave stabile
// della DataTable: l'id per le standalone, `composito:<uuid>` per i padri, che
// non hanno un id di testata perche' sono N righe in
// `listini_righe_componenti`).

// Dialog variazione percentuale massa
const showVariazioneDialog = ref(false)
// Disabilita dismissable del drawer quando il dialog e' aperto.
const hasChildOpen = computed(() => showVariazioneDialog.value)

function onVariazioneApplied() {
  store.fetchList()
}

const annullaForm = () => inline.chiudiConConferma(closeForm)
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <!-- ⚠️ Fino al 2026-10-03 la larghezza era `'1000px'`, scritta a mano e fuori
       dalla scala (analisi-fe-chrome-drawer §4 D-4). Dal modello e' il caso di
       `WIDE_PLUS`: master-detail con la sotto-tabella dei componenti BoM in
       expansion. -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.listini.tab_righe')"
    :icon="MANAGE_ICONS.RIGHE"
    :width="DRAWER_WIDTH.WIDE_PLUS"
    :dismissable="!hasChildOpen"
    :modificato="modificato"
    :conferma-uscita="inline.chiudiConConferma"
    :footer="formMode ? 'nessuno' : 'chiudi'"
    @update:visible="(v) => emit('update:visible', v)"
  >

    <!-- === Intestazione contesto versione === -->
    <div style="display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1rem; align-items: end;">
      <div class="form-grid-3col">
        <div class="form-field">
          <label>{{ t('vendite.listini.field_codice') }}</label>
          <span>{{ listinoCodice || '—' }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('vendite.listini.field_descrizione') }}</label>
          <span>{{ listinoDescrizione || '—' }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('vendite.listini.versione') }}</label>
          <span>{{ versione?.codice_versione || `#${versione?.id}` }}</span>
        </div>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.listini.col_stato') }}</label>
        <Tag :value="versione?.stato" :severity="statoVersioneListinoSeverity(versione?.stato)" />
      </div>
    </div>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.listini.field_valido_dal') }}</label>
        <span>{{ displayDate(versione?.valido_dal) }}</span>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.listini.field_valido_al') }}</label>
        <span>{{ displayDate(versione?.valido_al) || '—' }}</span>
      </div>
    </div>

    <!-- === MASTER: toolbar + lista configurabile (server-side lazy) === -->
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText v-model="searchText" class="app-filter-w-lg"
            :placeholder="t('vendite.listini.righe_cerca_articolo')" />
        </template>
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <!-- Lista unificata (UNION BE): righe standalone + compositi nello
         stesso flusso paginato. Distinzione visiva via Tag "Composito" +
         colonne adattive (UoM/prezzo vuoti sui compositi, badge N
         componenti al posto del prezzo). Click riga discrimina: composito
         apre `ComponentiDialog`, standalone apre form edit inline. -->
    <ListaConfigurabile
      ref="listaRef"
      codice="vendite.listini_righe"
      data-key="row_key"
      :riga-attiva="rigaInModifica?.row_key ?? null"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      @config-loaded="onConfigLoaded"
    >
      <template #cell-articolo_codice="{ data }">
        <span>{{ data.articolo_codice }}</span>
        <Tag v-if="data.is_composito"
          :value="t('vendite.listini.tag_composito')"
          severity="info"
          style="margin-left: 0.4rem; font-size: 0.7rem;" />
      </template>
      <template #cell-uom="{ data }">
        {{ data.uom_codice || '—' }}
      </template>
      <template #cell-prezzo="{ data }">
        <span v-if="data.is_composito" style="color: var(--app-text-muted); font-style: italic;">
          {{ t('vendite.listini.composito_n_componenti', { n: data.n_componenti_bundle }) }}
        </span>
        <span v-else>{{ formatPrezzoListino(data.prezzo) }}</span>
      </template>
      <template #cell-iva_aliquota="{ data }">
        {{ formatIvaLabel(data) }}
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>

      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRigaActions(data)" />
      </template>
    </ListaConfigurabile>

    <!-- === DETAIL: form inserimento/modifica (inline, sotto la tabella) === -->
    <template v-if="formMode">
      <div :ref="ancoraForm" class="app-drawer-section">
        <h4>{{ formTitle }}</h4>
      </div>

      <div class="form-field">
        <label>{{ t('vendite.listini.field_articolo') }} *</label>
        <ArticoloLookup
          v-model="form.articolo_obj"
          @update:modelValue="onArticoloSelected"
          :disabled="formMode === 'edit'"
          documento="LISTINO_VERSIONE"
          :documento-id="versione.id"
          :motivi-selezionabili="['COMPOSITO_COME_BUNDLE']"
        />
        <!-- Il composito il DB lo da' col motivo COMPOSITO_COME_BUNDLE: come riga
             semplice non entra, ma si sceglie lo stesso perche' qui ha la sua
             strada, il dialog dei prezzi bundle (`onArticoloSelected`). -->
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.listini.field_uom') }} *</label>
          <Select v-model="form.uom_id"
            :options="uomOptions"
            option-value="uom_id"
            :option-label="uomLabel"
            :placeholder="form.articolo_id ? t('catalogo.select_uom') : t('vendite.listini.uom_select_articolo_first')"
            :disabled="!form.articolo_id || uomLoading"
            :loading="uomLoading"
            :empty-message="t('vendite.listini.uom_no_operative')"
            :invalid="campiErrati.includes('uom_id')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.listini.field_prezzo') }} *</label>
          <InputNumber v-model="form.prezzo"
            :minFractionDigits="2" :maxFractionDigits="10"
            :invalid="campiErrati.includes('prezzo')"
          />
        </div>
      </div>

      <FormFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="annullaForm" />
    </template>

    <ApplicaVariazioneDialog
      :visible="showVariazioneDialog"
      @update:visible="v => showVariazioneDialog = v"
      :listino-id="listinoId"
      :versione-id="versione?.id"
      @applied="onVariazioneApplied" />

    <!-- Dialog bundle componenti BoM (modello unificato 2026-05-13).
         Riusa `ComponentiDialog` building block con prop:
           - `apiPreview` puntato a `bundleApiPreview` (chiusa col listinoId)
           - `showPrezzoSuggerito=false` (no resolver lato listino)
           - `i18nPrefix='vendite.componenti.bundle'` (titoli/hint dedicati)
         Apertura: auto al lookup composito o click "Modifica" su row. -->
    <ComponentiDialog
      v-if="bundleDialogVisible && bundlePadreCorrente"
      v-model:visible="bundleDialogVisible"
      :articolo="bundlePadreCorrente"
      :documento-id="versione?.id"
      :uom-operativa-id="1"
      :quantita="1"
      :api-preview="bundleApiPreview"
      :show-prezzo-suggerito="false"
      :emit-all-prices="true"
      i18n-prefix="vendite.componenti.bundle"
      @confirm="onBundleConfirm"
    />
  </AppDrawer>
</template>
