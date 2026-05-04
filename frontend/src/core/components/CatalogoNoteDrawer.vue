<script setup>
// Scopo: Drawer generico per gestione note catalogo (articoli e componenti).
// Pattern: formMode state machine (null=lista, 'new'=aggiungi, 'edit'=modifica).
// Card layout per lista, Textarea + LookupSelect stile per form.
// Riutilizzabile: accetta listFn e createFn come props.
// Update e delete usano gli endpoint generici /note/<id>/.

import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useApiHandler } from '../composables/useApiHandler'
import { updateNota, deleteNota } from '../../catalogo/api/catalogo'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../constants'
import LookupSelect from './LookupSelect.vue'
import DrawerTitle from './DrawerTitle.vue'
import DrawerFooter from './DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  listFn: { type: Function, required: true },
  createFn: { type: Function, required: true },
  title: { type: String, default: null },
})
const emit = defineEmits(['update:visible', 'saved'])

const noteList = ref([])
const listLoading = ref(false)
const formMode = ref(null)
const editId = ref(null)
const form = ref({ testo: '', id_stile: null })

function defaultForm() {
  return { testo: '', id_stile: null }
}

// Scopo: Carica lista note dall'API fornita dal parent.
async function loadNote() {
  listLoading.value = true
  try {
    const res = await props.listFn()
    const payload = res.data?.data
    noteList.value = payload?.results || payload || []
  } catch {
    noteList.value = []
  } finally {
    listLoading.value = false
  }
}

watch(() => props.visible, (val) => {
  if (!val) return
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
  loadNote()
})

function onStartNew() {
  formMode.value = 'new'
  editId.value = null
  form.value = defaultForm()
}

function onStartEdit(n) {
  formMode.value = 'edit'
  editId.value = n.nota_id
  form.value = {
    testo: n.nota_testo || '',
    id_stile: n.id_stile ?? n.stile_id ?? null,
  }
}

function onCancelForm() {
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
}

const canSaveForm = computed(() => {
  return form.value.testo?.trim() && form.value.id_stile != null
})

// Scopo: Salva nota (create o update). Ricarica lista e notifica il parent.
async function onSaveForm() {
  if (formMode.value === 'edit' && editId.value) {
    const result = await execute(
      () => updateNota(editId.value, {
        testo: form.value.testo,
        id_stile: form.value.id_stile,
      }),
      { successMessage: t('catalogo.nota_salvata') }
    )
    if (result === null) return
  } else {
    const result = await execute(
      () => props.createFn({
        testo: form.value.testo,
        id_stile: form.value.id_stile,
        posizione: 'HEADER',
        anchor_tipo: 'DOCUMENTO',
      }),
      { successMessage: t('catalogo.nota_creata') }
    )
    if (result === null) return
  }
  formMode.value = null
  editId.value = null
  form.value = defaultForm()
  await loadNote()
  emit('saved')
}

// Scopo: Elimina nota per id. Ricarica lista e notifica il parent.
async function onDelete(n) {
  const result = await execute(
    () => deleteNota(n.nota_id),
    { successMessage: t('catalogo.nota_eliminata') }
  )
  if (result !== null) {
    await loadNote()
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
      <DrawerTitle :action="t('common.edit')" :title="title || t('catalogo.tab_note')" icon="pi pi-file-edit" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="!listLoading">
        <div v-if="noteList.length === 0 && !formMode" class="app-empty-state">
          <i class="pi pi-file-edit" />
          <p>{{ t('catalogo.nessuna_nota') }}</p>
        </div>

        <div v-else-if="noteList.length > 0" class="note-list">
          <div v-for="n in noteList" :key="n.nota_id" class="nota-card">
            <div class="nota-card-content">
              <Tag v-if="n.stile_descrizione" :value="n.stile_descrizione" severity="secondary" />
              <span class="nota-card-testo">{{ n.nota_testo }}</span>
            </div>
            <div v-if="!formMode && !isReadonly" class="nota-card-actions">
              <Button :icon="MANAGE_ICONS.EDIT" text rounded size="small"
                class="app-edit-btn" :title="t('common.edit')" @click="onStartEdit(n)" />
              <Button :icon="MANAGE_ICONS.DELETE" text rounded size="small"
                class="app-delete-btn" :title="t('common.delete')" @click="onDelete(n)" />
            </div>
          </div>
        </div>

        <div v-if="!formMode && !isReadonly" class="mt-05">
          <Button
            :label="t('catalogo.aggiungi_nota')"
            :icon="MANAGE_ICONS.ADD"
            text size="small"
            class="app-action-btn"
            @click="onStartNew"
          />
        </div>
      </template>

      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formMode === 'edit' ? t('catalogo.modifica_nota') : t('catalogo.nuova_nota') }}</h4>
        </div>
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('catalogo.field_stile') }} *</label>
            <LookupSelect v-model="form.id_stile" rel="config.note_stili"
              :placeholder="t('catalogo.select_stile')" />
          </div>
          <div class="form-field">
            <label>{{ t('catalogo.field_testo') }} *</label>
            <Textarea v-model="form.testo" rows="5" :placeholder="t('catalogo.nota_testo_placeholder')" class="w-full" />
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
.note-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.nota-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius-sm, 4px);
  padding: 0.5rem 0.75rem;
}
.nota-card-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.nota-card-testo {
  font-size: 0.85rem;
  color: var(--p-text-color);
  white-space: pre-wrap;
  word-break: break-word;
}
.nota-card-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}
</style>
