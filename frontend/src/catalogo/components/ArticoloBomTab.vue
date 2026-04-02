<script setup>
// Scopo: Tab distinta base (BoM) dell'articolo con CRUD inline.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { listArticoloComponenti, createArticoloComponente, deleteArticoloComponente } from '../api/catalogo'
import { displayDate } from '../../core/utils/date'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import { DATE_FORMAT } from '../../core/constants'
import { toDateString } from '../../core/utils/date'

const props = defineProps({ articoloId: { type: [String, null], required: true } })
const { t } = useI18n()
const { execute, loading } = useApiHandler()

const rows = ref([])
const adding = ref(false)
const addForm = ref({})

async function loadRows() {
  if (!props.articoloId) return
  const res = await listArticoloComponenti(props.articoloId)
  rows.value = res.data.data.results ?? res.data.data ?? []
}

onMounted(loadRows)

function startAdd() {
  adding.value = true
  addForm.value = { componente_obj: null, coeff_qta: 1, partecipa_qta: true, obbligatorio: true, determina_qta_padre: false, valido_dal: null }
}

async function confirmAdd() {
  const payload = {
    componente_id: addForm.value.componente_obj?.id,
    coeff_qta: addForm.value.coeff_qta,
    partecipa_qta: addForm.value.partecipa_qta,
    obbligatorio: addForm.value.obbligatorio,
    determina_qta_padre: addForm.value.determina_qta_padre,
    valido_dal: addForm.value.valido_dal ? toDateString(addForm.value.valido_dal) : toDateString(new Date())
  }
  await execute(() => createArticoloComponente(props.articoloId, payload), { successMessage: t('catalogo.componente_aggiunto') })
  adding.value = false
  await loadRows()
}

async function removeRow(row) {
  await execute(() => deleteArticoloComponente(props.articoloId, row.id), { successMessage: t('catalogo.componente_rimosso') })
  await loadRows()
}
</script>

<template>
  <div>
    <div style="display: flex; justify-content: flex-end; margin-bottom: 0.5rem;">
      <Button icon="pi pi-plus" :label="t('catalogo.aggiungi_componente')" size="small" @click="startAdd" :disabled="adding" />
    </div>

    <div v-if="adding" class="form-grid-2col" style="margin-bottom: 1rem; padding: 0.75rem; border: 1px solid var(--app-card-border); border-radius: 6px;">
      <div class="form-field" style="grid-column: span 2;">
        <label>{{ t('catalogo.field_componente') }}</label>
        <ArticoloLookup v-model="addForm.componente_obj" :placeholder="t('catalogo.search_componente')" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_coeff_qta') }}</label>
        <InputNumber v-model="addForm.coeff_qta" :minFractionDigits="1" :maxFractionDigits="6" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_valido_dal') }}</label>
        <DatePicker v-model="addForm.valido_dal" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_obbligatorio') }}</label>
        <ToggleSwitch v-model="addForm.obbligatorio" />
      </div>
      <div style="display: flex; gap: 0.5rem; align-items: flex-end;">
        <Button icon="pi pi-check" size="small" @click="confirmAdd" :loading="loading" :disabled="!addForm.componente_obj?.id" />
        <Button icon="pi pi-times" size="small" severity="secondary" @click="adding = false" />
      </div>
    </div>

    <DataTable :value="rows" :loading="loading" striped-rows class="app-datatable" data-key="id">
      <Column field="componente_codice" :header="t('catalogo.col_codice')" style="width: 130px;" />
      <Column field="componente_descrizione" :header="t('catalogo.col_descrizione')" style="min-width: 180px;" />
      <Column field="coeff_qta" :header="t('catalogo.col_coeff_qta')" style="width: 100px;" />
      <Column field="obbligatorio" :header="t('catalogo.field_obbligatorio')" style="width: 100px;">
        <template #body="{ data }">{{ data.obbligatorio ? t('common.yes') : t('common.no') }}</template>
      </Column>
      <Column field="valido_dal" :header="t('catalogo.field_valido_dal')" style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
      </Column>
      <Column field="valido_al" :header="t('catalogo.field_valido_al')" style="width: 110px;">
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
