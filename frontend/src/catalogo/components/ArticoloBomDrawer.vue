<script setup>
// Scopo: Sub-drawer per gestione distinta base (BoM) articolo.
// Layout: lista componenti sempre visibile in alto + form inserimento in basso.
// Modifica: valido_al editabile inline nella DataTable per disattivare un componente.
// Lookup componenti filtrato per is_solo_componente=true.

import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import {
  listArticoloComponenti, createArticoloComponente,
  updateArticoloComponente, deleteArticoloComponente,
  listComponenteNote, createComponenteNota,
} from '../api/catalogo'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import { displayDate, toDateString } from '../../core/utils/date'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import CatalogoNoteDrawer from '../../core/components/CatalogoNoteDrawer.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
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

// Form inserimento nuovo componente
const form = ref({})
const componenteObj = ref(null)
const adding = ref(false)

// Edit inline: traccia quale riga ha il DatePicker valido_al aperto
const editingValidoAlId = ref(null)
const editingValidoAlValue = ref(null)

// Sub-drawer note per componente
const noteDrawerVisible = ref(false)
const noteCompId = ref(null)

const noteListFn = computed(() => () => listComponenteNote(props.articoloId, noteCompId.value))
const noteCreateFn = computed(() => (payload) => createComponenteNota(props.articoloId, noteCompId.value, payload))

function openNoteDrawer(row) {
  noteCompId.value = row.id
  noteDrawerVisible.value = true
}

function defaultForm() {
  return {
    componente_id: null,
    coeff_qta: 1,
    partecipa_qta: true,
    obbligatorio: true,
    determina_qta_padre: false,
    valido_dal: new Date(),
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
  form.value = defaultForm()
  componenteObj.value = null
  adding.value = false
  editingValidoAlId.value = null
  loadComponenti()
})

// Scopo: Callback quando l'utente seleziona un articolo dal lookup.
function onComponenteSelect(item) {
  componenteObj.value = item
  form.value.componente_id = item?.id || null
}

function startAdd() {
  form.value = defaultForm()
  componenteObj.value = null
  adding.value = true
}

function cancelAdd() {
  adding.value = false
  form.value = defaultForm()
  componenteObj.value = null
}

const canSaveForm = computed(() => {
  return form.value.componente_id != null && form.value.coeff_qta > 0
})

// Scopo: Inserisce nuovo componente. Ricarica lista e notifica il parent.
async function onSaveNew() {
  const payload = {
    componente_id: form.value.componente_id,
    coeff_qta: form.value.coeff_qta,
    partecipa_qta: form.value.partecipa_qta,
    obbligatorio: form.value.obbligatorio,
    determina_qta_padre: form.value.determina_qta_padre,
    valido_dal: toDateString(form.value.valido_dal),
    valido_al: toDateString(form.value.valido_al),
  }
  const result = await execute(
    () => createArticoloComponente(props.articoloId, payload),
    { successMessage: t('catalogo.componente_aggiunto') }
  )
  if (result === null) return
  adding.value = false
  form.value = defaultForm()
  componenteObj.value = null
  await loadComponenti()
  emit('saved')
}

// Scopo: Apre edit inline valido_al per una riga.
function startEditValidoAl(row) {
  editingValidoAlId.value = row.id
  editingValidoAlValue.value = parseDate(row.valido_al)
}

// Scopo: Salva valido_al modificato inline.
async function confirmEditValidoAl(row) {
  const result = await execute(
    () => updateArticoloComponente(props.articoloId, row.id, {
      valido_al: toDateString(editingValidoAlValue.value),
    }),
    { successMessage: t('catalogo.componente_salvato') }
  )
  if (result === null) return
  editingValidoAlId.value = null
  editingValidoAlValue.value = null
  await loadComponenti()
  emit('saved')
}

