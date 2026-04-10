<script setup>
// Scopo: Drawer autonomo gestione associazioni di un listino.
// Richiamabile da: ListinoDrawer o ListiniSearchTable (pulsante riga).
// Pattern formMode: null=lista, 'new'=aggiungi, 'edit'=modifica.
// Utility prima di BA (BA dipende dal contesto utility).
// Emittente: solo output nella lista, derivato dal contesto.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { listAssociazioni, createAssociazione, updateAssociazione, deleteAssociazione } from '../api/listini'
import { displayDate, toDateString, parseIsoDate } from '../../core/utils/date'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import LookupSelect from '../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()
const { defaults: paramDefaults, load: loadDefaults } = useParameterDefaults(['DEFAULT_UTILITY_ID'])

const props = defineProps({
  visible: { type: Boolean, default: false },
  listinoId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const rows = ref([])
const listLoading = ref(false)
const formMode = ref(null)
const editId = ref(null)
const form = ref({})

function defaultForm() {
  const defaultUtility = paramDefaults.value.DEFAULT_UTILITY_ID
    ? Number(paramDefaults.value.DEFAULT_UTILITY_ID)
    : null
  return {
    utility_id: defaultUtility,
    billing_account_id: null,
    billing_account_obj: null,
    valido_dal: new Date(),
    valido_al: null
  }
}

async function loadRows() {
  if (!props.listinoId) return
  listLoading.value = true
  try {
    const res = await listAssociazioni(props.listinoId)
    rows.value = res.data.data.results || []
  } catch { rows.value = [] }
  finally { listLoading.value = false }
}

watch(() => props.visible, async (v) => {
  if (!v) return
  formMode.value = null
  editId.value = null
  await loadDefaults()
  form.value = defaultForm()
  loadRows()
})

function onStartNew() {
  formMode.value = 'new'
  editId.value = null
  form.value = defaultForm()
}

function onStartEdit(row) {
  formMode.value = 'edit'
  editId.value = row.id
  form.value = {
    utility_id: row.utility_id || null,
    billing_account_id: row.billing_account_id || null,
    billing_account_obj: buildBaObjFromRow(row),
    valido_dal: parseIsoDate(row.valido_dal) || new Date(),
    valido_al: parseIsoDate(row.valido_al),
  }
}

// Scopo: Ricostruisce _obj del BA dai campi arricchiti di list_associazioni
// per evitare round-trip all'apertura del form in edit. Se billing_account_id
// e' null, l'autocomplete resta vuoto. I campi sono allineati al payload
// restituito da BillingAccountLookupView (search_lookup) per coerenza col dropdown.
function buildBaObjFromRow(row) {
  if (!row.billing_account_id) return null
  const display = [
    row.billing_account_ragione_sociale,
    row.billing_account_codice,
    row.billing_account_id_fiscale,
  ].filter(Boolean).join(' · ') || `#${row.billing_account_id}`
  return {
    id: row.billing_account_id,
    codice: row.billing_account_codice,
    ragione_sociale_completa: row.billing_account_ragione_sociale,
    id_fiscale: row.billing_account_id_fiscale,
    pdp: row.billing_account_pdp,
    utility_id: row.billing_account_utility_id,
    utility_codice: row.billing_account_utility_codice,
    parent_account_id: row.billing_account_parent_id,
    parent_codice: row.billing_account_parent_codice,
    _display: display,
  }
}

function onCancelForm() {
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
}

// Sempre salvabile: la backend valida i campi (valido_dal default a oggi se vuoto).
// Lo scope (utility/BA) puo' essere tutto NULL per "associazione globale".
const canSave = computed(() => true)

function onBaSelect(ba) {
  // Sincronizza id + obj quando l'utente seleziona un BA dall'autocomplete.
  form.value.billing_account_id = ba?.id || null
  form.value.billing_account_obj = ba
}

function onBaClear() {
  form.value.billing_account_id = null
  form.value.billing_account_obj = null
}

async function onSaveForm() {
  const f = form.value
  const payload = {
    utility_id: f.utility_id || null,
    billing_account_id: f.billing_account_id || null,
    valido_dal: toDateString(f.valido_dal) || toDateString(new Date()),
    valido_al: toDateString(f.valido_al),
  }

  if (formMode.value === 'edit' && editId.value) {
    const result = await execute(
      () => updateAssociazione(props.listinoId, editId.value, payload),
      { successMessage: t('listini.associazione_salvata') }
    )
    if (result === null) return
  } else {
    const result = await execute(
      () => createAssociazione(props.listinoId, payload),
      { successMessage: t('listini.associazione_creata') }
    )
    if (result === null) return
  }
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
  await loadRows()
  emit('saved')
}

async function onDelete(row) {
  const result = await execute(
    () => deleteAssociazione(props.listinoId, row.id),
    { successMessage: t('listini.associazione_eliminata') }
  )
  if (result !== null) {
    await loadRows()
    emit('saved')
  }
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="emit('update:visible', $event)"
    position="right" :style="{ width: DRAWER_WIDTH.COMPLEX }">
    <template #header>
      <DrawerTitle :action="t('common.edit')" :title="t('listini.tab_associazioni')" icon="pi pi-link" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="!listLoading && !formMode">
        <div v-if="rows.length === 0" class="app-empty-state">
          <i class="pi pi-link" />
          <p>{{ t('listini.nessuna_associazione') }}</p>
        </div>

        <DataTable v-else :value="rows" class="app-datatable" striped-rows data-key="id">
          <Column field="utility_descrizione" :header="t('listini.col_utility')" style="width: 140px;">
            <template #body="{ data }">{{ data.utility_descrizione || '—' }}</template>
          </Column>
          <Column field="billing_account_codice" :header="t('listini.col_ba')" style="width: 120px;">
            <template #body="{ data }">{{ data.billing_account_codice || '—' }}</template>
          </Column>
          <Column field="emittente_descrizione" :header="t('listini.col_emittente')" style="width: 160px;">
            <template #body="{ data }">{{ data.emittente_descrizione || '—' }}</template>
          </Column>
          <Column :header="t('listini.field_valido_dal')" style="width: 95px;">
            <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
          </Column>
          <Column :header="t('listini.field_valido_al')" style="width: 95px;">
            <template #body="{ data }">{{ displayDate(data.valido_al) || '—' }}</template>
          </Column>
          <Column v-if="!isReadonly" style="width: 80px;">
            <template #body="{ data }">
              <div class="flex gap-1">
                <Button icon="pi pi-pencil" text rounded size="small"
                  class="app-edit-btn" @click="onStartEdit(data)" />
                <Button icon="pi pi-trash" text rounded size="small"
                  class="app-delete-btn" @click="onDelete(data)" />
              </div>
            </template>
          </Column>
        </DataTable>

        <div v-if="!isReadonly" class="mt-05">
          <Button :label="t('listini.aggiungi_associazione')" icon="pi pi-plus"
            text size="small" class="app-action-btn" @click="onStartNew" />
        </div>
      </template>

      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formMode === 'edit' ? t('listini.modifica_associazione') : t('listini.nuova_associazione') }}</h4>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_utility') }}</label>
            <UtilityPerRuoloSelect v-model="form.utility_id"
              :placeholder="t('listini.select_utility')" show-clear />
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_ba') }}</label>
            <BillingAccountLookup
              :modelValue="form.billing_account_obj"
              :utility-id="form.utility_id"
              :placeholder="t('billing_account.select_ba')"
              @select="onBaSelect"
              @clear="onBaClear"
            />
          </div>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_valido_dal') }}</label>
            <DatePicker v-model="form.valido_dal" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_valido_al') }}</label>
            <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
          </div>
        </div>

        <DrawerFooter :loading="loading" :disabled="!canSave" @save="onSaveForm" @cancel="onCancelForm" />
      </template>
    </div>
  </Drawer>
</template>
