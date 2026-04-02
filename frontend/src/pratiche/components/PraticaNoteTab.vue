<script setup>
// Scopo: Tab note dentro il drawer pratica.
// Lista note con tipo, contenuto, data, utente.
// Form inline per nuova nota (Select tipo + Textarea).
// Edit/delete su note esistenti.
import { ref, watch } from 'vue'

import { useI18n } from 'vue-i18n'
import { fetchNote, createNota, updateNota, deleteNota } from '../api/pratiche-api'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useLookup } from '../../core/composables/useLookup'
import { lookupCodici } from '../../core/apiCore'
import { displayTimestamp } from '../../core/utils/date'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
const { execute } = useApiHandler()
const isReadonly = useInjectReadonly()
const { confirmDelete } = useConfirmAction()

const props = defineProps({
  praticaId: { type: Number, required: true }
})

const note = ref([])
const loading = ref(false)

// Form nuova nota — il tipo default e' il primo del lookup (evita hardcoded 'GENERALE')
const tipiNota = useLookup(() => lookupCodici('config.tipi_nota'), { immediate: true })
const nuovaNota = ref({ tipo_nota_codice: null, contenuto: '' })
watch(() => tipiNota.items.value, (items) => {
  if (items.length > 0 && !nuovaNota.value.tipo_nota_codice) {
    nuovaNota.value.tipo_nota_codice = items[0].codice_interno
  }
})

// Nota in editing (null = nessuna)
const editingId = ref(null)
const editingContenuto = ref('')

async function loadNote() {
  loading.value = true
  try {
    const res = await fetchNote(props.praticaId)
    note.value = res.data.data.results || []
  } finally {
    loading.value = false
  }
}

// Scopo: Crea una nuova nota.
async function onCrea() {
  if (!nuovaNota.value.contenuto.trim()) return
  const result = await execute(
    () => createNota(props.praticaId, nuovaNota.value),
    { successMessage: t('pratiche.nota_creata') }
  )
  if (result !== null) {
    nuovaNota.value.contenuto = ''
    await loadNote()
  }
}

// Scopo: Inizia editing inline di una nota.
function startEdit(nota) {
  editingId.value = nota.id
  editingContenuto.value = nota.contenuto
}

function cancelEdit() {
  editingId.value = null
  editingContenuto.value = ''
}

// Scopo: Salva la nota in editing.
async function onSalvaEdit(nota) {
  if (!editingContenuto.value.trim()) return
  const result = await execute(
    () => updateNota(props.praticaId, nota.id, { contenuto: editingContenuto.value }),
    { successMessage: t('pratiche.nota_salvata') }
  )
  if (result !== null) {
    cancelEdit()
    await loadNote()
  }
}

// Scopo: Elimina una nota con conferma.
function onElimina(nota) {
  confirmDelete(t('pratiche.nota'), async () => {
    const result = await execute(
      () => deleteNota(props.praticaId, nota.id),
      { successMessage: t('pratiche.nota_eliminata') }
    )
    if (result !== null) await loadNote()
  })
}

watch(() => props.praticaId, (id) => {
  if (id) loadNote()
}, { immediate: true })
</script>

<template>
  <div class="pratica-note-tab">
    <!-- Form nuova nota -->
    <div v-if="!isReadonly" class="nota-form">
      <div class="nota-form-row">
        <Select
          v-model="nuovaNota.tipo_nota_codice"
          :options="tipiNota.items.value"
          :loading="tipiNota.loading.value"
          option-label="descrizione"
          option-value="codice_interno"
          :placeholder="t('pratiche.nota_tipo')"
          style="width: 160px;"
        />
        <Button
          icon="pi pi-plus"
          :label="t('pratiche.nota_aggiungi')"
          size="small"
          :disabled="!nuovaNota.contenuto.trim() || !nuovaNota.tipo_nota_codice"
          @click="onCrea"
        />
      </div>
      <Textarea
        v-model="nuovaNota.contenuto"
        :placeholder="t('pratiche.nota_placeholder')"
        class="w-full"
        rows="2"
        auto-resize
      />
    </div>

    <!-- Lista note -->
    <div v-if="loading" class="text-center text-color-secondary p-3">
      <i class="pi pi-spin pi-spinner"></i>
    </div>

    <div v-else-if="note.length === 0" class="text-center text-color-secondary p-3">
      {{ t('pratiche.note_vuote') }}
    </div>

    <div v-else class="note-list">
      <div v-for="n in note" :key="n.id" class="nota-entry">
        <div class="nota-header">
          <Tag :value="n.tipo_nota_descrizione || n.tipo_nota_codice" severity="secondary" />
          <span class="nota-date">{{ displayTimestamp(n.data_insert) }}</span>
          <span class="nota-user">{{ n.user_insert }}</span>
          <div v-if="!isReadonly" class="nota-actions">
            <Button v-if="editingId !== n.id" icon="pi pi-pencil" text rounded size="small"
              class="app-action-btn" @click="startEdit(n)" />
            <Button icon="pi pi-trash" text rounded size="small"
              class="app-action-btn" severity="danger" @click="onElimina(n)" />
          </div>
        </div>
        <!-- Contenuto: editing inline o testo -->
        <div v-if="editingId === n.id" class="nota-edit">
          <Textarea v-model="editingContenuto" class="w-full" rows="2" auto-resize />
          <div class="nota-edit-actions">
            <Button icon="pi pi-check" size="small" @click="onSalvaEdit(n)" />
            <Button icon="pi pi-times" size="small" severity="secondary" @click="cancelEdit" />
          </div>
        </div>
        <div v-else class="nota-contenuto">{{ n.contenuto }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nota-form {
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--app-toolbar-border);
}

.nota-form-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}

.note-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.nota-entry {
  padding: 0.5rem 0.75rem;
  border-left: 3px solid var(--app-toolbar-border);
  border-radius: 0 4px 4px 0;
  background: color-mix(in srgb, var(--p-surface-700) 20%, transparent);
}

.nota-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.25rem;
}

.nota-date {
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.nota-user {
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
  font-style: italic;
}

.nota-actions {
  margin-left: auto;
  display: flex;
  gap: 0.15rem;
}

.nota-contenuto {
  font-size: var(--app-font-size-sm);
  white-space: pre-wrap;
}

.nota-edit {
  margin-top: 0.25rem;
}

.nota-edit-actions {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.25rem;
}
</style>
