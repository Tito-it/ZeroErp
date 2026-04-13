<script setup>
// Scopo: Sub-drawer dettaglio versione listino con righe prezzo.
// Righe paginata server-side con filtri (search articolo, billing account, utility).
// Aggiunta riga: select UoM dipendente dall'articolo selezionato — caricato
// dinamicamente da catalogo.articoli_uom_operativa, con pre-selezione della
// UoM base se presente. Evita di proporre UoM incompatibili con l'articolo.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { displayDate } from '../../core/utils/date'
import { statoVersioneListinoSeverity } from '../../core/utils/severity'
import { createRiga, deleteRiga } from '../api/listini'
import { listArticoloUom } from '../../catalogo/api/catalogo'
import { useListiniRigheStore } from '../stores/listiniRighe'
import { DRAWER_WIDTH } from '../../core/constants'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import NewButton from '../../core/components/NewButton.vue'
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
const { execute, loading: actionLoading } = useApiHandler()
const isReadonly = useInjectReadonly()
const store = useListiniRigheStore()

const props = defineProps({
  visible: Boolean,
  listinoId: { type: [Number, null], required: true },
  listinoDescrizione: { type: String, default: '' },
  versione: { type: Object, required: true }
})
const emit = defineEmits(['update:visible'])

// Filtri locali per BA (oggetto completo da autocomplete) e utility (id numerico).
const filterBa = ref(null)
const filterUtility = ref(null)

const { searchText, onPage, onSort, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'articolo_codice',
  defaultSortOrder: 'asc',
  extraFilters: () => ({
    billing_account_id: filterBa.value?.id ?? null,
    utility_id: filterUtility.value ?? null
  })
})

const adding = ref(false)
const addForm = ref({})

// UoM operative dell'articolo corrente del form add.
const uomOptions = ref([])
const uomLoading = ref(false)

// Watch apertura/chiusura drawer e cambio versione: configura contesto store.
watch(
  () => [props.visible, props.versione?.id],
  ([v, vid]) => {
    if (v && vid) {
      store.setContext(props.listinoId, vid)
      searchText.value = ''
      filterBa.value = null
      filterUtility.value = null
      store.fetchList()
    } else {
      store.clearContext()
    }
  },
  { immediate: true },
)

function startAdd() {
  adding.value = true
  addForm.value = { articolo_obj: null, uom_id: null, prezzo: null }
  uomOptions.value = []
}

// Quando l'utente seleziona un articolo: carica le UoM operative compatibili
// e pre-seleziona quella base. Se l'articolo viene deselezionato, azzera tutto.
async function onArticoloSelect(articolo) {
  addForm.value.uom_id = null
  uomOptions.value = []
  if (!articolo?.id) return
  uomLoading.value = true
  try {
    const res = await listArticoloUom(articolo.id)
    const list = res.data.data.results || res.data.data || []
    uomOptions.value = list
    const base = list.find(u => u.is_base)
    if (base) {
      addForm.value.uom_id = base.uom_id
    } else if (list.length === 1) {
      addForm.value.uom_id = list[0].uom_id
    }
  } catch {
    uomOptions.value = []
  } finally {
    uomLoading.value = false
  }
}

async function confirmAdd() {
  const payload = {
    articolo_id: addForm.value.articolo_obj?.id,
    uom_id: addForm.value.uom_id,
    prezzo: addForm.value.prezzo,
  }
  await execute(() => createRiga(props.listinoId, props.versione.id, payload), { successMessage: t('listini.riga_creata') })
  adding.value = false
  await store.fetchList()
}

async function removeRow(row) {
  await execute(() => deleteRiga(props.listinoId, props.versione.id, row.id), { successMessage: t('listini.riga_eliminata') })
  await store.fetchList()
}

const isBozza = computed(() => props.versione?.stato === 'BOZZA')

const showVariazioneDialog = ref(false)

function onVariazioneApplied() {
  store.fetchList()
}

function onFilterBaChange(val) {
  filterBa.value = val
  store.filters.billing_account_id = val?.id ?? null
  store.filters.offset = 0
  store.fetchList()
}

function onFilterBaClear() {
  filterBa.value = null
  store.filters.billing_account_id = null
  store.filters.offset = 0
  store.fetchList()
}

function onFilterUtilityChange(val) {
  filterUtility.value = val
  store.filters.utility_id = val ?? null
  store.filters.offset = 0
  store.fetchList()
}

