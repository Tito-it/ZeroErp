<script setup>
// Scopo: Sub-drawer per gestione UoM operative articolo.
// Pattern: formMode state machine (null=lista DataTable, 'new'=aggiungi, 'edit'=modifica).

import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { listArticoloUom, createArticoloUom, updateArticoloUom, deleteArticoloUom } from '../api/catalogo'
import { DRAWER_WIDTH } from '../../core/constants'
import LookupSelect from '../../core/components/LookupSelect.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'

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

function defaultForm() {
  return {
    uom_id: null,
    factor_to_base: 1,
    is_sell_uom: false,
    is_purchase_uom: false,
    is_logistic_uom: false,
  }
}

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
    factor_to_base: row.factor_to_base ?? 1,
    is_sell_uom: row.is_sell_uom || false,
    is_purchase_uom: row.is_purchase_uom || false,
    is_logistic_uom: row.is_logistic_uom || false,
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
  const payload = {
    factor_to_base: form.value.factor_to_base,
    is_sell_uom: form.value.is_sell_uom,
    is_purchase_uom: form.value.is_purchase_uom,
    is_logistic_uom: form.value.is_logistic_uom,
  }

  if (formMode.value === 'edit' && editId.value) {
    const result = await execute(
      () => updateArticoloUom(props.articoloId, editId.value, payload),
      { successMessage: t('catalogo.uom_salvata') }
    )
    if (result === null) return
  } else {
    payload.uom_id = form.value.uom_id
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
    :style="{ width: DRAWER_WIDTH.STANDARD }"
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
          <Column field="uom_codice" :header="t('catalogo.col_codice')" />
          <Column field="uom_descrizione" :header="t('catalogo.col_descrizione')" />
          <Column field="factor_to_base" :header="t('catalogo.col_fattore')" style="width: 80px;" />
          <Column :header="t('catalogo.field_vendita')" style="width: 60px;">
            <template #body="{ data }">
              <Tag :value="data.is_sell_uom ? 'V' : ''" :severity="data.is_sell_uom ? 'success' : 'secondary'" />
            </template>
          </Column>
          <Column :header="t('catalogo.field_acquisto')" style="width: 60px;">
            <template #body="{ data }">
              <Tag :value="data.is_purchase_uom ? 'A' : ''" :severity="data.is_purchase_uom ? 'success' : 'secondary'" />
            </template>
          </Column>
          <Column :header="t('catalogo.col_base')" style="width: 60px;">
            <template #body="{ data }">
              <Tag v-if="data.is_base" :value="t('catalogo.tag_base')" severity="info" />
            </template>
          </Column>
          <Column v-if="!isReadonly" style="width: 80px;">
            <template #body="{ data }">
              <div class="flex gap-1">
                <Button icon="pi pi-pencil" text rounded size="small"
                  class="app-action-btn" @click="onStartEdit(data)" />
                <Button v-if="!data.is_base" icon="pi pi-trash" severity="danger"
                  text rounded size="small" @click="onDelete(data)" />
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
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('catalogo.field_uom') }} *</label>
            <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura"
              :placeholder="t('catalogo.select_uom')" :disabled="formMode === 'edit'" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_fattore') }} *</label>
            <InputNumber v-model="form.factor_to_base" :min="0" :min-fraction-digits="2"
              :max-fraction-digits="10" class="w-full" />
          </div>
        </div>
        <div class="form-grid-2col mt-05">
          <div class="form-field">
            <label>{{ t('catalogo.field_vendita') }}</label>
            <ToggleSwitch v-model="form.is_sell_uom" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_acquisto') }}</label>
            <ToggleSwitch v-model="form.is_purchase_uom" />
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
