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
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { displayDate } from '../../core/utils/date'
import { statoVersioneListinoSeverity, statoVersioneVisibile } from '../../core/utils/severity'
import { createRiga, updateRiga, deleteRiga } from '../api/listini'
import { listArticoloUom } from '../../catalogo/api/catalogo'
import { useListiniRigheStore } from '../stores/listiniRighe'
import { DRAWER_WIDTH } from '../../core/constants'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import NewButton from '../../core/components/NewButton.vue'
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
const uomOptions = ref([])
const uomLoading = ref(false)

function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('listini.uom_base_suffix')}` : ''
  return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
}

// Scopo: carica le UoM operative dell'articolo e pre-seleziona la base.
async function loadUomPerArticolo(articoloId) {
  uomOptions.value = []
  if (!articoloId) return
  uomLoading.value = true
  try {
    const res = await listArticoloUom(articoloId)
    const list = res.data.data?.results || res.data.data || []
    uomOptions.value = list
    if (formMode.value === 'create' && !form.value.uom_id) {
      const base = list.find(u => u.is_base)
      form.value.uom_id = base ? base.uom_id : (list.length === 1 ? list[0].uom_id : null)
    }
  } catch {
    uomOptions.value = []
  } finally {
    uomLoading.value = false
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
    }
  },
  { immediate: true },
)

const isBozza = computed(() => props.versione?.stato === 'BOZZA')

// === Azioni master ===
function onNew() {
  form.value = defaultForm()
  formMode.value = 'create'
  rigaEditId.value = null
  selectedRow.value = null
  uomOptions.value = []
}

function onRowSelect(event) {
  if (!isBozza.value) {
    // In versioni non BOZZA le righe sono sola lettura: non apriamo il form.
    selectedRow.value = null
    return
  }
  const r = event.data
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
  loadUomPerArticolo(r.articolo_id)
}

function onArticoloSelected(item) {
  form.value.articolo_id = item?.id || null
  form.value.uom_id = null
  loadUomPerArticolo(item?.id)
}

function closeForm() {
  formMode.value = null
  rigaEditId.value = null
  form.value = {}
  selectedRow.value = null
  uomOptions.value = []
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
    uom_id: f.uom_id,
    prezzo: f.prezzo,
  }
  if (formMode.value === 'create') {
    payload.articolo_id = f.articolo_id
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
function onDelete(row) {
  confirmDelete(row.articolo_codice || row.articolo_descrizione || `#${row.id}`, async () => {
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

// Scopo: azioni di riga — modifica + elimina, visibili solo in BOZZA e non readonly.
function buildRigaActions(row) {
  return [
    {
      key: 'modifica-riga',
      label: t('common.edit'),
      icon: 'pi pi-pencil',
      visible: isBozza.value && !isReadonly.value,
      allowWhenInactive: true,
      command: () => onRowSelect({ data: row }),
    },
    {
      key: 'elimina-riga',
      label: t('common.delete'),
      icon: 'pi pi-trash',
      severity: 'danger',
      visible: isBozza.value && !isReadonly.value,
      command: () => onDelete(row),
    },
  ]
}

// Dialog variazione percentuale massa
const showVariazioneDialog = ref(false)
// Disabilita dismissable del drawer quando il dialog e' aperto.
const hasChildOpen = computed(() => showVariazioneDialog.value)

function onVariazioneApplied() {
  store.fetchList()
}

function onClose() {
  emit('update:visible', false)
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE }" :dismissable="!hasChildOpen">
    <template #header>
      <DrawerTitle :action="versione?.codice_versione || `#${versione?.id}`"
        :title="`${t('listini.tab_righe')} — ${listinoDescrizione}`" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- === Intestazione contesto versione === -->
      <div style="text-align: right;" class="mb-2">
        <Tag :value="statoVersioneVisibile(versione)" :severity="statoVersioneListinoSeverity(statoVersioneVisibile(versione))" />
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
        <div v-if="isBozza" class="app-page-actions">
          <Button icon="pi pi-percentage" :label="t('listini.variazione_short')"
            v-tooltip.bottom="t('listini.variazione_pct_titolo')"
            class="app-page-action" @click="showVariazioneDialog = true" />
          <NewButton :tooltip="t('listini.aggiungi_prezzo_hint')"
            @click="onNew" :disabled="formMode === 'create' || isReadonly" />
        </div>
      </div>

      <DataTable :value="store.items" :loading="store.loading" striped-rows
        class="app-datatable" data-key="id"
        lazy v-bind="paginatorProps" @page="onPage" @sort="onSort" removable-sort
        v-model:selection="selectedRow" selection-mode="single" @row-select="onRowSelect">
        <Column field="articolo_codice" :header="t('listini.col_articolo')" sortable style="width: 120px;" />
        <Column field="articolo_descrizione" :header="t('catalogo.col_descrizione')" sortable style="min-width: 200px;" />
        <Column field="uom_codice" :header="t('catalogo.col_uom')" style="width: 70px;" />
        <Column field="prezzo" :header="t('listini.col_prezzo')" sortable style="width: 110px;">
          <template #body="{ data }">{{ data.prezzo }}</template>
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

      <DrawerFooter close-only @cancel="onClose" />
    </div>

    <ApplicaVariazioneDialog
      :visible="showVariazioneDialog"
      @update:visible="v => showVariazioneDialog = v"
      :listino-id="listinoId"
      :versione-id="versione?.id"
      @applied="onVariazioneApplied" />
  </Drawer>
</template>
