<script setup>
// Scopo: Tab allegati dentro il drawer pratica.
// v1: solo metadati (nome_file, tipo, dimensione) — upload file posticipato.
// Gli allegati sono immutabili (no edit, solo add/delete).
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchAllegati, deleteAllegato } from '../api/pratiche-api'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { displayTimestamp } from '../../core/utils/date'
import { formatSize } from '../../core/utils/format'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const { t } = useI18n()
const { execute } = useApiHandler()
const isReadonly = useInjectReadonly()
const { confirmDelete } = useConfirmAction()

const props = defineProps({
  praticaId: { type: Number, required: true }
})

const allegati = ref([])
const loading = ref(false)

async function loadAllegati() {
  loading.value = true
  try {
    const res = await fetchAllegati(props.praticaId)
    allegati.value = res.data.data.results || []
  } finally {
    loading.value = false
  }
}

// Scopo: Elimina un allegato con conferma.
function onElimina(allegato) {
  confirmDelete(allegato.nome_file, async () => {
    const result = await execute(
      () => deleteAllegato(props.praticaId, allegato.id),
      { successMessage: t('pratiche.allegato_eliminato') }
    )
    if (result !== null) await loadAllegati()
  })
}

watch(() => props.praticaId, (id) => {
  if (id) loadAllegati()
}, { immediate: true })
</script>

<template>
  <div>
    <!-- Placeholder upload (futuro) -->
    <div v-if="!isReadonly" class="allegati-placeholder">
      <i class="allegati-placeholder-icon" :class="MANAGE_ICONS.ALLEGATI"></i>
      <span class="app-text-muted">{{ t('pratiche.allegati_upload_futuro') }}</span>
    </div>

    <!-- Lista allegati -->
    <div v-if="loading" class="text-center app-text-muted p-3">
      <i :class="STATUS_ICONS.CARICAMENTO"></i>
    </div>

    <div v-else-if="allegati.length === 0" class="text-center app-text-muted p-3">
      {{ t('pratiche.allegati_vuoti') }}
    </div>

    <div v-else class="allegati-list">
      <div v-for="a in allegati" :key="a.id" class="app-voce-registro">
        <div class="allegato-header">
          <i class="allegato-icon" :class="MANAGE_ICONS.ALLEGATI"></i>
          <span class="allegato-nome">{{ a.nome_file }}</span>
          <Tag :value="a.tipo_allegato_descrizione || a.tipo_allegato_codice" severity="secondary" />
          <span v-if="a.dimensione" class="allegato-size">{{ formatSize(a.dimensione) }}</span>
          <span class="allegato-date">{{ displayTimestamp(a.data_insert) }}</span>
          <span class="allegato-user">{{ a.user_insert }}</span>
          <Button v-if="!isReadonly" :icon="MANAGE_ICONS.DELETE" text rounded size="small"
            class="app-delete-btn"
            @click="onElimina(a)" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.allegati-placeholder {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
  border: 1px dashed var(--app-toolbar-border);
  border-radius: 6px;
}

.allegati-placeholder-icon {
  font-size: 1.2rem;
  color: var(--app-icon-color);
}

.allegati-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}


.allegato-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.allegato-icon {
  font-size: 0.9rem;
  color: var(--app-icon-color);
}

.allegato-nome {
  font-size: var(--app-font-size-sm);
  font-weight: 500;
}

.allegato-size,
.allegato-date,
.allegato-user {
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.allegato-user {
  font-style: italic;
}
</style>
