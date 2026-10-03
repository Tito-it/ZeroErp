<script setup>
// Scopo: Drawer dettaglio di un job della coda lavori (FE-6, brief
//        gestione-code): testata (tipo/stato/proprietario/priorità/origine),
//        timeline (accodato→claimed→started→ended), tentativi + ultimo errore,
//        esito (result) e payload. Sola lettura: le azioni restano nel kebab
//        della lista. Fuori scope/inesistente → 404 dal BE → toast + chiusura.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import AppDrawer from '../../core/components/AppDrawer.vue'
import JsonBlocco from '../../core/components/JsonBlocco.vue'
import { useNotify } from '../../core/composables/useNotify'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { extractApiError } from '../../core/utils/apiError'
import { displayTimestamp } from '../../core/utils/date'
import { statoCodaLavoriSeverity } from '../../core/utils/severity'
import { DRAWER_WIDTH, STATUS_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { getCodaLavoroDettaglio } from '../../core/api/tracciamento'

const { t } = useI18n()
const notify = useNotify()

const props = defineProps({
  visible: { type: Boolean, default: false },
  jobId: { type: Number, default: null },
})

const emit = defineEmits(['update:visible', 'changed'])
const onClose = useDrawerClose(emit)

const job = ref(null)
const loading = ref(false)

// Scopo: carica il dettaglio; 404 (fuori scope) → toast e chiusura.
async function load() {
  if (!props.jobId) return
  loading.value = true
  job.value = null
  try {
    const res = await getCodaLavoroDettaglio(props.jobId)
    job.value = res.data?.data ?? null
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
    onClose()
  } finally {
    loading.value = false
  }
}

watch(() => [props.visible, props.jobId], ([v]) => { if (v) load() })

// Il pretty-print dei tre jsonb (errore/esito/payload) e' il BB `JsonBlocco`
// (2026-09-19, regola del 2 alla seconda occorrenza: il `context` di
// `dbops.error_log`) — la copia locale e' stata ritirata.
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('strumenti.code.dettaglio_titolo', { id: props.jobId ?? '' })"
    :icon="NAV_ICONS.CODE_LAVORO"
    :width="DRAWER_WIDTH.STANDARD"
    :proteggi-corpo="false"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <!-- Durante la lettura si dice che si sta leggendo: un corpo bianco non
         distingue «in arrivo» da «niente». -->
    <div v-if="loading" class="app-loading"><i :class="STATUS_ICONS.CARICAMENTO" /></div>
    <template v-else-if="job">
      <!-- Testata -->
      <div class="app-job-testata">
        <span class="app-mono app-job-tipo">{{ job.job_type }}</span>
        <Tag :value="job.stato" :severity="statoCodaLavoriSeverity(job.stato)" />
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('strumenti.code.col_proprietario') }}</label>
          <span>
            {{ job.proprietario ?? '—' }}
            <Tag
              v-if="job.is_mio"
              :value="t('strumenti.code.mio_tag')"
              severity="info"
            />
          </span>
        </div>
        <div class="form-field">
          <label>{{ t('strumenti.code.dettaglio_origine') }}</label>
          <span>{{ job.origine }} · {{ t('strumenti.code.dettaglio_priorita') }} {{ job.priorita }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('strumenti.code.col_tentativi') }}</label>
          <span>{{ job.tentativi }}/{{ job.max_tentativi }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('strumenti.code.dettaglio_job_run') }}</label>
          <span>{{ job.job_run_id ?? '—' }}</span>
        </div>
      </div>

      <!-- Timeline -->
      <div class="form-field">
        <label>{{ t('strumenti.code.dettaglio_timeline') }}</label>
        <ul class="app-job-timeline">
          <li>{{ t('strumenti.code.timeline_accodato') }}: {{ job.data_insert ? displayTimestamp(job.data_insert) : '—' }}</li>
          <li v-if="job.run_after">{{ t('strumenti.code.timeline_run_after') }}: {{ displayTimestamp(job.run_after) }}</li>
          <li>{{ t('strumenti.code.timeline_avviato') }}: {{ job.started_at ? displayTimestamp(job.started_at) : '—' }}</li>
          <li>{{ t('strumenti.code.timeline_concluso') }}: {{ job.ended_at ? displayTimestamp(job.ended_at) : '—' }}</li>
        </ul>
      </div>

      <!-- Ultimo errore -->
      <div v-if="job.ultimo_errore" class="form-field">
        <label>{{ t('strumenti.code.dettaglio_errore') }}</label>
        <JsonBlocco :value="job.ultimo_errore" errore />
      </div>

      <!-- Esito -->
      <div v-if="job.result" class="form-field">
        <label>{{ t('strumenti.code.dettaglio_esito') }}</label>
        <JsonBlocco :value="job.result" />
      </div>

      <!-- Payload -->
      <div v-if="job.payload" class="form-field">
        <label>{{ t('strumenti.code.dettaglio_payload') }}</label>
        <JsonBlocco :value="job.payload" />
      </div>
    </template>
  </AppDrawer>
</template>

<style scoped>
.app-job-testata {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.app-job-tipo {
  font-weight: 600;
}
.app-job-timeline {
  margin: 0;
  padding-left: 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
</style>