// Etichetta UoM nel dropdown: "codice - descrizione (BASE)" se base.
function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('listini.uom_base_suffix')}` : ''
  return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE }" :dismissable="true">
    <template #header>
      <DrawerTitle :action="versione?.codice_versione || `#${versione?.id}`"
        :title="`${t('listini.tab_righe')} — ${listinoDescrizione}`" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-row-inline" style="align-items: center;">
        <span class="form-field" style="flex: 0 0 auto;">
          <label>{{ t('listini.field_valido_dal') }}</label>
          <span>{{ displayDate(versione?.valido_dal) }}</span>
        </span>
        <span class="form-field" style="flex: 0 0 auto;">
          <label>{{ t('listini.field_valido_al') }}</label>
          <span>{{ displayDate(versione?.valido_al) || '—' }}</span>
        </span>
        <span style="margin-left: auto;">
          <Tag :value="versione?.stato" :severity="statoVersioneListinoSeverity(versione?.stato)" />
        </span>
      </div>

      <!-- Form aggiunta riga -->
      <template v-if="adding">
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('listini.field_articolo') }} *</label>
            <ArticoloLookup v-model="addForm.articolo_obj" @select="onArticoloSelect" />
          </div>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_uom') }} *</label>
            <Select v-model="addForm.uom_id"
              :options="uomOptions"
              option-value="uom_id"
              :option-label="uomLabel"
              :placeholder="addForm.articolo_obj?.id ? t('catalogo.select_uom') : t('listini.uom_select_articolo_first')"
              :disabled="!addForm.articolo_obj?.id || uomLoading"
              :loading="uomLoading"
              :empty-message="t('listini.uom_no_operative')" />
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_prezzo') }} *</label>
            <InputNumber v-model="addForm.prezzo" :minFractionDigits="2" :maxFractionDigits="10" />
          </div>
        </div>
        <DrawerFooter :loading="actionLoading"
          :disabled="!addForm.articolo_obj?.id || !addForm.uom_id || addForm.prezzo == null"
          @save="confirmAdd" @cancel="adding = false" />
      </template>

      <!-- Toolbar standard: filtri a sinistra, azioni a destra -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="searchText" :placeholder="t('listini.righe_cerca_articolo')"
            style="width: 200px;" />
          <BillingAccountLookup :modelValue="filterBa"
            @select="onFilterBaChange" @clear="onFilterBaClear"
            :placeholder="t('listini.righe_filtra_ba')" style="width: 220px;" />
          <UtilityPerRuoloSelect :modelValue="filterUtility"
            @change="onFilterUtilityChange"
            :placeholder="t('listini.righe_filtra_utility')" :showClear="true" style="width: 180px;" />
        </div>
        <div v-if="isBozza && !adding" class="app-page-actions">
          <Button icon="pi pi-percentage" :label="t('listini.variazione_short')"
            v-tooltip.bottom="t('listini.variazione_pct_titolo')"
            class="app-page-action" @click="showVariazioneDialog = true" />
          <NewButton :tooltip="t('listini.aggiungi_prezzo_hint')" @click="startAdd" />
        </div>
      </div>

      <DataTable :value="store.items" :loading="store.loading" striped-rows class="app-datatable" data-key="id"
        lazy v-bind="paginatorProps" @page="onPage" @sort="onSort" removable-sort
        scrollable scrollHeight="flex">
        <Column field="articolo_codice" :header="t('listini.col_articolo')" sortable style="width: 130px;" />
        <Column field="articolo_descrizione" :header="t('catalogo.col_descrizione')" style="min-width: 180px;" />
        <Column field="uom_codice" :header="t('catalogo.col_uom')" style="width: 80px;" />
        <Column field="prezzo" :header="t('listini.col_prezzo')" sortable style="width: 130px;">
          <template #body="{ data }">{{ data.prezzo }}</template>
        </Column>
        <Column field="billing_account_codice" :header="t('listini.col_ba')" sortable style="width: 120px;" />
        <Column field="utility_descrizione" :header="t('listini.col_utility')" sortable style="width: 130px;" />
        <Column field="emittente_descrizione" :header="t('listini.col_emittente')" style="width: 150px;" />
        <Column v-if="isBozza" style="width: 50px;">
          <template #body="{ data }">
            <Button icon="pi pi-trash" text rounded size="small" class="app-delete-btn" @click="removeRow(data)" />
          </template>
        </Column>
      </DataTable>
    </div>

    <ApplicaVariazioneDialog
      :visible="showVariazioneDialog"
      @update:visible="v => showVariazioneDialog = v"
      :listino-id="listinoId"
      :versione-id="versione?.id"
      @applied="onVariazioneApplied" />
  </Drawer>
</template>
