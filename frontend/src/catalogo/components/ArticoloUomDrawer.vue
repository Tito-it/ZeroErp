<script setup>
// Scopo: Sub-drawer per gestione UoM operative articolo.
// Pattern: formMode state machine (null=lista DataTable, 'new'=aggiungi, 'edit'=modifica).
// Campi completi: is_base, factor_to_base, flags vendita/acquisto/logistica,
// qty_step, max_decimals, rounding_mode, forbid_fraction, require_lot, gtin,
// valido_dal/al, attivo.

import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { listArticoloUom, createArticoloUom, updateArticoloUom, deleteArticoloUom } from '../api/catalogo'
import { toDateString } from '../../core/utils/date'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import LookupSelect from '../../core/components/LookupSelect.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const uomList = ref([])
const listLoading = ref(false)
const formMode = ref(null)
const editId = ref(null)
const form = ref({})

const roundingOptions = [
  { value: 'HALF_UP', label: 'HALF_UP' },
  { value: 'HALF_DOWN', label: 'HALF_DOWN' },
  { value: 'HALF_EVEN', label: 'HALF_EVEN' },
  { value: 'UP', label: 'UP' },
  { value: 'DOWN', label: 'DOWN' }
]

function defaultForm() {
  return {
    uom_id: null,
    is_base: false,
    factor_to_base: 1,
    is_sell_uom: false,
    is_purchase_uom: false,
    is_logistic_uom: false,
    qty_step: 1,
    rounding_mode: 'HALF_UP',
    max_decimals: 6,
    forbid_fraction: false,
    require_lot: false,
    gtin: '',
    valido_dal: null,
    valido_al: null,
    attivo: true,
  }
}

// Scopo: Sincronizza is_base con factor_to_base.
//        factor=1 → base=true, factor≠1 → base=false.
watch(() => form.value.factor_to_base, (val) => {
  form.value.is_base = val === 1
})

// Scopo: Carica lista UoM operative dell'articolo.
async function loadUom() {
  if (!props.articoloId) return
  listLoading.value = true
  try {
    const res = await listArticoloUom(props.articoloId)
    const payload = res.data?.data
    uomList.value = payload?.results || payload || []
  } catch {
    uomList.value = []
  } finally {
    listLoading.value = false
  }
}

// Scopo: Verifica se esiste gia' una UoM base nella lista.
const hasBase = computed(() => uomList.value.some(u => u.is_base))

watch(() => props.visible, (val) => {
  if (!val) return
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
  loadUom()
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
    uom_id: row.uom_id,
    is_base: row.is_base || false,
    factor_to_base: row.factor_to_base ?? 1,
    is_sell_uom: row.is_sell_uom || false,
    is_purchase_uom: row.is_purchase_uom || false,
    is_logistic_uom: row.is_logistic_uom || false,
    qty_step: row.qty_step ?? 1,
    rounding_mode: row.rounding_mode || 'HALF_UP',
    max_decimals: row.max_decimals ?? 6,
    forbid_fraction: row.forbid_fraction || false,
    require_lot: row.require_lot || false,
    gtin: row.gtin || '',
    valido_dal: row.valido_dal ? new Date(row.valido_dal + 'T00:00:00') : null,
    valido_al: row.valido_al ? new Date(row.valido_al + 'T00:00:00') : null,
    attivo: row.attivo ?? true,
  }
}

function onCancelForm() {
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
}

const canSaveForm = computed(() => {
  return form.value.uom_id != null && form.value.factor_to_base > 0
})

// Scopo: Salva UoM operativa (create o update). Ricarica lista e notifica il parent.
async function onSaveForm() {
  const f = form.value
  const payload = {
    is_base: f.is_base,
    factor_to_base: f.factor_to_base,
    is_sell_uom: f.is_sell_uom,
    is_purchase_uom: f.is_purchase_uom,
    is_logistic_uom: f.is_logistic_uom,
    qty_step: f.qty_step,
    rounding_mode: f.rounding_mode,
    max_decimals: f.max_decimals,
    forbid_fraction: f.forbid_fraction,
    require_lot: f.require_lot,
    gtin: f.gtin?.trim() || null,
    valido_dal: toDateString(f.valido_dal),
    valido_al: toDateString(f.valido_al),
    attivo: f.attivo,
  }

  if (formMode.value === 'edit' && editId.value) {
    const result = await execute(
      () => updateArticoloUom(props.articoloId, editId.value, payload),
      { successMessage: t('catalogo.uom_salvata') }
    )
    if (result === null) return
  } else {
    payload.uom_id = f.uom_id
    const result = await execute(
      () => createArticoloUom(props.articoloId, payload),
      { successMessage: t('catalogo.uom_aggiunta') }
    )
    if (result === null) return
  }

  formMode.value = null
  editId.value = null
  form.value = defaultForm()
  await loadUom()
  emit('saved')
}

