<script setup>
// Scopo: Sub-drawer dettaglio versione listino con righe prezzo — pattern
//        master-detail inline (frontend-standards §"Master-Detail inline").
//        Lista paginata server-side sopra, form dettaglio sotto.
//        Click riga = edit, pulsante Nuovo = create. Salva/Annulla sempre
//        in basso sotto il form. Articolo immutabile in edit.
//        Solo righe in versione BOZZA sono modificabili/eliminabili.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { displayDate } from '../../core/utils/date'
import { formatIvaLabel } from '../../core/utils/format'
import { statoVersioneListinoSeverity, statoVersioneVisibile } from '../../core/utils/severity'
import {
  createRiga,
  updateRiga,
  deleteRiga,
  listBundleCompositi,
  previewBundleComponenti,
  saveBundleComponenti,
  deleteBundleComponenti,
} from '../api/listini'
import ComponentiDialog from '../_shared/componenti/ComponentiDialog.vue'
import { useArticoloUomOptions } from '../../core/composables/useArticoloUomOptions'
import { useListiniRigheStore } from '../stores/listiniRighe'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import ApplicaVariazioneDialog from './ApplicaVariazioneDialog.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
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

const { searchText, onPage, onSort, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'articolo_descrizione',
  defaultSortOrder: 'asc',
})

// Stato master-detail inline
// formMode: null (nessun form visibile), 'create', 'edit'
const formMode = ref(null)
const rigaEditId = ref(null)
const form = ref({})
const selectedRow = ref(null)

// UoM operative dell'articolo selezionato (pattern ContrattoRigheDrawer).
// Composable centralizzato (Fase 4.F1): autopick base solo in create.
const {
  uomOptions, uomLoading, loadUomPerArticolo, pickBaseUomId, resetUomOptions,
} = useArticoloUomOptions()

