<script setup>
// Scopo: Sub-drawer per gestione distinta base (BoM) articolo.
// Pattern: formMode state machine (null=lista DataTable, 'new'=aggiungi, 'edit'=modifica).
// Edit mode: componente_id readonly, modificabili coeff_qta, date, flag.

import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import {
  listArticoloComponenti, createArticoloComponente,
  updateArticoloComponente, deleteArticoloComponente
} from '../api/catalogo'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import { displayDate, toDateString } from '../../core/utils/date'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const componentiList = ref([])
const listLoading = ref(false)
const formMode = ref(null)
const editId = ref(null)
const form = ref({})
const componenteObj = ref(null)

function defaultForm() {
  return {
    componente_id: null,
    coeff_qta: 1,
    partecipa_qta: true,
    obbligatorio: true,
    determina_qta_padre: false,
    valido_dal: null,
    valido_al: null,
  }
}

// Scopo: Converte stringa ISO date in Date object per DatePicker.
function parseDate(val) {
  if (!val) return null
  if (val instanceof Date) return val
  const d = new Date(val)
  return isNaN(d.getTime()) ? null : d
}

// Scopo: Carica lista componenti dell'articolo.
async function loadComponenti() {
  if (!props.articoloId) return
  listLoading.value = true
  try {
    const res = await listArticoloComponenti(props.articoloId)
    const payload = res.data?.data
    componentiList.value = payload?.results || payload || []
  } catch {
    componentiList.value = []
  } finally {
    listLoading.value = false
  }
}

watch(() => props.visible, (val) => {
  if (!val) return
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
  componenteObj.value = null
  loadComponenti()
})

function onStartNew() {
  formMode.value = 'new'
  editId.value = null
  form.value = defaultForm()
  componenteObj.value = null
}

function onStartEdit(row) {
  formMode.value = 'edit'
  editId.value = row.id
  componenteObj.value = { id: row.componente_id, codice: row.componente_codice, descrizione: row.componente_descrizione }
  form.value = {
    componente_id: row.componente_id,
    coeff_qta: row.coeff_qta ?? 1,
    partecipa_qta: row.partecipa_qta ?? true,
    obbligatorio: row.obbligatorio ?? true,
    determina_qta_padre: row.determina_qta_padre ?? false,
    valido_dal: parseDate(row.valido_dal),
    valido_al: parseDate(row.valido_al),
  }
}

function onCancelForm() {
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
  componenteObj.value = null
}

// Scopo: Callback quando l'utente seleziona un articolo dal lookup.
function onComponenteSelect(item) {
  componenteObj.value = item
  form.value.componente_id = item?.id || null
}

const canSaveForm = computed(() => {
  return form.value.componente_id != null && form.value.coeff_qta > 0
})

// Scopo: Salva componente (create o update). Ricarica lista e notifica il parent.
async function onSaveForm() {
  const payload = {
    coeff_qta: form.value.coeff_qta,
    partecipa_qta: form.value.partecipa_qta,
    obbligatorio: form.value.obbligatorio,
    determina_qta_padre: form.value.determina_qta_padre,
    valido_dal: toDateString(form.value.valido_dal),
    valido_al: toDateString(form.value.valido_al),
  }

  if (formMode.value === 'edit' && editId.value) {
    const result = await execute(
      () => updateArticoloComponente(props.articoloId, editId.value, payload),
      { successMessage: t('catalogo.componente_salvato') }
    )
    if (result === null) return
  } else {
    payload.componente_id = form.value.componente_id
    const result = await execute(
      () => createArticoloComponente(props.articoloId, payload),
      { successMessage: t('catalogo.componente_aggiunto') }
    )
    if (result === null) return
  }

  formMode.value = null
  editId.value = null
  form.value = defaultForm()
  componenteObj.value = null
  await loadComponenti()
  emit('saved')
}

// Scopo: Elimina componente. Ricarica lista e notifica il parent.
async function onDelete(row) {
  const result = await execute(
    () => deleteArticoloComponente(props.articoloId, row.id),
    { successMessage: t('catalogo.componente_eliminato') }
  )
  if (result !== null) {
    await loadComponenti()
    emit('saved')
  }
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
  >
    <template #header>
      <DrawerTitle :action="t('common.edit')" :title="t('catalogo.tab_bom')" icon="pi pi-sitemap" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="!listLoading && !formMode">
        <div v-if="componentiList.length === 0" class="app-empty-state">
          <i class="pi pi-sitemap" />
          <p>{{ t('catalogo.nessun_componente') }}</p>
        </div>

        <DataTable v-else :value="componentiList" class="app-datatable" striped-rows>
          <Column field="componente_codice" :header="t('catalogo.col_codice')" />
          <Column field="componente_descrizione" :header="t('catalogo.col_descrizione')" />
          <Column field="coeff_qta" :header="t('catalogo.col_coeff_qta')" style="width: 80px;" />
          <Column :header="t('catalogo.field_obbligatorio')" style="width: 60px;">
            <template #body="{ data }">
              <Tag :value="data.obbligatorio ? 'S' : 'N'" :severity="data.obbligatorio ? 'success' : 'secondary'" />
            </template>
          </Column>
          <Column :header="t('catalogo.field_valido_dal')" style="width: 100px;">
            <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
          </Column>
          <Column v-if="!isReadonly" style="width: 80px;">
            <template #body="{ data }">
              <div class="flex gap-1">
                <Button icon="pi pi-pencil" text rounded size="small"
                  class="app-action-btn" @click="onStartEdit(data)" />
                <Button icon="pi pi-trash" severity="danger"
                  text rounded size="small" @click="onDelete(data)" />
              </div>
            </template>
          </Column>
        </DataTable>

        <div v-if="!isReadonly" class="mt-05">
          <Button
            :label="t('catalogo.aggiungi_componente')"
            icon="pi pi-plus"
            text size="small"
            class="app-action-btn"
            @click="onStartNew"
          />
        </div>
      </template>

      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formMode === 'edit' ? t('catalogo.modifica_componente') : t('catalogo.nuovo_componente') }}</h4>
        </div>
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('catalogo.field_componente') }} *</label>
            <ArticoloLookup
              :model-value="componenteObj"
              :placeholder="t('catalogo.search_componente')"
              :disabled="formMode === 'edit'"
              @select="onComponenteSelect"
            />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_coeff_qta') }} *</label>
            <InputNumber v-model="form.coeff_qta" :min="0" :min-fraction-digits="2"
              :max-fraction-digits="6" class="w-full" />
          </div>
        </div>
        <div class="form-grid-2col mt-05">
          <div class="form-field">
            <label>{{ t('catalogo.field_valido_dal') }}</label>
            <DatePicker v-model="form.valido_dal" :date-format="DATE_FORMAT"
              show-icon show-button-bar class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_valido_al') }}</label>
            <DatePicker v-model="form.valido_al" :date-format="DATE_FORMAT"
              show-icon show-button-bar class="w-full" />
          </div>
        </div>
        <div class="form-grid-2col mt-05">
          <div class="form-field">
            <label>{{ t('catalogo.field_obbligatorio') }}</label>
            <ToggleSwitch v-model="form.obbligatorio" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_partecipa_qta') }}</label>
            <ToggleSwitch v-model="form.partecipa_qta" />
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
