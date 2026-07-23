<script setup>
// Scopo: Pannello esiti fatturazione (cockpit Fase C, C-5). Sola lettura:
//        mostra lo stato della coda stampa (conteggi per stato, scope emittente
//        dell'operatore lato BE) e il riassunto dei giri delle CORSIE di
//        fatturazione (da maintenance.job_run_log). Nessuna logica di dominio:
//        legge `GET /vendite/fatturazione/esiti/` e rende. Freschezza su rientro
//        (onActivated) coerente col KeepAlive della view.
//
// `competenzaMese` (2026-07-23): i giri mostrati sono quelli lanciati PER quel
// mese, lo stesso filtrato nella lista lotti sopra cui il pannello vive. Il
// pannello non filtra nulla da sé: passa il parametro e rende ciò che il BE
// concede.
// I worker di drenaggio code (draina_*) NON sono più qui: erano poller che si
// svegliano ogni 1-2 minuti, quindi il loro contatore di run cresceva di ~1440
// al giorno e affiancato alle corsie vere rendeva impossibile distinguere
// «worker vivo» da «batch fermo da un mese». La loro liveness vive ora accanto
// alle code che monitorano (tab della vista Code di lavoro).
//
// I giri arrivano dalle DUE strade con cui si fattura, marcate da `origine`:
// «app» (pulsanti del cockpit, via coda lavori) e «batch» (riga di comando,
// quando verrà schedulato — etichettato «di sistema»). Entrambe sempre
// presenti: leggerne una sola è il difetto che faceva dichiarare «nessun
// giro» mentre si fatturava ogni giorno dall'app.
//
// I conteggi sono COMPLESSIVI (decisione Tid 2026-07-23): chi è autorizzato
// all'attività vede il totale del mese, non solo il proprio — un totale
// ristretto è un'informazione sbagliata. Le righe «app» portano lo split
// mio_count/altri_count per distinguere il proprio lavoro senza perdere il
// quadro; le righe «batch» no (sono di sistema, non di un operatore).
import { ref, computed, onActivated, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import { useNotify } from '../../core/composables/useNotify'
import { extractApiError } from '../../core/utils/apiError'
import { displayTimestamp } from '../../core/utils/date'
import { statoCodaStampaSeverity } from '../../core/utils/severity'
import { MANAGE_ICONS } from '../../core/constants'
import { getFatturazioneEsiti } from '../api/lotti'

const props = defineProps({
  // Mese di competenza in formato API (YYYY-MM-DD) o null = nessun filtro
  // (giri di tutti i tempi). Arriva dal filtro della lista lotti.
  competenzaMese: { type: String, default: null },
})

const { t } = useI18n()
const notify = useNotify()

const giri = ref([])
const codaStampa = ref({})
const loading = ref(false)
// TRUE dopo il primo load riuscito: distingue "nessun giro" da "non ancora
// caricato", così l'empty state non mente al primo paint.
const caricato = ref(false)

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

// Etichette dei giri: mappa ESPLICITA e statica (nessuna chiave i18n costruita
// a runtime, così il guard i18n le vede come citate — stessa disciplina di
// CODA_STATI sopra). Un jobname non mappato si mostra grezzo invece di
// sparire: meglio un nome tecnico che una riga muta.
const ETICHETTE_GIRO = computed(() => ({
  FATTURAZIONE_GIRO: t('vendite.fatturazione.giro_app'),
  FATTURAZIONE_NUMERA: t('vendite.fatturazione.numera_app'),
  'run_fatturazione_batch:differita': t('vendite.fatturazione.batch_differita'),
  'run_fatturazione_batch:immediata': t('vendite.fatturazione.batch_immediata'),
}))

function etichettaGiro(jobname) {
  return ETICHETTE_GIRO.value[jobname] ?? jobname
}

function etichettaOrigine(origine) {
  return origine === 'app'
    ? t('vendite.fatturazione.origine_app')
    : t('vendite.fatturazione.origine_batch')
}

async function load() {
  loading.value = true
  try {
    const res = await getFatturazioneEsiti(props.competenzaMese)
    const data = res.data?.data ?? {}
    giri.value = data.giri ?? []
    codaStampa.value = data.coda_stampa ?? {}
    caricato.value = true
  } catch (err) {
    // Fail-visible: un pannello vuoto per errore non deve sembrare "tutto ok".
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    loading.value = false
  }
}

onActivated(load)
// Il mese filtrato cambia → i giri mostrati devono seguirlo. Senza questo il
// pannello resterebbe sui giri del mese precedente accanto a una lista già
// aggiornata: due periodi diversi affiancati, l'errore che si voleva togliere.
watch(() => props.competenzaMese, load)
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
          {{ competenzaMese
            ? t('vendite.fatturazione.coda_vuota_mese')
            : t('vendite.fatturazione.coda_vuota') }}
        </span>
      </div>

      <!-- Giri delle corsie di fatturazione per il mese selezionato. -->
      <div v-if="giri.length" class="app-esiti-giri">
        <div v-for="g in giri" :key="`${g.origine}:${g.jobname}`" class="app-esiti-giro">
          <Tag
            :value="g.last_ok ? t('vendite.fatturazione.giro_ok') : t('vendite.fatturazione.giro_ko')"
            :severity="g.last_ok ? 'success' : 'danger'"
          />
          <span class="app-esiti-giro-label">{{ etichettaGiro(g.jobname) }}</span>
          <!-- Da DOVE è partito il lavoro: le due strade convivono e vanno
               distinte a colpo d'occhio, non dedotte dal nome tecnico. -->
          <Tag
            :value="etichettaOrigine(g.origine)"
            severity="secondary"
            class="app-esiti-origine"
          />
          <span class="text-color-secondary">
            {{ g.last_run_at ? displayTimestamp(g.last_run_at) : '—' }}
          </span>
          <!-- Esecuzioni riuscite sul totale, RELATIVE al mese filtrato.
               L'etichetta è esplicita: "(23/24)" da solo si legge come un
               conteggio di fatture, che non è. -->
          <span class="text-color-secondary">
            {{ t('vendite.fatturazione.giro_esecuzioni', {
              ok: g.ok_count, tot: g.total_runs,
            }) }}
          </span>
          <!-- Split miei/altri, solo righe app (le batch sono di sistema):
               distingue il proprio lavoro dentro il totale complessivo. Sempre
               visibile, anche a split «0 tuoi»: l'assenza dello split è
               proprio l'ambiguità che nascondeva il lavoro altrui. -->
          <span v-if="g.mio_count !== undefined" class="text-color-secondary">
            {{ t('vendite.fatturazione.giro_miei_altri', {
              mie: g.mio_count, altri: g.altri_count,
            }) }}
          </span>
        </div>
      </div>
      <div v-else-if="caricato" class="text-color-secondary">
        {{ competenzaMese
          ? t('vendite.fatturazione.nessun_giro_mese')
          : t('vendite.fatturazione.nessun_giro') }}
      </div>
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
.app-esiti-giro-label {
  font-weight: 500;
}
.app-esiti-origine {
  font-size: 0.75em;
}
</style>