// Scopo: Elimina UoM operativa. Ricarica lista e notifica il parent.
async function onDelete(row) {
  const result = await execute(
    () => deleteArticoloUom(props.articoloId, row.id),
    { successMessage: t('catalogo.uom_eliminata') }
  )
  if (result !== null) {
    await loadUom()
    emit('saved')
  }
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
  >
    <template #header>
      <DrawerTitle :action="t('common.edit')" :title="t('catalogo.tab_uom')" icon="pi pi-box" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="!listLoading && !formMode">
        <div v-if="uomList.length === 0" class="app-empty-state">
          <i class="pi pi-box" />
          <p>{{ t('catalogo.nessuna_uom') }}</p>
        </div>

        <DataTable v-else :value="uomList" class="app-datatable" striped-rows>
          <Column field="uom_codice" :header="t('catalogo.col_codice')" style="width: 80px;" />
          <Column field="uom_descrizione" :header="t('catalogo.col_descrizione')" />
          <Column :header="t('catalogo.col_base')" style="width: 50px;">
            <template #body="{ data }">
              <Tag v-if="data.is_base" :value="t('catalogo.tag_base')" severity="info" />
            </template>
          </Column>
          <Column field="factor_to_base" :header="t('catalogo.col_fattore')" style="width: 70px;">
            <template #body="{ data }">
              <span class="font-mono">{{ data.factor_to_base }}</span>
            </template>
          </Column>
          <Column :header="t('catalogo.field_vendita')" style="width: 40px;">
            <template #body="{ data }">
              <Tag v-if="data.is_sell_uom" value="V" severity="success" />
            </template>
          </Column>
          <Column :header="t('catalogo.field_acquisto')" style="width: 40px;">
            <template #body="{ data }">
              <Tag v-if="data.is_purchase_uom" value="A" severity="success" />
            </template>
          </Column>
          <Column :header="t('catalogo.field_logistica')" style="width: 40px;">
            <template #body="{ data }">
              <Tag v-if="data.is_logistic_uom" value="L" severity="success" />
            </template>
          </Column>
          <Column :header="t('catalogo.col_attivo')" style="width: 50px;">
            <template #body="{ data }">
              <Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />
            </template>
          </Column>
          <Column v-if="!isReadonly" style="width: 80px;">
            <template #body="{ data }">
              <div class="flex gap-1">
                <Button icon="pi pi-pencil" text rounded size="small"
                  class="app-edit-btn" @click="onStartEdit(data)" />
                <Button v-if="!data.is_base" icon="pi pi-trash"
                  text rounded size="small" class="app-delete-btn" @click="onDelete(data)" />
              </div>
            </template>
          </Column>
        </DataTable>

        <div v-if="!isReadonly" class="mt-05">
          <Button
            :label="t('catalogo.aggiungi_uom')"
            icon="pi pi-plus"
            text size="small"
            class="app-action-btn"
            @click="onStartNew"
          />
        </div>
      </template>

      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formMode === 'edit' ? t('catalogo.modifica_uom_operativa') : t('catalogo.nuova_uom_operativa') }}</h4>
        </div>

        <!-- UoM + Base + Fattore -->
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('catalogo.field_uom') }} *</label>
            <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura"
              :placeholder="t('catalogo.select_uom')" :disabled="formMode === 'edit'" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('catalogo.col_base') }}</label>
            <ToggleSwitch v-model="form.is_base" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_fattore') }} *</label>
            <InputNumber v-model="form.factor_to_base" :min="0" :min-fraction-digits="2"
              :max-fraction-digits="6" class="w-full" :disabled="form.is_base" />
          </div>
        </div>

        <!-- Flags uso -->
        <div class="app-drawer-section"><h4>{{ t('catalogo.section_uso') }}</h4></div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('catalogo.field_vendita') }}</label>
            <ToggleSwitch v-model="form.is_sell_uom" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_acquisto') }}</label>
            <ToggleSwitch v-model="form.is_purchase_uom" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_logistica') }}</label>
            <ToggleSwitch v-model="form.is_logistic_uom" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_require_lot') }}</label>
            <ToggleSwitch v-model="form.require_lot" />
          </div>
        </div>

        <!-- Regole input -->
        <div class="app-drawer-section"><h4>{{ t('catalogo.section_regole_input') }}</h4></div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('catalogo.field_forbid_fraction') }}</label>
            <ToggleSwitch v-model="form.forbid_fraction" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_qty_step') }}</label>
            <InputNumber v-model="form.qty_step" :min="0.000001" :min-fraction-digits="0"
              :max-fraction-digits="6" class="w-full" :disabled="form.forbid_fraction" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_max_decimals') }}</label>
            <InputNumber v-model="form.max_decimals" :min="0" :max="6"
              class="w-full" :disabled="form.forbid_fraction" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_rounding_mode') }}</label>
            <Select v-model="form.rounding_mode" :options="roundingOptions"
              option-label="label" option-value="value" />
          </div>
        </div>

        <!-- GTIN + Validita' + Attivo -->
        <div class="app-drawer-section"><h4>{{ t('catalogo.section_extra') }}</h4></div>
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('catalogo.field_gtin') }}</label>
            <InputText v-model="form.gtin" />
          </div>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('catalogo.field_valido_dal') }}</label>
            <DatePicker v-model="form.valido_dal" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_valido_al') }}</label>
            <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
          </div>
        </div>
        <div v-if="formMode === 'edit'" class="form-grid">
          <div class="form-field">
            <label>{{ t('indirizzi.campo_attivo') }}</label>
            <ToggleSwitch v-model="form.attivo" />
          </div>
        </div>

        <DrawerFooter
          :loading="loading"
          :disabled="!canSaveForm"
          @save="onSaveForm"
          @cancel="onCancelForm"
        />
      </template>
    </div>
  </Drawer>
</template>

<style scoped>
.font-mono { font-family: monospace; }
.app-drawer-section {
  margin-top: 1rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--app-border-color, #e0e0e0);
}
.app-drawer-section h4 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
}
</style>
