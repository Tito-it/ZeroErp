<script setup>
// Scopo: Sub-drawer dettaglio versione listino con tab righe prezzo.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { displayDate } from '../../core/utils/date'
import { statoVersioneListinoSeverity } from '../../core/utils/severity'
import { listRighe, createRiga, deleteRiga } from '../api/listini'
import { DRAWER_WIDTH } from '../../core/constants'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  listinoId: { type: [Number, null], required: true },
  versione: { type: Object, required: true }
})
const emit = defineEmits(['update:visible'])

const righe = ref([])
const adding = ref(false)
const addForm = ref({})

async function loadRighe() {
  if (!props.listinoId || !props.versione?.id) return
  const res = await listRighe(props.listinoId, props.versione.id)
  righe.value = res.data.data.results || []
}

watch(() => props.visible, (v) => {
  if (v) loadRighe()
})

function startAdd() {
  adding.value = true
  addForm.value = { articolo_obj: null, uom_id: null, prezzo: null }
}

async function confirmAdd() {
  const payload = {
    articolo_id: addForm.value.articolo_obj?.id,
    uom_id: addForm.value.uom_id,
    prezzo: addForm.value.prezzo,
  }
  await execute(() => createRiga(props.listinoId, props.versione.id, payload), { successMessage: t('listini.riga_creata') })
  adding.value = false
  await loadRighe()
}

async function removeRow(row) {
  await execute(() => deleteRiga(props.listinoId, props.versione.id, row.id), { successMessage: t('listini.riga_eliminata') })
  await loadRighe()
}

const isBozza = computed(() => props.versione?.stato === 'BOZZA')
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.COMPLEX }" :dismissable="true">
    <template #header>
      <DrawerTitle :action="t('listini.versione')" :title="versione?.codice_versione || `#${versione?.id}`" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('listini.col_stato') }}</label>
          <Tag :value="versione?.stato" :severity="statoVersioneListinoSeverity(versione?.stato)" />
        </div>
        <div class="form-field">
          <label>{{ t('listini.col_priorita') }}</label>
          <span>{{ versione?.priorita }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('listini.field_valido_dal') }}</label>
          <span>{{ displayDate(versione?.valido_dal) }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('listini.field_valido_al') }}</label>
          <span>{{ displayDate(versione?.valido_al) || '—' }}</span>
        </div>
      </div>

      <div class="app-drawer-section"><h4>{{ t('listini.tab_righe') }}</h4></div>

      <div v-if="isBozza && !adding" class="mt-05">
        <Button icon="pi pi-plus" :label="t('listini.aggiungi_riga')" text size="small"
          class="app-action-btn" @click="startAdd" />
      </div>

      <template v-if="adding">
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('listini.field_articolo') }} *</label>
            <ArticoloLookup v-model="addForm.articolo_obj" />
          </div>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_uom') }} *</label>
            <LookupSelect v-model="addForm.uom_id" rel="catalogo.unita_misura" :placeholder="t('catalogo.select_uom')" />
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_prezzo') }} *</label>
            <InputNumber v-model="addForm.prezzo" :minFractionDigits="2" :maxFractionDigits="10" />
          </div>
        </div>
      </template>
      <DrawerFooter v-if="adding" :loading="loading"
        :disabled="!addForm.articolo_obj?.id || !addForm.uom_id || addForm.prezzo == null"
        @save="confirmAdd" @cancel="adding = false" />

      <DataTable :value="righe" :loading="loading" striped-rows class="app-datatable" data-key="id">
        <Column field="articolo_codice" :header="t('listini.col_articolo')" style="width: 130px;" />
        <Column field="articolo_descrizione" :header="t('catalogo.col_descrizione')" style="min-width: 180px;" />
        <Column field="uom_codice" :header="t('catalogo.col_uom')" style="width: 80px;" />
        <Column field="prezzo" :header="t('listini.col_prezzo')" style="width: 130px;">
          <template #body="{ data }">{{ data.prezzo }}</template>
        </Column>
        <Column field="billing_account_codice" :header="t('listini.col_ba')" style="width: 120px;" />
        <Column field="utility_descrizione" :header="t('listini.col_utility')" style="width: 130px;" />
        <Column field="emittente_descrizione" :header="t('listini.col_emittente')" style="width: 150px;" />
        <Column v-if="isBozza" style="width: 50px;">
          <template #body="{ data }">
            <Button icon="pi pi-trash" text rounded size="small" class="app-delete-btn" @click="removeRow(data)" />
          </template>
        </Column>
      </DataTable>
    </div>
  </Drawer>
</template>
