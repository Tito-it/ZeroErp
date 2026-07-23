<script setup>
// Scopo: Riga di stato del WORKER che drena una coda: ultimo giro eseguito +
//        se il worker è vivo. Risponde alla sola domanda utile su un poller —
//        «la coda sta girando o è ferma?» — accanto alla coda che monitora.
//
// Perché qui e non nel cockpit fatturazione (2026-07-23, richiesta Tid): i
// worker si svegliano ogni 1-2 minuti, quindi il loro CONTEGGIO di esecuzioni
// cresce di ~1440 al giorno e non dice nulla sul lavoro svolto. Mostrato tra
// gli esiti di fatturazione affiancava numeri enormi e irrilevanti alle corsie
// vere, rendendo impossibile distinguere «worker vivo» da «batch fermo da un
// mese». Del worker si tiene quindi solo l'ULTIMO GIRO, ed è pertinente qui.
//
// `attivo` è calcolato dal BE (run negli ultimi WORKER_ATTIVO_SOGLIA_MINUTI=10
// minuti): il FE non ha una seconda definizione di «vivo» che possa divergere.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { useLazyTabLoad } from '../../core/composables/useLazyTabLoad'
import { displayTimestamp } from '../../core/utils/date'
import { getCodeConteggi } from '../../core/api/tracciamento'

const props = defineProps({
  // Chiave della coda nella risposta conteggi: 'coda_lavori' | 'coda_stampa'.
  coda: { type: String, required: true },
})

const { t } = useI18n()

const info = ref(null)
// Errori SILENZIOSI: è un indicatore ambientale accessorio: un toast a ogni
// fallimento disturberebbe il lavoro sulla coda, che resta utilizzabile. Il
// dato assente si rende come "sconosciuto", non come "fermo" (che sarebbe un
// falso allarme).
async function load() {
  try {
    const res = await getCodeConteggi()
    info.value = res.data?.data?.worker?.[props.coda] ?? null
  } catch {
    info.value = null
  }
}

// Primo caricamento + freshness al rientro, senza doppio fetch iniziale (il
// vecchio onMounted+onActivated senza guardia fetchava DUE volte al primo
// ingresso rotta: i due hook scattano nello stesso flush — BB alla 3ª copia).
useLazyTabLoad(load)
defineExpose({ refresh: load })

const ultimoGiro = computed(() =>
  info.value?.last_run_at ? displayTimestamp(info.value.last_run_at) : null,
)
// `attivo` mancante (dato non arrivato) ≠ worker fermo: niente Tag allarmistico.
const attivo = computed(() => info.value?.attivo ?? null)
</script>

<template>
  <div class="coda-worker-stato">
    <span class="text-color-secondary">
      {{ t('strumenti.code.worker_ultimo_giro') }}:
      {{ ultimoGiro ?? t('strumenti.code.worker_mai_eseguito') }}
    </span>
    <Tag
      v-if="attivo !== null"
      :value="attivo ? t('strumenti.code.worker_attivo') : t('strumenti.code.worker_fermo')"
      :severity="attivo ? 'success' : 'danger'"
    />
  </div>
</template>

<style scoped>
.coda-worker-stato {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  /* Indicatore accessorio: non deve competere con i filtri sopra né con la
     tabella sotto. */
  font-size: var(--app-font-size-sm);
  margin-bottom: 0.5rem;
}
</style>
