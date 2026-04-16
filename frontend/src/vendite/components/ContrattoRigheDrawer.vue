<script setup>
// Scopo: Sub-drawer gestione righe contratto — pattern master-detail inline.
//        Lista paginata sopra (10 righe/pagina), form dettaglio sotto.
//        Click riga = edit, pulsante Nuovo = create, Salva/Annulla sempre in basso.
//        Modalita' C: prezzo_unitario obbligatorio su tutte le righe.
//        Modalita' B: opzionale (solo se serve override).
//        Modalita' A: di norma non necessarie (solo override puntuali).
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContrattiStore } from '../stores/contratti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { statoContrattoSeverity } from '../../core/utils/severity'
import { listArticoloUom } from '../../catalogo/api/catalogo'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import NewButton from '../../core/components/NewButton.vue'

const { t } = useI18n()
const store = useContrattiStore()
const { execute, loading } = useApiHandler()
const { confirmDelete } = useConfirmAction()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  contrattoId: { type: Number, required: true },
  contrattoModalita: { type: String, default: 'B' },
  righeIniziali: { type: Array, default: () => [] },
  // Contesto contratto (per intestazione riepilogativa)
  contrattoNumero: { type: String, default: '' },
  contrattoCliente: { type: String, default: '' },
  contrattoValidoDal: { type: String, default: '' },
  contrattoValidoAl: { type: String, default: null },
  contrattoStatoCodice: { type: String, default: '' },
  contrattoStatoDescrizione: { type: String, default: '' },
})
const emit = defineEmits(['update:visible', 'changed'])

const righe = ref([])

// === Form state ===
// formMode: null (nessun form), 'create', 'edit'
const formMode = ref(null)
const rigaEditId = ref(null)
const form = ref({})
const selectedRow = ref(null)

// === UoM operative dell'articolo selezionato ===
const uomOptions = ref([])
const uomLoading = ref(false)

function uomLabel(item) {
  return item.is_base ? `${item.uom_codice} (base)` : item.uom_codice
}

async function loadUomPerArticolo(articoloId) {
  uomOptions.value = []
  if (!articoloId) return
  uomLoading.value = true
  try {
    const res = await listArticoloUom(articoloId)
    const list = res.data.data?.results || res.data.data || []
    uomOptions.value = list
    if (formMode.value && !form.value.uom_operativa_id) {
      const base = list.find(u => u.is_base)
      form.value.uom_operativa_id = base ? base.uom_id : (list.length === 1 ? list[0].uom_id : null)
    }
  } catch {
    uomOptions.value = []
  } finally {
    uomLoading.value = false
  }
}

// === Options ===
const tipoErogazioneOptions = computed(() => [
  { value: 'CANONE', label: t('contratti.tipo_erogazione_canone') },
  { value: 'CONSUMO', label: t('contratti.tipo_erogazione_consumo') },
  { value: 'UNA_TANTUM', label: t('contratti.tipo_erogazione_una_tantum') },
])

function defaultForm() {
  return {
    articolo_id: null,
    articolo_obj: null,
    tipo_erogazione: 'CANONE',
    prezzo_unitario: null,
    qta_operativa: 1,
    uom_operativa_id: null,
    ordine: 10,
  }
}

// === Lifecycle ===
watch(() => props.visible, (v) => {
  if (v) {
    righe.value = [...(props.righeIniziali || [])]
    closeForm()
  }
})

watch(() => props.righeIniziali, (v) => {
  righe.value = [...(v || [])]
}, { deep: true })

// === Azioni ===
function onNew() {
  form.value = defaultForm()
  formMode.value = 'create'
  rigaEditId.value = null
  selectedRow.value = null
  uomOptions.value = []
}

