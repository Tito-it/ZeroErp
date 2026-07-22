<script setup>
// Scopo: Pannello esiti fatturazione (cockpit Fase C, C-5). Sola lettura:
//        mostra lo stato della coda stampa (conteggi per stato, scope emittente
//        dell'operatore lato BE) e il riassunto degli ultimi giri per corsia
//        (da maintenance.job_run_log). Nessuna logica di dominio: legge
//        `GET /vendite/fatturazione/esiti/` e rende. Freschezza su rientro
//        (onActivated) coerente col KeepAlive della view.
import { ref, computed, onActivated } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import { useNotify } from '../../core/composables/useNotify'
import { extractApiError } from '../../core/utils/apiError'
import { displayTimestamp } from '../../core/utils/date'
import { statoCodaStampaSeverity } from '../../core/utils/severity'
import { MANAGE_ICONS } from '../../core/constants'
import { getFatturazioneEsiti } from '../api/lotti'

const { t } = useI18n()
const notify = useNotify()

const giri = ref([])
const codaStampa = ref({})
const loading = ref(false)

// Ordine degli stati coda + label i18n ESPLICITE (statiche): niente
// costruzione dinamica della chiave, così il guard i18n le vede come citate.
// La severità è centralizzata in core/utils/severity.js
// (statoCodaStampaSeverity — FE-7 brief gestione-code, prima inline qui).
const CODA_STATI = computed(() => [
  { key: 'PENDING', label: t('vendite.fatturazione.coda_pending') },
  { key: 'IN_CORSO', label: t('vendite.fatturazione.coda_in_corso') },
  { key: 'FATTO', label: t('vendite.fatturazione.coda_fatto') },
  { key: 'ERRORE', label: t('vendite.fatturazione.coda_errore') },
])

// Coda senza alcuna riga (in nessuno stato) → messaggio "vuota" al posto dei badge.
const codaVuota = computed(() =>
  CODA_STATI.value.every((s) => (codaStampa.value[s.key] ?? 0) === 0),
)

async function load() {
  loading.value = true
  try {
    const res = await getFatturazioneEsiti()
    const data = res.data?.data ?? {}
    giri.value = data.giri ?? []
    codaStampa.value = data.coda_stampa ?? {}
  } catch (err) {
    // Fail-visible: un pannello vuoto per errore non deve sembrare "tutto ok".
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    loading.value = false
  }
}

onActivated(load)
defineExpose({ refresh: load })
</script>

<template>
  <div class="app-esiti-panel">
    <div class="app-esiti-header">
      <span class="app-esiti-titolo">
        <i class="pi pi-chart-bar" /> {{ t('vendite.fatturazione.esiti_titolo') }}
      </span>
      <Button
        :icon="MANAGE_ICONS.RELOAD"
        text
        rounded
        size="small"
        :loading="loading"
        v-tooltip.top="t('common.reload_list')"
        @click="load"
      />
    </div>

    <div class="app-esiti-body">
      <!-- Stato coda stampa: conteggi per stato. -->
      <div class="app-esiti-coda">
        <span class="text-color-secondary">{{ t('vendite.fatturazione.coda_stampa') }}:</span>
        <template v-for="s in CODA_STATI" :key="s.key">
          <Tag
            v-if="(codaStampa[s.key] ?? 0) > 0"
            :value="`${s.label}: ${codaStampa[s.key]}`"
            :severity="statoCodaStampaSeverity(s.key)"
          />
        </template>
        <span v-if="codaVuota" class="text-color-secondary">
          {{ t('vendite.fatturazione.coda_vuota') }}
        </span>
      </div>

      <!-- Ultimi giri per corsia. -->
      <div v-if="giri.length" class="app-esiti-giri">
        <div v-for="g in giri" :key="g.jobname" class="app-esiti-giro">
          <Tag
            :value="g.last_ok ? t('vendite.fatturazione.giro_ok') : t('vendite.fatturazione.giro_ko')"
            :severity="g.last_ok ? 'success' : 'danger'"
          />
          <span class="app-esiti-jobname">{{ g.jobname }}</span>
          <span class="text-color-secondary">
            {{ g.last_run_at ? displayTimestamp(g.last_run_at) : '—' }}
          </span>
          <span class="text-color-secondary">
            ({{ g.ok_count }}/{{ g.total_runs }})
          </span>
        </div>
      </div>
      <div v-else class="text-color-secondary">{{ t('vendite.fatturazione.nessun_giro') }}</div>
    </div>
  </div>
</template>

<style scoped>
.app-esiti-panel {
  /* Variabili applicative REALI di theme.css (mai --p-* dirette): card
     standard con override dark/light gia' centralizzati. */
  border: 1px solid var(--app-card-border);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  background: var(--app-card-bg);
}
.app-esiti-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.app-esiti-titolo {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.app-esiti-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.app-esiti-coda {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.app-esiti-giri {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.app-esiti-giro {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.app-esiti-jobname {
  font-family: monospace;
  font-size: 0.85em;
}
</style>
