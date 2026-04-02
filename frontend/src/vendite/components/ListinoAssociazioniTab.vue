<script setup>
// Scopo: Tab associazioni listino con CRUD inline.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { listAssociazioni, createAssociazione, deleteAssociazione } from '../api/listini'
import { displayDate } from '../../core/utils/date'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import { DATE_FORMAT } from '../../core/constants'
import { toDateString } from '../../core/utils/date'

const props = defineProps({ listinoId: { type: [Number, null], required: true } })
const { t } = useI18n()
const { execute, loading } = useApiHandler()

const rows = ref([])
const adding = ref(false)
const addForm = ref({})

async function loadRows() {
  if (!props.listinoId) return
  const res = await listAssociazioni(props.listinoId)
  rows.value = res.data.data.results ?? res.data.data ?? []
}

onMounted(loadRows)

function startAdd() {
  adding.value = true
  addForm.value = { priorita: 0, valido_dal: null, valido_al: null }
}

async function confirmAdd() {
  const payload = {
    priorita: addForm.value.priorita,
    valido_dal: addForm.value.valido_dal ? toDateString(addForm.value.valido_dal) : null,
    valido_al: addForm.value.valido_al ? toDateString(addForm.value.valido_al) : null,
  }
  await execute(() => createAssociazione(props.listinoId, payload), { successMessage: t('listini.associazione_creata') })
  adding.value = false
  await loadRows()
}

async function removeRow(row) {
  await execute(() => deleteAssociazione(props.listinoId, row.id), { successMessage: t('listini.associazione_eliminata') })
  await loadRows()
}
</script>

<template>
  <div>
    <div style="display: flex; justify-content: flex-end; margin-bottom: 0.5rem;">
      <Button icon="pi pi-plus" :label="t('listini.aggiungi_associazione')" size="small" @click="startAdd" :disabled="adding" />
    </div>

    <div v-if="adding" class="form-grid-2col" style="margin-bottom: 1rem; padding: 0.75rem; border: 1px solid var(--app-card-border); border-radius: 6px;">
      <div class="form-field">
        <label>{{ t('listini.field_priorita') }}</label>
        <InputNumber v-model="addForm.priorita" />
      </div>
      <div class="form-field">
        <label>{{ t('listini.field_valido_dal') }}</label>
        <DatePicker v-model="addForm.valido_dal" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
      </div>
      <div class="form-field">
        <label>{{ t('listini.field_valido_al') }}</label>
        <DatePicker v-model="addForm.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
      </div>
      <div style="display: flex; gap: 0.5rem; align-items: flex-end;">
        <Button icon="pi pi-check" size="small" @click="confirmAdd" :loading="loading" />
        <Button icon="pi pi-times" size="small" severity="secondary" @click="adding = false" />
      </div>
    </div>

    <DataTable :value="rows" :loading="loading" striped-rows class="app-datatable" data-key="id">
      <Column field="billing_account_codice" :header="t('listini.col_ba')" style="width: 130px;" />
      <Column field="utility_descrizione" :header="t('listini.col_utility')" style="width: 150px;" />
      <Column field="emittente_descrizione" :header="t('listini.col_emittente')" style="width: 180px;" />
      <Column field="priorita" :header="t('listini.col_priorita')" style="width: 90px;" />
      <Column field="valido_dal" :header="t('listini.field_valido_dal')" style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
      </Column>
      <Column field="valido_al" :header="t('listini.field_valido_al')" style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.valido_al) }}</template>
      </Column>
      <Column style="width: 50px;">
        <template #body="{ data }">
          <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="removeRow(data)" />
        </template>
      </Column>
    </DataTable>
  </div>
</template>
