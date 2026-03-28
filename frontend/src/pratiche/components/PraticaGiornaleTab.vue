<script setup>
// Scopo: Tab giornale (audit log) dentro il drawer pratica.
// Timeline cronologica inversa degli eventi sulla pratica.
// Componente riutilizzabile — sara' usato anche da altri domini in futuro.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchGiornale } from '../api/pratiche-api'
import { displayDate } from '../../core/utils/date'
import Tag from 'primevue/tag'

const { t } = useI18n()

const props = defineProps({
  praticaId: { type: Number, required: true }
})

const eventi = ref([])
const loading = ref(false)

// Scopo: Mappa azione giornale a severity e icona.
function azioneStyle(azione) {
  const map = {
    CREAZIONE: { severity: 'info', icon: 'pi pi-plus-circle' },
    CAMBIO_STATO: { severity: 'warn', icon: 'pi pi-sync' },
    ASSEGNAZIONE: { severity: 'secondary', icon: 'pi pi-user' },
    CAMBIO_PRIORITA: { severity: 'secondary', icon: 'pi pi-flag' },
    NOTA: { severity: 'secondary', icon: 'pi pi-comment' },
    ALLEGATO: { severity: 'secondary', icon: 'pi pi-paperclip' },
    SOSPENSIONE: { severity: 'warn', icon: 'pi pi-pause' },
    RIATTIVAZIONE: { severity: 'success', icon: 'pi pi-play' },
    CREAZIONE_FLUSSO: { severity: 'info', icon: 'pi pi-sitemap' },
    CAMBIO_STATO_FLUSSO: { severity: 'warn', icon: 'pi pi-sync' },
    GENERAZIONE: { severity: 'info', icon: 'pi pi-copy' },
  }
  return map[(azione || '').trim()] || { severity: 'secondary', icon: 'pi pi-circle' }
}

// Scopo: Formatta il dettaglio JSON in testo leggibile.
function formatDettaglio(dettaglio) {
  if (!dettaglio || typeof dettaglio !== 'object') return ''
  const parts = []
  if (dettaglio.da) parts.push(`${dettaglio.da} → ${dettaglio.a || '?'}`)
  if (dettaglio.esito) parts.push(`${t('pratiche.flusso_col_esito')}: ${dettaglio.esito}`)
  if (dettaglio.motivo) parts.push(dettaglio.motivo)
  if (dettaglio.note_esito) parts.push(dettaglio.note_esito)
  if (parts.length === 0) {
    // Fallback: mostra chiavi principali
    return Object.entries(dettaglio)
      .filter(([, v]) => v != null && v !== '')
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ')
  }
  return parts.join(' — ')
}

async function loadGiornale() {
  loading.value = true
  try {
    const res = await fetchGiornale(props.praticaId, { limit: 100 })
    eventi.value = res.data.data.results || []
  } finally {
    loading.value = false
  }
}

watch(() => props.praticaId, (id) => {
  if (id) loadGiornale()
}, { immediate: true })
</script>

<template>
  <div class="pratica-giornale-tab">
    <div v-if="loading" class="text-center text-color-secondary p-3">
      <i class="pi pi-spin pi-spinner"></i>
    </div>

    <div v-else-if="eventi.length === 0" class="text-center text-color-secondary p-3">
      {{ t('pratiche.giornale_vuoto') }}
    </div>

    <div v-else class="giornale-list">
      <div v-for="ev in eventi" :key="ev.id" class="giornale-entry">
        <div class="giornale-entry-header">
          <i :class="azioneStyle(ev.azione).icon" class="giornale-icon"></i>
          <Tag :value="ev.azione" :severity="azioneStyle(ev.azione).severity" />
          <span class="giornale-date">{{ displayDate(ev.data_insert) }}</span>
          <span v-if="ev.user_insert" class="giornale-user">{{ ev.user_insert }}</span>
        </div>
        <div v-if="formatDettaglio(ev.dettaglio)" class="giornale-detail">
          {{ formatDettaglio(ev.dettaglio) }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.giornale-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.giornale-entry {
  padding: 0.5rem 0.75rem;
  border-left: 3px solid var(--app-toolbar-border);
  border-radius: 0 4px 4px 0;
  background: color-mix(in srgb, var(--p-surface-700) 20%, transparent);
}

.giornale-entry-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.giornale-icon {
  font-size: 0.8rem;
  color: var(--app-icon-color);
}

.giornale-date {
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.giornale-user {
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
  font-style: italic;
}

.giornale-detail {
  margin-top: 0.25rem;
  font-size: var(--app-font-size-sm);
  color: var(--p-text-muted-color);
  padding-left: 1.3rem;
}
</style>
