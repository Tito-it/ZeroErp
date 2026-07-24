<script setup>
// Scopo: Drawer RAPIDO delle code di lavoro (FE-3, brief gestione-code —
//        D-B): aperto dal badge top bar. Mostra i conteggi delle due code
//        (scoped all'operatore), lo stato dei worker drainer («coda impegnata»
//        vs «worker giù») e gli ultimi job propri; footer link alla vista
//        completa (Strumenti → Code di lavoro). Sola lettura: le azioni di
//        governo (annulla/requeue) vivono nella vista completa.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Message from 'primevue/message'
import FormFooter from './FormFooter.vue'
import { useNotify } from '../composables/useNotify'
import { useDrawerClose } from '../composables/useDrawerClose'
import { extractApiError } from '../utils/apiError'
import { displayTimestamp } from '../utils/date'
import { statoCodaLavoriSeverity, statoCodaStampaSeverity } from '../utils/severity'
import { DRAWER_WIDTH } from '../constants'
import { getCodeConteggi, listCodaLavori } from '../api/tracciamento'
import { contaVivi, workerOkDaConteggi } from '../composables/useQueueCountsPolling'

const { t } = useI18n()
const notify = useNotify()
const router = useRouter()

const props = defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible'])
const onClose = useDrawerClose(emit)

const conteggi = ref(null)
const ultimiJob = ref([])
const loading = ref(false)

// Stati mostrati come chip (label i18n ESPLICITE — il guard i18n le vede).
const STATI_LAVORI = computed(() => [
  { key: 'PENDING', label: t('strumenti.code.stato_pending') },
  { key: 'IN_CORSO', label: t('strumenti.code.stato_in_corso') },
])
const STATI_STAMPA = STATI_LAVORI

// Predicati dalla fonte unica del polling (regola del 2: stessa definizione
// di «vivo» e «worker ok» del badge, mai due copie che possono divergere).
const workerOk = computed(() => workerOkDaConteggi(conteggi.value))
const codaImpegnata = computed(() =>
  (contaVivi(conteggi.value, 'coda_lavori') + contaVivi(conteggi.value, 'coda_stampa')) > 0,
)

// Scopo: carica conteggi + ultimi 5 job propri (id DESC dal BE). Fail-visible.
//        SOLA LETTURA: nessun emit verso il topbar — il badge segue il suo
//        polling (un «changed» qui rifetcherebbe lo stesso endpoint appena
//        letto, innescando anche la race delle catene di polling).
async function load() {
  loading.value = true
  try {
    const [resConteggi, resJobs] = await Promise.all([
      getCodeConteggi(),
      listCodaLavori({ limit: 5, offset: 0 }),
    ])
    conteggi.value = resConteggi.data?.data ?? null
    ultimiJob.value = resJobs.data?.data?.results ?? []
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (v) => { if (v) load() })

// Scopo: apre la vista completa (Strumenti → Code di lavoro) e chiude il drawer.
function apriGestioneCompleta() {
  onClose()
  router.push('/strumenti/code-lavoro')
}
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.SIMPLE }"
    :header="t('strumenti.code.drawer_titolo')"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <div class="app-drawer-content">
      <!-- Stato worker: giù (nessun run recente) / coda impegnata / tutto scorre -->
      <Message v-if="workerOk === false" severity="warn" :closable="false">
        {{ t('strumenti.code.banner_worker_giu') }}
      </Message>
      <Message v-else-if="codaImpegnata" severity="info" :closable="false">
        {{ t('strumenti.code.banner_coda_impegnata') }}
      </Message>
      <Message v-else-if="conteggi" severity="success" :closable="false">
        {{ t('strumenti.code.banner_tutto_scorre') }}
      </Message>

      <!-- Conteggi coda lavori -->
      <div class="app-code-sezione">
        <span class="app-code-sezione-titolo">
          <i class="pi pi-inbox" /> {{ t('strumenti.code.coda_lavori') }}
        </span>
        <div class="app-code-chips">
          <template v-for="s in STATI_LAVORI" :key="s.key">
            <Tag
              v-if="(conteggi?.coda_lavori?.[s.key.toLowerCase()] ?? 0) > 0"
              :value="`${s.label}: ${conteggi.coda_lavori[s.key.toLowerCase()]}`"
              :severity="statoCodaLavoriSeverity(s.key)"
            />
          </template>
          <span
            v-if="((conteggi?.coda_lavori?.pending ?? 0) + (conteggi?.coda_lavori?.in_corso ?? 0)) === 0"
            class="text-color-secondary"
          >
            {{ t('strumenti.code.coda_vuota') }}
          </span>
        </div>
      </div>

      <!-- Conteggi coda stampa -->
      <div class="app-code-sezione">
        <span class="app-code-sezione-titolo">
          <i class="pi pi-print" /> {{ t('strumenti.code.coda_stampa') }}
        </span>
        <div class="app-code-chips">
          <template v-for="s in STATI_STAMPA" :key="s.key">
            <Tag
              v-if="(conteggi?.coda_stampa?.[s.key.toLowerCase()] ?? 0) > 0"
              :value="`${s.label}: ${conteggi.coda_stampa[s.key.toLowerCase()]}`"
              :severity="statoCodaStampaSeverity(s.key)"
            />
          </template>
          <span
            v-if="((conteggi?.coda_stampa?.pending ?? 0) + (conteggi?.coda_stampa?.in_corso ?? 0)) === 0"
            class="text-color-secondary"
          >
            {{ t('strumenti.code.coda_vuota') }}
          </span>
        </div>
      </div>

      <!-- Ultimi job propri (stato/tipo/quando) -->
      <div class="app-code-sezione">
        <span class="app-code-sezione-titolo">
          <i class="pi pi-history" /> {{ t('strumenti.code.ultimi_job') }}
        </span>
        <div v-if="ultimiJob.length" class="app-code-jobs">
          <div v-for="job in ultimiJob" :key="job.id" class="app-code-job">
            <Tag :value="job.stato" :severity="statoCodaLavoriSeverity(job.stato)" />
            <span class="app-code-job-tipo">{{ job.job_type }}</span>
            <span class="text-color-secondary">
              {{ job.started_at ? displayTimestamp(job.started_at) : '—' }}
            </span>
          </div>
        </div>
        <span v-else class="text-color-secondary">
          {{ t('strumenti.code.nessun_job') }}
        </span>
      </div>

      <Button
        :label="t('strumenti.code.apri_gestione')"
        icon="pi pi-arrow-right"
        icon-pos="right"
        text
        :loading="loading"
        @click="apriGestioneCompleta"
      />

      <FormFooter close-only @cancel="onClose" />
    </div>
  </Drawer>
</template>

<style scoped>
.app-code-sezione {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--app-card-border);
}
.app-code-sezione-titolo {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.app-code-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.app-code-jobs {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.app-code-job {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.app-code-job-tipo {
  font-family: monospace;
  font-size: 0.85em;
}
</style>