function onRowSelect(event) {
  const r = event.data
  form.value = {
    articolo_id: r.articolo_id,
    articolo_obj: { id: r.articolo_id, codice: r.articolo_codice, descrizione: r.articolo_descrizione, _display: `${r.articolo_codice} — ${r.articolo_descrizione}` },
    tipo_erogazione: r.tipo_erogazione || 'CANONE',
    prezzo_unitario: r.prezzo_unitario != null ? Number(r.prezzo_unitario) : null,
    qta_operativa: r.qta_operativa != null ? Number(r.qta_operativa) : 1,
    uom_operativa_id: r.uom_operativa_id,
    ordine: r.ordine || 10,
  }
  formMode.value = 'edit'
  rigaEditId.value = r.id
  loadUomPerArticolo(r.articolo_id)
}

function onArticoloSelected(item) {
  form.value.articolo_id = item?.id || null
  form.value.uom_operativa_id = null
  loadUomPerArticolo(item?.id)
}

function closeForm() {
  formMode.value = null
  rigaEditId.value = null
  form.value = {}
  selectedRow.value = null
  uomOptions.value = []
}

// === Validazione ===
const canSave = computed(() => {
  if (isReadonly.value) return false
  if (!formMode.value) return false
  if (!form.value.articolo_id) return false
  if (!form.value.uom_operativa_id) return false
  if (props.contrattoModalita === 'C' && (form.value.prezzo_unitario == null || form.value.prezzo_unitario === '')) return false
  return true
})

const formTitle = computed(() => {
  if (formMode.value === 'create') return t('contratti.nuova_riga')
  if (formMode.value === 'edit') return t('contratti.modifica_riga')
  return ''
})

// === Salvataggio ===
async function onSave() {
  const f = form.value
  const payload = {
    tipo_erogazione: f.tipo_erogazione || null,
    prezzo_unitario: f.prezzo_unitario != null ? String(f.prezzo_unitario) : null,
    qta_operativa: f.qta_operativa != null ? String(f.qta_operativa) : '1',
    uom_operativa_id: f.uom_operativa_id || null,
    ordine: f.ordine != null ? Number(f.ordine) : null,
  }
  if (formMode.value === 'create') {
    payload.articolo_id = f.articolo_id
    const result = await execute(
      () => store.addRiga(props.contrattoId, payload),
      { successMessage: t('contratti.riga_creata') }
    )
    if (result !== null) {
      emit('changed')
      closeForm()
    }
  } else {
    const result = await execute(
      () => store.updateRiga(props.contrattoId, rigaEditId.value, payload),
      { successMessage: t('contratti.riga_salvata') }
    )
    if (result !== null) {
      emit('changed')
      closeForm()
    }
  }
}

function onDelete(r) {
  confirmDelete(r.articolo_codice || r.articolo_descrizione || `#${r.id}`, async () => {
    const result = await execute(
      () => store.deleteRiga(props.contrattoId, r.id),
      { successMessage: t('contratti.riga_eliminata') }
    )
    if (result !== null) {
      // Se stavo editando questa riga, chiudi il form.
      if (rigaEditId.value === r.id) closeForm()
      emit('changed')
    }
  })
}

function onClose() {
  emit('update:visible', false)
}
</script>

