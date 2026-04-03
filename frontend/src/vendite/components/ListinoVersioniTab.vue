<script setup>
// Scopo: Tab versioni del listino — lista con apertura VersioneDrawer.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { listVersioni, createVersione, changeVersioneStato } from '../api/listini'
import { displayDate, toDateString } from '../../core/utils/date'
import { statoVersioneListinoSeverity } from '../../core/utils/severity'
import VersioneDrawer from './VersioneDrawer.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import { DATE_FORMAT } from '../../core/constants'

const props = defineProps({ listinoId: { type: [Number, null], required: true } })
const { t } = useI18n()
const { execute, loading } = useApiHandler()

const rows = ref([])
const adding = ref(false)
const addForm = ref({})
const selectedVersione = ref(null)
const versioneDrawerVisible = ref(false)

async function loadRows() {
  if (!props.listinoId) return
  const res = await listVersioni(props.listinoId)
  rows.value = res.data.data.results ?? res.data.data ?? []
}

onMounted(loadRows)

function startAdd() {
  adding.value = true
  addForm.value = { codice_versione: '', valido_dal: null, valido_al: null, priorita: 0 }
}

async function confirmAdd() {
  const payload = {
    codice_versione: addForm.value.codice_versione?.trim() || null,
    valido_dal: addForm.value.valido_dal ? toDateString(addForm.value.valido_dal) : toDateString(new Date()),
    valido_al: addForm.value.valido_al ? toDateString(addForm.value.valido_al) : null,
    priorita: addForm.value.priorita,
  }
  await execute(() => createVersione(props.listinoId, payload), { successMessage: t('listini.versione_creata') })
  adding.value = false
  await loadRows()
}

async function onStato(row, nuovoStato) {
  await execute(
    () => changeVersioneStato(props.listinoId, row.id, { nuovo_stato: nuovoStato }),
    { successMessage: t('listini.stato_aggiornato') }
  )
  await loadRows()
}

function openVersione(row) {
  selectedVersione.value = row
  versioneDrawerVisible.value = true
}

function onVersioneClose() {
  versioneDrawerVisible.value = false
  selectedVersione.value = null
  loadRows()
}
</script>

<template>
  <div>
    <div style="display: flex; justify-content: flex-end; margin-bottom: 0.5rem;">
      <Button icon="pi pi-plus" :label="t('listini.aggiungi_versione')" size="small" @click="startAdd" :disabled="adding" />
    </div>

    <div v-if="adding" class="form-grid-2col" style="margin-bottom: 1rem; padding: 0.75rem; border: 1px solid var(--app-card-border); border-radius: 6px;">
      <div class="form-field">
        <label>{{ t('listini.field_codice_versione') }}</label>
        <InputText v-model="addForm.codice_versione" />
      </div>
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

    <DataTable :value="rows" :loading="loading" striped-rows class="app-datatable" data-key="id"
      @row-click="(e) => openVersione(e.data)" selection-mode="single">
      <Column field="stato" :header="t('listini.col_stato')" style="width: 100px;">
        <template #body="{ data }">
          <Tag :value="data.stato" :severity="statoVersioneListinoSeverity(data.stato)" />
        </template>
      </Column>
      <Column field="codice_versione" :header="t('listini.col_codice_versione')" style="width: 140px;" />
      <Column field="valido_dal" :header="t('listini.field_valido_dal')" style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
      </Column>
      <Column field="valido_al" :header="t('listini.field_valido_al')" style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.valido_al) || '—' }}</template>
      </Column>
      <Column field="priorita" :header="t('listini.col_priorita')" style="width: 80px;" />
      <Column field="righe_count" :header="t('listini.col_righe')" style="width: 80px;" />
      <Column :header="t('listini.col_azioni')" style="width: 120px;">
        <template #body="{ data }">
          <div style="display: flex; gap: 0.25rem;" @click.stop>
            <Button v-if="data.stato === 'BOZZA'" icon="pi pi-check-circle" text rounded size="small"
              class="app-action-btn" v-tooltip.top="t('listini.attiva')" @click="onStato(data, 'ATTIVA')" />
            <Button v-if="data.stato === 'ATTIVA'" icon="pi pi-lock" text rounded size="small"
              severity="warn" v-tooltip.top="t('listini.chiudi')" @click="onStato(data, 'CHIUSA')" />
          </div>
        </template>
      </Column>
    </DataTable>

    <VersioneDrawer v-if="selectedVersione"
      :visible="versioneDrawerVisible"
      @update:visible="v => { if (!v) onVersioneClose() }"
      :listino-id="props.listinoId"
      :versione="selectedVersione" />
  </div>
</template>