function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('listini.uom_base_suffix')}` : ''
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
      loadBundleCompositi()
      closeForm()
    } else {
      store.clearContext()
      bundleCompositi.value = []
      bundleDialogVisible.value = false
      bundlePadreCorrente.value = null
    }
  },
  { immediate: true },
)

const isBozza = computed(() => props.versione?.stato === 'BOZZA')

// Scopo: ricarica righe standalone (store) + lista compositi in parallelo.
// Necessario perche' la sezione compositi non e' nel `store` paginato e
// quindi il F5 della DataTable da solo non la aggiorna.
async function reloadAll() {
  await Promise.all([store.fetchList(), loadBundleCompositi()])
}

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.refresh'),
    tooltip: t('common.refresh'),
    icon: 'pi pi-refresh',
    class: 'app-page-action',
    command: reloadAll,
  },
  {
    key: 'variazione',
    kind: 'utility',
    label: t('listini.variazione_short'),
    tooltip: t('listini.variazione_pct_titolo'),
    icon: 'pi pi-percentage',
    showLabel: true,
    class: 'app-page-action',
    visible: isBozza.value,
    command: () => { showVariazioneDialog.value = true },
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('listini.aggiungi_prezzo_hint'),
    icon: MANAGE_ICONS.ADD,
    visible: isBozza.value,
    disabled: formMode.value === 'create' || isReadonly.value,
    command: onNew,
  },
])

// === Azioni master ===
function onNew() {
  form.value = defaultForm()
  formMode.value = 'create'
  rigaEditId.value = null
  selectedRow.value = null
  resetUomOptions()
}

function onRowSelect(event) {
  const r = event.data
  // Riga composito (modello unificato): non c'e' un form editabile testata
  // riga — i prezzi vivono in `listini_righe_componenti` via Dialog.
  if (r?._isComposito) {
    selectedRow.value = null
    openBundleDialog({
      id: r.articolo_id,
      codice: r.articolo_codice,
      descrizione: r.articolo_descrizione,
      is_composito: true,
    })
    return
  }
  if (!isBozza.value) {
    // In versioni non BOZZA le righe standalone sono sola lettura.
    selectedRow.value = null
    return
  }
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
  formMode.value = 'edit'
  rigaEditId.value = r.id
  // Edit: UoM gia' nel form, no autopick.
  loadUomPerArticolo(r.articolo_id)
}

function onArticoloSelected(item) {
  // I padri compositi sono pre-filtrati dal lookup (filtri.compositi='escludi'):
  // `listini_righe` non li ammette (trigger DB `E_LISTINO_RIGA_COMPOSITO_VIETATO`).
  // I bundle prezzi si gestiscono dalla sezione "Prezzi compositi" in cima
  // alla lista, non da questo form.
  form.value.articolo_id = item?.id || null
  form.value.uom_id = null
  // Create: autopick base.
  caricaUomConPickBase(item?.id)
}

// ── Bundle compositi (modello unificato 2026-05-13) ──
// Lista articoli compositi con almeno 1 prezzo bundle definito + Dialog
// per editing. Refresh dopo ogni save bundle.
const bundleCompositi = ref([])
const bundleDialogVisible = ref(false)
// Padre composito corrente: oggetto { id, codice, descrizione,
// is_composito } passato come prop `articolo` al Dialog.
const bundlePadreCorrente = ref(null)
// Cache della preview corrente (lista BoM + prezzi gia' definiti) per
// poter risolvere il mapping {componente_id -> articolo_componente_id}
// al confirm della Dialog senza un secondo fetch.
let _bundlePreviewCache = []

async function loadBundleCompositi() {
  if (!props.listinoId || !props.versione?.id) return
  try {
    const res = await listBundleCompositi(props.listinoId, props.versione.id)
    bundleCompositi.value = res.data?.data ?? []
  } catch {
    bundleCompositi.value = []
  }
}

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
    { successMessage: t('listini.bundle_salvato') },
  )
  if (result !== null) {
    await loadBundleCompositi()
    bundleDialogVisible.value = false
    bundlePadreCorrente.value = null
  }
}

function closeForm() {
  formMode.value = null
  rigaEditId.value = null
  form.value = {}
  selectedRow.value = null
  resetUomOptions()
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
  if (formMode.value === 'create') return t('listini.nuova_riga')
  if (formMode.value === 'edit') return t('listini.modifica_riga')
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
      { successMessage: t('listini.riga_creata') }
    )
    if (result !== null) {
      await store.fetchList()
      closeForm()
    }
  } else {
    const result = await execute(
      () => updateRiga(props.listinoId, props.versione.id, rigaEditId.value, payload),
      { successMessage: t('listini.riga_salvata') }
    )
    if (result !== null) {
      await store.fetchList()
      closeForm()
    }
  }
}

// === Eliminazione riga (con conferma) ===
// Branching:
//   - Riga standalone (`_isComposito=false`): DELETE su `listini_righe`.
//   - Riga composito: DELETE dedicato su /bundle/<padre>/ → tabula rasa
//     idempotente lato BE (soft-delete tutte le righe
//     `listini_righe_componenti` del padre per la versione). Endpoint REST
//     semanticamente corretto sostituisce il vecchio workaround
//     `saveBundleComponenti(rows=[])`.
function onDelete(row) {
  const label = row.articolo_codice || row.articolo_descrizione || `#${row.id}`
  confirmDelete(label, async () => {
    if (row._isComposito) {
      const result = await execute(
        () => deleteBundleComponenti(
          props.listinoId, props.versione.id, row.articolo_id,
        ),
        { successMessage: t('listini.composito_eliminato') },
      )
      if (result !== null) {
        await loadBundleCompositi()
      }
      return
    }
    const result = await execute(
      () => deleteRiga(props.listinoId, props.versione.id, row.id),
      { successMessage: t('listini.riga_eliminata') },
    )
    if (result !== null) {
      // Se stavo editando questa riga, chiudi il form.
      if (rigaEditId.value === row.id) closeForm()
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

// Lista unificata righe standalone + righe composito (modello unificato
// BoM 2026-05-13). I compositi vanno in testa (layout fisso, no
// paginazione): pochi in genere, e l'admin li vede subito sopra alle
// righe standalone paginate. Marker `_isComposito: true` per
// discriminare nelle azioni / colonne / handler. NB: il `data-key` resta
// `id` per la DataTable, ma per i compositi non c'e' un `lrc.id` testata
// (sono N righe in `listini_righe_componenti`) → usiamo
// `composito:{articolo_id}` come chiave virtuale univoca.
const righeUnificate = computed(() => {
  const compositi = (bundleCompositi.value || []).map((c) => ({
    id: `composito:${c.articolo_id}`,
    _isComposito: true,
    articolo_id: c.articolo_id,
    articolo_codice: c.articolo_codice,
    articolo_descrizione: c.articolo_descrizione,
    uom_codice: null,
    uom_id: null,
    prezzo: null,
    iva_id: c.iva_id,
    iva_codice: c.iva_codice,
    iva_aliquota: c.iva_aliquota,
    n_componenti_bundle: c.n_componenti_bundle,
  }))
  const standalone = (store.items || []).map((r) => ({
    ...r,
    _isComposito: false,
  }))
  return [...compositi, ...standalone]
})

// Dialog variazione percentuale massa
const showVariazioneDialog = ref(false)
// Disabilita dismissable del drawer quando il dialog e' aperto.
const hasChildOpen = computed(() => showVariazioneDialog.value)

function onVariazioneApplied() {
  store.fetchList()
}

const onClose = useDrawerClose(emit)
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE }" :dismissable="!hasChildOpen">
    <template #header>
      <DrawerTitle :title="t('listini.tab_righe')" icon="pi pi-list" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- === Intestazione contesto versione === -->
      <div style="display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1rem; align-items: end;">
        <div class="form-grid-3col">
          <div class="form-field">
            <label>{{ t('listini.field_codice') }}</label>
            <span>{{ listinoCodice || '—' }}</span>
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_descrizione') }}</label>
            <span>{{ listinoDescrizione || '—' }}</span>
          </div>
          <div class="form-field">
            <label>{{ t('listini.versione') }}</label>
            <span>{{ versione?.codice_versione || `#${versione?.id}` }}</span>
          </div>
        </div>
        <div class="form-field">
          <label>{{ t('listini.col_stato') }}</label>
          <Tag :value="statoVersioneVisibile(versione)" :severity="statoVersioneListinoSeverity(statoVersioneVisibile(versione))" />
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('listini.field_valido_dal') }}</label>
          <span>{{ displayDate(versione?.valido_dal) }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('listini.field_valido_al') }}</label>
          <span>{{ displayDate(versione?.valido_al) || '—' }}</span>
        </div>
      </div>

      <!-- === MASTER: toolbar + lista paginata (server-side lazy) === -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="searchText" :placeholder="t('listini.righe_cerca_articolo')"
            style="width: 240px;" />
        </div>
        <PageActionsBar :actions="pageActions" />
      </div>

      <!-- Lista unificata: righe composito (modello unificato BoM
           2026-05-13) in testa (no paginazione) + righe standalone
           paginate. Distinzione visiva via Tag "Composito" + colonne
           adattive (UoM/prezzo vuoti sui compositi, badge N componenti
           al posto del prezzo). Click riga discrimina: composito apre
           `ComponentiDialog`, standalone apre form edit inline. -->
      <DataTable :value="righeUnificate" :loading="store.loading" striped-rows
        class="app-datatable" data-key="id"
        lazy v-bind="paginatorProps" @page="onPage" @sort="onSort" removable-sort
        v-model:selection="selectedRow" selection-mode="single" @row-select="onRowSelect">
        <Column field="articolo_codice" :header="t('listini.col_articolo')" sortable style="width: 160px;">
          <template #body="{ data }">
            <span>{{ data.articolo_codice }}</span>
            <Tag v-if="data._isComposito"
              :value="t('listini.tag_composito')"
              severity="info"
              style="margin-left: 0.4rem; font-size: 0.7rem;" />
          </template>
        </Column>
        <Column field="articolo_descrizione" :header="t('catalogo.col_descrizione')" sortable style="min-width: 200px;" />
        <Column field="uom_codice" :header="t('catalogo.col_uom')" style="width: 70px;">
          <template #body="{ data }">{{ data.uom_codice || '—' }}</template>
        </Column>
        <Column field="prezzo" :header="t('listini.col_prezzo')" sortable style="width: 140px;">
          <template #body="{ data }">
            <span v-if="data._isComposito" style="color: var(--app-text-muted); font-style: italic;">
              {{ t('listini.composito_n_componenti', { n: data.n_componenti_bundle }) }}
            </span>
            <span v-else>{{ data.prezzo }}</span>
          </template>
        </Column>
        <Column field="iva_aliquota" :header="t('listini.col_iva')" style="width: 70px;">
          <template #body="{ data }">{{ formatIvaLabel(data) }}</template>
        </Column>
        <Column v-if="isBozza" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
          <template #body="{ data }">
            <RowActionsMenu :row="data" :actions="buildRigaActions(data)" />
          </template>
        </Column>
      </DataTable>

      <!-- === DETAIL: form inserimento/modifica (inline, sotto la tabella) === -->
      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formTitle }}</h4>
        </div>

        <div class="form-field">
          <label>{{ t('listini.field_articolo') }} *</label>
          <ArticoloLookup
            v-model="form.articolo_obj"
            @update:modelValue="onArticoloSelected"
            :disabled="formMode === 'edit'"
            :filtri="{ soloComponenti: 'escludi', compositi: 'escludi' }"
          />
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_uom') }} *</label>
            <Select v-model="form.uom_id"
              :options="uomOptions"
              option-value="uom_id"
              :option-label="uomLabel"
              :placeholder="form.articolo_id ? t('catalogo.select_uom') : t('listini.uom_select_articolo_first')"
              :disabled="!form.articolo_id || uomLoading"
              :loading="uomLoading"
              :empty-message="t('listini.uom_no_operative')"
              class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_prezzo') }} *</label>
            <InputNumber v-model="form.prezzo" class="w-full"
              :minFractionDigits="2" :maxFractionDigits="10" />
          </div>
        </div>

        <div class="app-drawer-footer">
          <Button :label="t('common.cancel')" severity="secondary" @click="closeForm" />
          <Button :label="t('common.save')" :disabled="!canSave || loading" :loading="loading" @click="onSave" />
        </div>
      </template>

      <DrawerFooter v-if="!formMode" close-only @cancel="onClose" />
    </div>

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
  </Drawer>
</template>