function cancelEditValidoAl() {
  editingValidoAlId.value = null
  editingValidoAlValue.value = null
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
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
  >
    <template #header>
      <DrawerTitle :action="t('common.edit')" :title="t('catalogo.tab_bom')" icon="pi pi-sitemap" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="!listLoading">
        <!-- Lista componenti (sempre visibile) -->
        <div v-if="componentiList.length === 0 && !adding" class="app-empty-state">
          <i class="pi pi-sitemap" />
          <p>{{ t('catalogo.nessun_componente') }}</p>
        </div>

        <DataTable v-if="componentiList.length > 0" :value="componentiList" class="app-datatable" striped-rows>
          <Column field="componente_codice" :header="t('catalogo.col_codice')" />
          <Column field="componente_descrizione" :header="t('catalogo.col_descrizione')" />
          <Column field="coeff_qta" :header="t('catalogo.col_coeff_qta')" style="width: 70px;" />
          <Column :header="t('catalogo.field_valido_al')" style="width: 120px;">
            <template #body="{ data }">
              <template v-if="editingValidoAlId === data.id">
                <div class="flex gap-1 align-items-center">
                  <DatePicker v-model="editingValidoAlValue" :date-format="DATE_FORMAT"
                    show-icon show-button-bar style="width: 110px;" />
                  <Button icon="pi pi-check" text rounded size="small" class="app-action-btn"
                    @click="confirmEditValidoAl(data)" />
                  <Button icon="pi pi-times" text rounded size="small"
                    @click="cancelEditValidoAl" />
                </div>
              </template>
              <template v-else>
                <span v-if="!isReadonly" class="valido-al-cell" @click="startEditValidoAl(data)">
                  {{ displayDate(data.valido_al) || '—' }}
                  <i class="pi pi-pencil" style="font-size: 0.7rem; margin-left: 0.25rem; opacity: 0.5;" />
                </span>
                <span v-else>{{ displayDate(data.valido_al) || '—' }}</span>
              </template>
            </template>
          </Column>
          <Column v-if="!isReadonly" style="width: 80px;">
            <template #body="{ data }">
              <div class="flex gap-1">
                <Button icon="pi pi-file-edit" text rounded size="small"
                  v-tooltip.bottom="t('catalogo.gestisci_note')"
                  class="app-action-btn" @click="openNoteDrawer(data)" />
                <Button icon="pi pi-trash"
                  text rounded size="small" class="app-delete-btn" @click="onDelete(data)" />
              </div>
            </template>
          </Column>
        </DataTable>

        <!-- Form inserimento nuovo componente -->
        <template v-if="!isReadonly">
          <div v-if="!adding" class="mt-05">
            <Button
              :label="t('catalogo.aggiungi_componente')"
              icon="pi pi-plus"
              text size="small"
              class="app-action-btn"
              @click="startAdd"
            />
          </div>

          <template v-if="adding">
            <div class="app-drawer-section">
              <h4>{{ t('catalogo.nuovo_componente') }}</h4>
            </div>
            <div class="form-grid">
              <div class="form-field">
                <label>{{ t('catalogo.field_componente') }} *</label>
                <ArticoloLookup
                  :model-value="componenteObj"
                  :placeholder="t('catalogo.search_componente')"
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
            <div class="flex justify-end gap-2 mt-05">
              <Button :label="t('common.cancel')" text @click="cancelAdd" />
              <Button :label="t('common.save')" :loading="loading" :disabled="!canSaveForm" @click="onSaveNew" />
            </div>
          </template>
        </template>
      </template>
    </div>
  </Drawer>

  <CatalogoNoteDrawer
    :visible="noteDrawerVisible"
    @update:visible="v => noteDrawerVisible = v"
    :list-fn="noteListFn"
    :create-fn="noteCreateFn"
    :title="t('catalogo.tab_note')"
    @saved="loadComponenti"
  />
</template>

<style scoped>
.valido-al-cell {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}
.valido-al-cell:hover {
  color: var(--p-primary-color);
}
</style>
