<script setup>
// Scopo: Tab giornale (audit log) dentro il drawer pratica.
// Timeline cronologica inversa degli eventi sulla pratica.
// Componente riutilizzabile — sara' usato anche da altri domini in futuro.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchGiornale } from '../api/pratiche-api'
import { displayDate, displayTime } from '../../core/utils/date'
import { azioneGiornaleStyle } from '../../core/utils/severity'
import Tag from 'primevue/tag'

const { t, te } = useI18n()

const props = defineProps({
  praticaId: { type: Number, required: true }
})

const eventi = ref([])
const loading = ref(false)

// Alias locale per brevita' nel template.
const azioneStyle = azioneGiornaleStyle

// Scopo: label leggibile dell'azione (i18n) con fallback al codice grezzo se la
// chiave non esiste (codici nuovi a DB non ancora tradotti restano comunque visibili).
function azioneLabel(azione) {
  const key = `pratiche.giornale_azioni.${azione}`
  return te(key) ? t(key) : azione
}

// Scopo: Formatta il dettaglio in testo leggibile. Usa i display fields decodificati
// dal BE (transizione stati, descrizione flusso) invece degli id grezzi del jsonb.
function formatDettaglio(ev) {
  const parts = []
  // Transizione di stato: descrizioni decodificate lato BE (FLUSSO_STATO_CAMBIATO).
  if (ev.dettaglio_stato_nuovo) {
    parts.push(ev.dettaglio_stato_precedente
      ? `${ev.dettaglio_stato_precedente} → ${ev.dettaglio_stato_nuovo}`
      : ev.dettaglio_stato_nuovo)
  }
  const d = ev.dettaglio && typeof ev.dettaglio === 'object' ? ev.dettaglio : {}
  if (d.esito) parts.push(`${t('pratiche.flusso_col_esito')}: ${d.esito}`)
  if (d.motivo) parts.push(d.motivo)
  if (d.note_esito) parts.push(d.note_esito)
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
          <Tag :value="azioneLabel(ev.azione)" :severity="azioneStyle(ev.azione).severity" />
          <span v-if="ev.flusso_template_descrizione" class="giornale-flusso">
            {{ ev.flusso_template_descrizione }}
          </span>
          <span v-if="ev.user_insert" class="giornale-user">{{ ev.user_insert }}</span>
          <!-- Quando: data sopra, ora sotto, allineati in fondo a destra. -->
          <div class="giornale-when">
            <span class="giornale-date">{{ displayDate(ev.data_insert) }}</span>
            <span class="giornale-time">{{ displayTime(ev.data_insert) }}</span>
          </div>
        </div>
        <div v-if="formatDettaglio(ev)" class="giornale-detail">
          {{ formatDettaglio(ev) }}
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

.giornale-flusso {
  font-size: var(--app-font-size-sm);
  font-weight: 600;
  color: var(--text-color);
}

/* Blocco "quando": spinto in fondo a destra, data sopra / ora sotto. */
.giornale-when {
  margin-left: auto;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  text-align: right;
  line-height: 1.2;
}

.giornale-date {
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.giornale-time {
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
