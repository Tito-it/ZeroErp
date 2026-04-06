<script setup>
// Scopo: Drawer autonomo gestione versioni di un listino.
// Richiamabile da: ListinoDrawer (tab) o ListiniSearchTable (pulsante riga).
// Pattern formMode: null=lista, 'new'=aggiungi. Click riga → apre VersioneDrawer (righe).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { listVersioni, createVersione, changeVersioneStato } from '../api/listini'
import { displayDate, toDateString } from '../../core/utils/date'
import { statoVersioneListinoSeverity } from '../../core/utils/severity'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import VersioneDrawer from './VersioneDrawer.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  listinoId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const rows = ref([])
const listLoading = ref(false)
const formMode = ref(null)
const form = ref({})

// Sub-drawer righe prezzo
const selectedVersione = ref(null)
const righeDrawerVisible = ref(false)

function defaultForm() {
  return { codice_versione: '', valido_dal: new Date(), valido_al: null, priorita: 100 }
}

async function loadRows() {
  if (!props.listinoId) return
  listLoading.value = true
  try {
    const res = await listVersioni(props.listinoId)
    rows.value = res.data.data.results || []
  } catch { rows.value = [] }
  finally { listLoading.value = false }
}

watch(() => props.visible, (v) => {
  if (!v) return
  formMode.value = null
  form.value = defaultForm()
  loadRows()
})

function onStartNew() {
  formMode.value = 'new'
  form.value = defaultForm()
}

function onCancelForm() {
  formMode.value = null
  form.value = defaultForm()
}

const canSave = computed(() => !!form.value.codice_versione?.trim() && !!form.value.valido_dal)

async function onSaveForm() {
  const payload = {
    codice_versione: form.value.codice_versione?.trim(),
    valido_dal: toDateString(form.value.valido_dal),
    valido_al: toDateString(form.value.valido_al),
    priorita: form.value.priorita,
  }
  const result = await execute(
    () => createVersione(props.listinoId, payload),
    { successMessage: t('listini.versione_creata') }
  )
  if (result === null) return
  formMode.value = null
  form.value = defaultForm()
  await loadRows()
  emit('saved')
}

async function onStato(row, nuovoStato) {
  await execute(
    () => changeVersioneStato(props.listinoId, row.id, { nuovo_stato: nuovoStato }),
    { successMessage: t('listini.stato_aggiornato') }
  )
  await loadRows()
  emit('saved')
}

function openRighe(row) {
  selectedVersione.value = row
  righeDrawerVisible.value = true
}

function onRigheClose() {
  righeDrawerVisible.value = false
  selectedVersione.value = null
  loadRows()
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="emit('update:visible', $event)"
    position="right" :style="{ width: DRAWER_WIDTH.COMPLEX }">
    <template #header>
      <DrawerTitle :action="t('common.edit')" :title="t('listini.tab_versioni')" icon="pi pi-history" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="!listLoading && !formMode">
        <div v-if="rows.length === 0" class="app-empty-state">
          <i class="pi pi-history" />
          <p>{{ t('listini.nessuna_versione') }}</p>
        </div>

        <DataTable v-else :value="rows" class="app-datatable" striped-rows data-key="id"
          @row-click="(e) => openRighe(e.data)" selection-mode="single">
          <Column :header="t('listini.col_stato')" style="width: 90px;">
            <template #body="{ data }">
              <Tag :value="data.stato" :severity="statoVersioneListinoSeverity(data.stato)" />
            </template>
          </Column>
          <Column field="codice_versione" :header="t('listini.col_codice_versione')" style="width: 130px;" />
          <Column :header="t('listini.field_valido_dal')" style="width: 100px;">
            <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
          </Column>
          <Column :header="t('listini.field_valido_al')" style="width: 100px;">
            <template #body="{ data }">{{ displayDate(data.valido_al) || '—' }}</template>
          </Column>
          <Column field="priorita" :header="t('listini.col_priorita')" style="width: 70px;" />
          <Column field="righe_count" :header="t('listini.col_righe')" style="width: 70px;" />
          <Column v-if="!isReadonly" style="width: 80px;">
            <template #body="{ data }">
              <div class="flex gap-1" @click.stop>
                <Button v-if="data.stato === 'BOZZA'" icon="pi pi-check-circle" text rounded size="small"
                  class="app-action-btn" v-tooltip.top="t('listini.attiva')" @click="onStato(data, 'ATTIVA')" />
                <Button v-if="data.stato === 'ATTIVA'" icon="pi pi-lock" text rounded size="small"
                  severity="warn" v-tooltip.top="t('listini.chiudi')" @click="onStato(data, 'CHIUSA')" />
              </div>
            </template>
          </Column>
        </DataTable>

        <div v-if="!isReadonly" class="mt-05">
          <Button :label="t('listini.aggiungi_versione')" icon="pi pi-plus"
            text size="small" class="app-action-btn" @click="onStartNew" />
        </div>
      </template>

      <template v-if="formMode">
        <div class="app-drawer-section"><h4>{{ t('listini.nuova_versione') }}</h4></div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_codice_versione') }} *</label>
            <InputText v-model="form.codice_versione" />
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_priorita') }}</label>
            <InputNumber v-model="form.priorita" :min="1" />
          </div>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_valido_dal') }} *</label>
            <DatePicker v-model="form.valido_dal" :dateFormat="DATE_FORMAT" showIcon />
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

  <VersioneDrawer v-if="selectedVersione"
    :visible="righeDrawerVisible"
    @update:visible="v => { if (!v) onRigheClose() }"
    :listino-id="props.listinoId"
    :versione="selectedVersione" />
</template>
