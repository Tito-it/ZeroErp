<script setup>
// Scopo: Tab note articolo con lista e CRUD inline.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { listArticoloNote, createArticoloNota, updateNota, deleteNota } from '../api/catalogo'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'

const props = defineProps({ articoloId: { type: [String, null], required: true } })
const { t } = useI18n()
const { execute, loading } = useApiHandler()

const rows = ref([])
const adding = ref(false)
const addForm = ref({ testo: '' })
const editingRow = ref(null)
const editForm = ref({ testo: '' })

async function loadRows() {
  if (!props.articoloId) return
  const res = await listArticoloNote(props.articoloId)
  rows.value = res.data.data.results ?? res.data.data ?? []
}

onMounted(loadRows)

function startAdd() {
  adding.value = true
  addForm.value = { testo: '' }
}

async function confirmAdd() {
  await execute(() => createArticoloNota(props.articoloId, { testo: addForm.value.testo, posizione: 'HEADER', anchor_tipo: 'DOCUMENTO' }),
    { successMessage: t('catalogo.nota_creata') })
  adding.value = false
  await loadRows()
}

function startEdit(row) {
  editingRow.value = row.nota_id
  editForm.value = { testo: row.nota_testo || '' }
}

async function confirmEdit(row) {
  await execute(() => updateNota(row.nota_id, { testo: editForm.value.testo }),
    { successMessage: t('catalogo.nota_salvata') })
  editingRow.value = null
  await loadRows()
}

async function removeRow(row) {
  await execute(() => deleteNota(row.nota_id), { successMessage: t('catalogo.nota_eliminata') })
  await loadRows()
}
</script>

<template>
  <div>
    <div style="display: flex; justify-content: flex-end; margin-bottom: 0.5rem;">
      <Button icon="pi pi-plus" :label="t('catalogo.aggiungi_nota')" size="small" @click="startAdd" :disabled="adding" />
    </div>

    <div v-if="adding" style="margin-bottom: 1rem; padding: 0.75rem; border: 1px solid var(--app-card-border); border-radius: 6px;">
      <div class="form-field">
        <label>{{ t('catalogo.field_testo') }}</label>
        <Textarea v-model="addForm.testo" rows="3" style="width: 100%;" />
      </div>
      <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
        <Button icon="pi pi-check" size="small" @click="confirmAdd" :loading="loading" :disabled="!addForm.testo?.trim()" />
        <Button icon="pi pi-times" size="small" severity="secondary" @click="adding = false" />
      </div>
    </div>

    <DataTable :value="rows" :loading="loading" striped-rows class="app-datatable" data-key="nota_id">
      <Column field="nota_testo" :header="t('catalogo.col_testo')" style="min-width: 300px;">
        <template #body="{ data }">
          <Textarea v-if="editingRow === data.nota_id" v-model="editForm.testo" rows="2" style="width: 100%;" />
          <span v-else>{{ data.nota_testo }}</span>
        </template>
      </Column>
      <Column field="nota_posizione" :header="t('catalogo.col_posizione')" style="width: 100px;" />
      <Column style="width: 90px;">
        <template #body="{ data }">
          <div style="display: flex; gap: 0.25rem;">
            <Button v-if="editingRow === data.nota_id" icon="pi pi-check" text rounded size="small" class="app-action-btn" @click="confirmEdit(data)" />
            <Button v-if="editingRow === data.nota_id" icon="pi pi-times" text rounded size="small" @click="editingRow = null" />
            <Button v-if="editingRow !== data.nota_id" icon="pi pi-pencil" text rounded size="small" class="app-action-btn" @click="startEdit(data)" />
            <Button v-if="editingRow !== data.nota_id" icon="pi pi-trash" text rounded size="small" severity="danger" @click="removeRow(data)" />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</template>
