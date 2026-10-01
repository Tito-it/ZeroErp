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
import { MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { displayTimestamp } from '../../core/utils/date'
import Textarea from 'primevue/textarea'
import LookupSelect from '../../core/components/LookupSelect.vue'
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

const nuovaNota = ref({ tipo_nota_codice: null, contenuto: '' })

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
  <div>
    <!-- Form nuova nota -->
    <div v-if="!isReadonly" class="nota-form">
      <div class="nota-form-row">
        <LookupSelect
          v-model="nuovaNota.tipo_nota_codice"
          rel="config.tipi_nota"
          value-field="codice_interno"
          :placeholder="t('pratiche.nota_tipo')"
          style="width: 160px;"
        />
        <Button
          :icon="MANAGE_ICONS.ADD"
          :label="t('pratiche.nota_aggiungi')"
          size="small"
          :disabled="!nuovaNota.contenuto.trim() || !nuovaNota.tipo_nota_codice"
          @click="onCrea"
        />
      </div>
      <Textarea
        v-model="nuovaNota.contenuto"
        :placeholder="t('pratiche.nota_placeholder')"
        rows="2"
        auto-resize
      />
    </div>

    <!-- Lista note -->
    <div v-if="loading" class="text-center app-text-muted p-3">
      <i :class="STATUS_ICONS.CARICAMENTO"></i>
    </div>

    <div v-else-if="note.length === 0" class="text-center app-text-muted p-3">
      {{ t('pratiche.note_vuote') }}
    </div>

    <div v-else class="note-list">
      <div v-for="n in note" :key="n.id" class="app-voce-registro">
        <div class="nota-header">
          <Tag :value="n.tipo_nota_descrizione || n.tipo_nota_codice" severity="secondary" />
          <span class="nota-date">{{ displayTimestamp(n.data_insert) }}</span>
          <span class="nota-user">{{ n.user_insert }}</span>
          <div v-if="!isReadonly" class="nota-actions">
            <Button v-if="editingId !== n.id" :icon="MANAGE_ICONS.EDIT" text rounded size="small"
              class="app-action-btn" @click="startEdit(n)" />
            <Button :icon="MANAGE_ICONS.DELETE" text rounded size="small"
              class="app-delete-btn" @click="onElimina(n)" />
          </div>
        </div>
        <!-- Contenuto: editing inline o testo -->
        <div v-if="editingId === n.id" class="nota-edit">
          <Textarea v-model="editingContenuto" rows="2" auto-resize />
          <div class="nota-edit-actions">
            <Button :icon="MANAGE_ICONS.CONFIRM" size="small" @click="onSalvaEdit(n)" />
            <Button :icon="MANAGE_ICONS.CANCEL" size="small" severity="secondary" @click="cancelEdit" />
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
