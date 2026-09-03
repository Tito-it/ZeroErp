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
import { useNotify } from '../../core/composables/useNotify'
import { extractApiError } from '../../core/utils/apiError'
import { displayTimestamp } from '../../core/utils/date'
import { statoCodaStampaSeverity } from '../../core/utils/severity'
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
  try {
    const res = await getFatturazioneEsiti(props.competenzaMese)
    const data = res.data?.data ?? {}
    giri.value = data.giri ?? []
    codaStampa.value = data.coda_stampa ?? {}
    caricato.value = true
  } catch (err) {
    // Fail-visible: un pannello vuoto per errore non deve sembrare "tutto ok".
    notify.error(extractApiError(err, t('common.error')))
  }
}

// ⚠️ `refresh` NON e' piu' un aggancio dichiarato e mai collegato: dal
// 2026-09-03 lo chiama il «Ricarica» della pagina, che e' la ragione per cui il
// pulsante interno ha potuto sparire. Se un domani il pannello venisse montato
// altrove, quel caller deve fare lo stesso — senza, il pannello non avrebbe
// nessun modo di aggiornarsi a comando.
onActivated(load)
// Il mese filtrato cambia → i giri mostrati devono seguirlo. Senza questo il
// pannello resterebbe sui giri del mese precedente accanto a una lista già
// aggiornata: due periodi diversi affiancati, l'errore che si voleva togliere.
watch(() => props.competenzaMese, load)
defineExpose({ refresh: load })
</script>

<template>
  <div class="app-esiti-panel">
    <!-- ⛔ Niente pulsante «Ricarica» qui: la pagina ne ha gia' uno nella
         PageActionsBar, e due comandi identici a mezzo schermo di distanza
         sono un dubbio su cosa aggiornino («questo solo il pannello?»), non
         una comodita'. Chi ricarica la pagina ricarica anche questo — vedi
         `azioniPagina` in LottiListView, che chiama `refresh` sull'istanza. -->
    <div class="app-esiti-header">
      <span class="app-esiti-titolo">
        <i class="pi pi-chart-bar" /> {{ t('vendite.fatturazione.esiti_titolo') }}
      </span>
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
/* ⭐ PANNELLO COMPATTO (2026-09-03, rilievo di Tid): e' un RIASSUNTO sopra la
   lista, non un contenuto — deve stare in poche righe e cedere l'altezza ai
   lotti, che sono il lavoro. Si stringe con la tipografia e le spaziature,
   NON con un'altezza fissa: le righe dei giri vanno a capo per conto loro su
   schermi stretti, e un `max-height` le taglierebbe invece di accorciarle.
   ⚠️ Le misure di carattere vengono dai token di theme.css, non da rem
   inventate: --app-font-size-sm e' la stessa scala delle liste, quindi il
   pannello e la tabella sotto si leggono come un unico piano. */
.app-esiti-panel {
  /* Variabili applicative REALI di theme.css (mai --p-* dirette): card
     standard con override dark/light gia' centralizzati. */
  border: 1px solid var(--app-card-border);
  border-radius: 8px;
  padding: 0.4rem 0.75rem;
  margin-bottom: 0.5rem;
  background: var(--app-card-bg);
  font-size: var(--app-font-size-sm);
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
  gap: 0.4rem;
}
.app-esiti-body {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.3rem;
}
.app-esiti-coda {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.app-esiti-giri {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
/* Le righe di DETTAGLIO: sono quelle che pesano di piu' in altezza (una per
   giro) e quelle che l'occhio consulta di rado — scendono sotto la scala
   comune. */
.app-esiti-giro {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  font-size: 0.78rem;
  line-height: 1.35;
}
.app-esiti-giro-label {
  font-weight: 500;
}
.app-esiti-origine {
  font-size: 0.75em;
}
/* :deep() sui Tag di PrimeVue: e' l'unico uso ammesso dagli standard
   (override di libreria) e serve qui perche' un Tag a dimensione piena
   riporterebbe da solo l'altezza che il resto del pannello ha appena perso. */
.app-esiti-panel :deep(.p-tag) {
  padding: 0.1rem 0.4rem;
  font-size: 0.72rem;
  line-height: 1.3;
}
</style>
