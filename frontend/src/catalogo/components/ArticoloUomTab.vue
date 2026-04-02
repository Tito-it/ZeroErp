<script setup>
// Scopo: Tab UoM operative dell'articolo con CRUD inline.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { listArticoloUom, createArticoloUom, updateArticoloUom, deleteArticoloUom } from '../api/catalogo'
import LookupSelect from '../../core/components/LookupSelect.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Tag from 'primevue/tag'

const props = defineProps({ articoloId: { type: [String, null], required: true } })
const { t } = useI18n()
const { execute, loading } = useApiHandler()

const rows = ref([])
const editingRow = ref(null)
const editForm = ref({})
const adding = ref(false)
const addForm = ref({})

async function loadRows() {
  if (!props.articoloId) return
  const res = await listArticoloUom(props.articoloId)
  rows.value = res.data.data.results ?? res.data.data ?? []
}

onMounted(loadRows)

function startAdd() {
  adding.value = true
  addForm.value = { uom_id: null, factor_to_base: 1, is_sell_uom: false, is_purchase_uom: false, is_logistic_uom: false }
}

async function confirmAdd() {
  await execute(() => createArticoloUom(props.articoloId, addForm.value), { successMessage: t('catalogo.uom_aggiunta') })
  adding.value = false
  await loadRows()
}

function startEdit(row) {
  editingRow.value = row.id
  editForm.value = { factor_to_base: row.factor_to_base, is_sell_uom: row.is_sell_uom, is_purchase_uom: row.is_purchase_uom, is_logistic_uom: row.is_logistic_uom }
}

async function confirmEdit(row) {
  await execute(() => updateArticoloUom(props.articoloId, row.id, editForm.value), { successMessage: t('catalogo.uom_salvata') })
  editingRow.value = null
  await loadRows()
}

async function removeRow(row) {
  await execute(() => deleteArticoloUom(props.articoloId, row.id), { successMessage: t('catalogo.uom_rimossa') })
  await loadRows()
}
</script>

<template>
  <div>
    <div style="display: flex; justify-content: flex-end; margin-bottom: 0.5rem;">
      <Button icon="pi pi-plus" :label="t('catalogo.aggiungi_uom')" size="small" @click="startAdd" :disabled="adding" />
    </div>

    <div v-if="adding" class="form-grid-2col" style="margin-bottom: 1rem; padding: 0.75rem; border: 1px solid var(--app-card-border); border-radius: 6px;">
      <div class="form-field">
        <label>{{ t('catalogo.field_uom') }}</label>
        <LookupSelect v-model="addForm.uom_id" rel="catalogo.unita_misura" :placeholder="t('catalogo.select_uom')" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_fattore') }}</label>
        <InputNumber v-model="addForm.factor_to_base" :minFractionDigits="1" :maxFractionDigits="6" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_vendita') }}</label>
        <ToggleSwitch v-model="addForm.is_sell_uom" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_acquisto') }}</label>
        <ToggleSwitch v-model="addForm.is_purchase_uom" />
      </div>
      <div style="display: flex; gap: 0.5rem; align-items: flex-end;">
        <Button icon="pi pi-check" size="small" @click="confirmAdd" :loading="loading" :disabled="!addForm.uom_id" />
        <Button icon="pi pi-times" size="small" severity="secondary" @click="adding = false" />
      </div>
    </div>

    <DataTable :value="rows" :loading="loading" striped-rows class="app-datatable" data-key="id">
      <Column field="uom_codice" :header="t('catalogo.col_uom')" style="width: 100px;" />
      <Column field="uom_descrizione" :header="t('catalogo.col_descrizione')" style="width: 160px;" />
      <Column field="factor_to_base" :header="t('catalogo.col_fattore')" style="width: 110px;">
        <template #body="{ data }">
          <InputNumber v-if="editingRow === data.id" v-model="editForm.factor_to_base" :minFractionDigits="1" :maxFractionDigits="6" />
          <span v-else>{{ data.factor_to_base }}</span>
        </template>
      </Column>
      <Column :header="t('catalogo.field_vendita')" style="width: 80px;">
        <template #body="{ data }">
          <ToggleSwitch v-if="editingRow === data.id" v-model="editForm.is_sell_uom" />
          <Tag v-else :value="data.is_sell_uom ? t('common.yes') : t('common.no')" :severity="data.is_sell_uom ? 'success' : 'secondary'" />
        </template>
      </Column>
      <Column :header="t('catalogo.field_acquisto')" style="width: 80px;">
        <template #body="{ data }">
          <ToggleSwitch v-if="editingRow === data.id" v-model="editForm.is_purchase_uom" />
          <Tag v-else :value="data.is_purchase_uom ? t('common.yes') : t('common.no')" :severity="data.is_purchase_uom ? 'success' : 'secondary'" />
        </template>
      </Column>
      <Column :header="t('catalogo.col_base')" style="width: 70px;">
        <template #body="{ data }">
          <Tag v-if="data.is_base" :value="t('common.yes')" severity="info" />
        </template>
      </Column>
      <Column style="width: 90px;">
        <template #body="{ data }">
          <div style="display: flex; gap: 0.25rem;">
            <Button v-if="editingRow === data.id" icon="pi pi-check" text rounded size="small" class="app-action-btn" @click="confirmEdit(data)" />
            <Button v-if="editingRow === data.id" icon="pi pi-times" text rounded size="small" @click="editingRow = null" />
            <Button v-if="editingRow !== data.id" icon="pi pi-pencil" text rounded size="small" class="app-action-btn" @click="startEdit(data)" />
            <Button v-if="editingRow !== data.id" icon="pi pi-trash" text rounded size="small" severity="danger" @click="removeRow(data)" />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</template>