<template>
  <Drawer
    :visible="props.visible"
    @update:visible="val => emit('update:visible', val)"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle :title="t('contratti.drawer_righe_titolo')" icon="pi pi-list" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- === Intestazione contesto contratto === -->
      <div v-if="contrattoStatoCodice" style="text-align: right;" class="mb-2">
        <Tag :value="contrattoStatoDescrizione"
          :severity="statoContrattoSeverity(contrattoStatoCodice)" />
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('contratti.field_numero') }}</label>
          <span class="font-bold">{{ contrattoNumero }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('contratti.col_ba') }}</label>
          <span>{{ contrattoCliente }}</span>
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('contratti.col_valido_dal') }}</label>
          <span>{{ displayDate(contrattoValidoDal) }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('contratti.col_valido_al') }}</label>
          <span>{{ contrattoValidoAl ? displayDate(contrattoValidoAl) : '—' }}</span>
        </div>
      </div>

      <!-- Avviso modalita' C -->
      <Message v-if="contrattoModalita === 'C'" severity="warn" :closable="false" size="small">
        {{ t('contratti.righe_c_warn') }}
      </Message>

      <!-- === MASTER: toolbar + lista paginata === -->
      <div class="app-page-toolbar">
        <div class="app-page-filters"></div>
        <div class="app-page-actions">
          <NewButton :tooltip="t('contratti.aggiungi_riga')"
            @click="onNew" :disabled="formMode === 'create' || isReadonly" />
        </div>
      </div>

      <DataTable
        :value="righe"
        v-model:selection="selectedRow"
        selection-mode="single"
        data-key="id"
        class="app-datatable"
        striped-rows
        paginator
        :rows="10"
        :rows-per-page-options="[10, 25]"
        paginator-position="top"
        @row-select="onRowSelect"
      >
        <Column field="articolo_codice" :header="t('contratti.col_articolo')" style="width: 150px;" />
        <Column field="articolo_descrizione" :header="t('contratti.col_descrizione')" />
        <Column field="uom_codice" :header="t('contratti.col_uom')" style="width: 70px;" />
        <Column field="prezzo_unitario" :header="t('contratti.col_prezzo')" style="width: 90px;">
          <template #body="{ data }">{{ data.prezzo_unitario ?? '—' }}</template>
        </Column>
        <Column field="qta_operativa" :header="t('contratti.col_qta')" style="width: 70px;" />
        <Column field="tipo_erogazione" :header="t('contratti.col_tipo_erogazione')" style="width: 100px;" />
        <Column :exportable="false" style="width: 50px;">
          <template #body="{ data }">
            <Button v-if="!isReadonly" icon="pi pi-trash" text rounded size="small" class="app-delete-btn"
              @click.stop="onDelete(data)" />
          </template>
        </Column>
      </DataTable>

      <!-- === DETAIL: form inserimento/modifica === -->
      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formTitle }}</h4>
        </div>

        <div class="form-field">
          <label>{{ t('contratti.field_articolo') }} *</label>
          <ArticoloLookup
            v-model="form.articolo_obj"
            @update:modelValue="onArticoloSelected"
            :disabled="formMode === 'edit'"
            :placeholder="t('contratti.select_articolo')"
          />
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('contratti.field_uom') }} *</label>
            <Select v-model="form.uom_operativa_id"
              :options="uomOptions"
              option-value="uom_id"
              :option-label="uomLabel"
              :placeholder="form.articolo_id ? t('contratti.select_uom') : t('contratti.uom_select_articolo_first')"
              :disabled="!form.articolo_id || uomLoading"
              :loading="uomLoading"
              class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('contratti.field_tipo_erogazione') }}</label>
            <Select v-model="form.tipo_erogazione" :options="tipoErogazioneOptions"
              option-label="label" option-value="value" class="w-full" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>
              {{ t('contratti.field_prezzo_unitario') }}
              <span v-if="contrattoModalita === 'C'">*</span>
            </label>
            <InputNumber v-model="form.prezzo_unitario" class="w-full"
              :min-fraction-digits="2" :max-fraction-digits="4" showButtons />
          </div>
          <div class="form-field">
            <label>{{ t('contratti.field_qta_operativa') }} *</label>
            <InputNumber v-model="form.qta_operativa" class="w-full"
              :min="0.0001" :min-fraction-digits="0" :max-fraction-digits="4" showButtons />
          </div>
        </div>

        <div class="form-field">
          <label>{{ t('contratti.field_ordine') }}</label>
          <InputNumber v-model="form.ordine" class="w-full" :min="0" />
        </div>

        <div class="app-drawer-footer">
          <Button :label="t('common.cancel')" severity="secondary" @click="closeForm" />
          <Button :label="t('common.save')" :disabled="!canSave || loading" :loading="loading" @click="onSave" />
        </div>
      </template>

      <DrawerFooter close-only @cancel="onClose" />
    </div>
  </Drawer>
</template>
