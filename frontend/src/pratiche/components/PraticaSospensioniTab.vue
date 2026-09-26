<script setup>
// Scopo: Tab sospensioni dentro il drawer pratica.
// v1: sola visualizzazione dello storico (lista cronologica inversa).
// Le righe arrivano dalla tabella pratiche.sospensioni (pratica + flussi).
// La gestione attiva (sospendi/riattiva con data/ora manuale) vive nel
// dialog condiviso SospensionePraticaDialog, collegato ai pulsanti della
// DrawerActionsBar: qui solo consultazione. Componente riutilizzabile —
// stesso pattern di PraticaGiornaleTab / PraticaAllegatiTab.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchSospensioni } from '../api/pratiche-api'
import { displayTimestamp } from '../../core/utils/date'
import Tag from 'primevue/tag'

const { t } = useI18n()

const props = defineProps({
  praticaId: { type: Number, required: true }
})

const sospensioni = ref([])
const loading = ref(false)

// Scopo: sospensione attiva = senza data_fine (in corso).
function isAttiva(s) {
  return !s.data_fine
}

// Scopo: durata leggibile della sospensione (chiusa: inizio→fine; attiva:
// inizio→ora). Solo display, nessuna logica di dominio: il DB resta l'autorita'.
function durata(s) {
  const inizio = new Date(s.data_inizio)
  const fine = s.data_fine ? new Date(s.data_fine) : new Date()
  const ms = fine - inizio
  if (!(ms > 0)) return null
  const minuti = Math.floor(ms / 60000)
  const giorni = Math.floor(minuti / 1440)
  const ore = Math.floor((minuti % 1440) / 60)
  const min = minuti % 60
  if (giorni > 0) return t('pratiche.sosp_durata_gg', { g: giorni, h: ore })
  if (ore > 0) return t('pratiche.sosp_durata_oh', { h: ore, m: min })
  return t('pratiche.sosp_durata_min', { m: min })
}

async function loadSospensioni() {
  loading.value = true
  try {
    const res = await fetchSospensioni(props.praticaId)
    sospensioni.value = res.data.data.results || []
  } finally {
    loading.value = false
  }
}

watch(() => props.praticaId, (id) => {
  if (id) loadSospensioni()
}, { immediate: true })
</script>

<template>
  <div>
    <div v-if="loading" class="text-center app-text-muted p-3">
      <i class="pi pi-spin pi-spinner"></i>
    </div>

    <div v-else-if="sospensioni.length === 0" class="text-center app-text-muted p-3">
      {{ t('pratiche.sospensioni_vuote') }}
    </div>

    <div v-else class="sospensioni-list">
      <div v-for="s in sospensioni" :key="s.id" class="app-voce-registro">
        <div class="sospensione-header">
          <i class="pi pi-pause sospensione-icon"></i>
          <Tag
            :value="isAttiva(s) ? t('pratiche.sosp_in_corso') : t('pratiche.sosp_conclusa')"
            :severity="isAttiva(s) ? 'warn' : 'success'"
          />
          <Tag
            :value="s.flusso_id ? t('pratiche.sosp_livello_flusso') : t('pratiche.sosp_livello_pratica')"
            severity="secondary"
          />
          <span v-if="durata(s)" class="sospensione-durata">{{ durata(s) }}</span>
          <span v-if="s.user_insert" class="sospensione-user">{{ s.user_insert }}</span>
        </div>

        <div class="sospensione-periodo">
          <span class="sospensione-periodo-label">{{ t('pratiche.sosp_dal') }}</span>
          <span>{{ displayTimestamp(s.data_inizio) }}</span>
          <span class="sospensione-periodo-label">{{ t('pratiche.sosp_al') }}</span>
          <span>{{ s.data_fine ? displayTimestamp(s.data_fine) : '—' }}</span>
        </div>

        <div v-if="s.data_riattivazione_prevista" class="sospensione-prevista">
          {{ t('pratiche.sosp_riattivazione_prevista') }}: {{ displayTimestamp(s.data_riattivazione_prevista) }}
        </div>

        <div v-if="s.motivo" class="sospensione-motivo">{{ s.motivo }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sospensioni-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}


.sospensione-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.sospensione-icon {
  font-size: 0.8rem;
  color: var(--app-icon-color);
}

.sospensione-durata,
.sospensione-user {
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.sospensione-user {
  margin-left: auto;
  font-style: italic;
}

.sospensione-periodo {
  margin-top: 0.3rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
  font-size: var(--app-font-size-sm);
}

.sospensione-periodo-label {
  color: var(--app-topbar-breadcrumb-color);
}

.sospensione-prevista {
  margin-top: 0.2rem;
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.sospensione-motivo {
  margin-top: 0.25rem;
  font-size: var(--app-font-size-sm);
  color: var(--app-text-muted);
}
</style>
