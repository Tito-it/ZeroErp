<script setup>
// Scopo: Sub-drawer per gestione note articolo.
// Pattern: formMode state machine (null=lista, 'new'=aggiungi, 'edit'=modifica).
// Card layout per lista, Textarea per form.

import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { listArticoloNote, createArticoloNota, updateNota, deleteNota } from '../api/catalogo'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const noteList = ref([])
const listLoading = ref(false)
const formMode = ref(null)
const editId = ref(null)
const form = ref({ testo: '' })

// Scopo: Carica lista note dell'articolo.
async function loadNote() {
  if (!props.articoloId) return
  listLoading.value = true
  try {
    const res = await listArticoloNote(props.articoloId)
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
  form.value = { testo: '' }
  loadNote()
})

function onStartNew() {
  formMode.value = 'new'
  editId.value = null
  form.value = { testo: '' }
}

function onStartEdit(n) {
  formMode.value = 'edit'
  editId.value = n.nota_id
  form.value = { testo: n.nota_testo || '' }
}

function onCancelForm() {
  formMode.value = null
  editId.value = null
  form.value = { testo: '' }
}

// Scopo: Salva nota (create o update). Ricarica lista e notifica il parent.
async function onSaveForm() {
  if (formMode.value === 'edit' && editId.value) {
    const result = await execute(
      () => updateNota(editId.value, { testo: form.value.testo }),
      { successMessage: t('catalogo.nota_salvata') }
    )
    if (result === null) return
  } else {
    const result = await execute(
      () => createArticoloNota(props.articoloId, {
        testo: form.value.testo,
        posizione: 'HEADER',
        anchor_tipo: 'DOCUMENTO',
      }),
      { successMessage: t('catalogo.nota_creata') }
    )
    if (result === null) return
  }
  formMode.value = null
  editId.value = null
  form.value = { testo: '' }
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
      <DrawerTitle :action="t('common.edit')" :title="t('catalogo.tab_note')" icon="pi pi-file-edit" />
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
              <span class="nota-card-testo">{{ n.nota_testo }}</span>
            </div>
            <div v-if="!formMode && !isReadonly" class="nota-card-actions">
              <Button icon="pi pi-pencil" text rounded size="small"
                class="app-action-btn" :title="t('common.edit')" @click="onStartEdit(n)" />
              <Button icon="pi pi-trash" severity="danger" text rounded size="small"
                :title="t('common.delete')" @click="onDelete(n)" />
            </div>
          </div>
        </div>

        <div v-if="!formMode && !isReadonly" class="mt-05">
          <Button
            :label="t('catalogo.aggiungi_nota')"
            icon="pi pi-plus"
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
            <label>{{ t('catalogo.field_testo') }} *</label>
            <Textarea v-model="form.testo" rows="5" :placeholder="t('catalogo.nota_testo_placeholder')" class="w-full" />
          </div>
        </div>

        <DrawerFooter
          :loading="loading"
          :disabled="!form.testo?.trim()"
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
