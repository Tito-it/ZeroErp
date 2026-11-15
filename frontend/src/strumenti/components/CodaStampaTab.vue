<script setup>
// Scopo: Tab «Coda stampa» della vista Strumenti (FE-4): lista paginata
//        dell'outbox PDF (vendite.fatture_stampa_coda). ⚠️ Non e' piu' di sola
//        lettura dal 2026-09-04: vedi la nota sull'archiviazione qui sotto.
//        Restano assenti i verbi di ESECUZIONE (P-4 — il drainer ritenta da
//        solo). Ambito PER-OPERATORE come
//        la coda lavori (2026-07-23, decisione Tid): «Solo i miei» = righe
//        innescate da me (audit user_insert via GUC identità), «Tutti» = di
//        tutti gli operatori. La colonna «Operatore» + tag «mio» rendono
//        leggibile chi ha lanciato; l'emittente resta colonna informativa.
//
//        Lista configurabile su config DB `vendite.fatture_stampa_coda`
//        (ui.lista_definizione id 35 — 7° lotto, 2026-08-03): personalizzazione
//        colonne + ordinamento server-side (whitelist BE CODA_STAMPA_SORT_SQL,
//        estesa il 2026-08-02 — la colonna fattura ordina per `fattura_numero`
//        con NULLS LAST, non per id) + preset `data_update desc` che replica il
//        default BE. Stato lista nello store Pinia `useCodaStampaStore`
//        (stores/codeJobs.js).
//
// ⭐ Dal 2026-08-27 lo SCHELETRO (toolbar, stato worker, lista, refresh
//    periodico silenzioso, colonna stato con la rotellina, empty) vive in
//    `CodaTabBase`, condiviso con la coda lavori. Qui restano le colonne di
//    dominio: fattura, emittente, operatore, lotto, esito.
//
// ⭐ Dal 2026-09-04 la scheda NON e' piu' di sola lettura: ha le due azioni di
//    riga «Archivia» / «Ripristina» (brief-db-archiviazione-righe-code), che
//    tolgono una riga dall'ELENCO senza toccarne lo stato — i conteggi del
//    pannello «Esiti fatturazione» restano fermi, ed e' la ragione per cui
//    l'archiviazione esiste invece di una cancellazione. Restano assenti i
//    verbi di ESECUZIONE (annulla / requeue): il drainer ritenta da solo (P-4).
// ⚠️ La colonna del kebab su questa lista e' nata col seed `ui.lista_colonna`
//    712 (2026-09-04): prima non c'era, e senza quella riga lo slot `#actions`
//    non avrebbe dove attaccarsi — silenziosamente, senza errore.
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { computed, ref } from 'vue'
import { statoCodaStampaSeverity, STATO_CODA_STAMPA_MAP } from '../../core/utils/severity'
import { formatFatturaNumero } from '../../core/utils/format'
import { MANAGE_ICONS } from '../../core/constants'
import { archiviaCodaStampa, ripristinaCodaStampa } from '../../core/api/tracciamento'
import { useCodaArchiviazione } from '../composables/useCodaArchiviazione'
import { useCodaFiltri } from '../composables/useCodaFiltri'
import { useSelezioneCoda } from '../composables/useSelezioneCoda'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useCodaStampaStore } from '../stores/codeJobs'
import CodaTabBase from './CodaTabBase.vue'

const { t } = useI18n()
const store = useCodaStampaStore()

const baseRef = ref(null)
function ricarica() {
  baseRef.value?.load()
}

// Scopo: messaggio sintetico dall'ultimo_errore jsonb (fail-visible in lista).
function erroreLabel(row) {
  const err = row.ultimo_errore
  if (!err) return null
  return err.message || err.code || t('common.error')
}

// Solo il gate delle AZIONI: le opzioni dei filtri le prende il telaio.
const { canManage } = useCodaFiltri(STATO_CODA_STAMPA_MAP)
const isReadonly = useInjectReadonly()

// Selezione multipla per l'archiviazione di massa (stessa macchina della coda
// lavori: le due code sono gemelle anche qui).
const selezione = useSelezioneCoda({
  righeVisibili: computed(() => store.items),
  abilitata: computed(() => canManage.value && !isReadonly.value),
})

// Le voci di kebab e il verbo di massa, dal composable condiviso con la coda
// lavori.
const { azioniArchiviazione, archiviaRighe, loading: archiviazioneLoading } =
  useCodaArchiviazione({
    archivia: archiviaCodaStampa,
    ripristina: ripristinaCodaStampa,
    ricarica,
    // La riga si nomina con la sua FATTURA, non col proprio id: e' quello che
    // l'operatore sta guardando.
    etichettaRiga: (row) => formatFatturaNumero(row),
    // Le righe archiviate escono dall'elenco: una selezione che le contasse
    // ancora mentirebbe. ⭐ Si tengono spuntate le sole FALLITE — sono
    // esattamente quelle su cui l'operatore deve tornare.
    onArchiviato: (idsFalliti) => selezione.tieniSolo(idsFalliti),
  })

// Scopo: azioni di riga della coda stampa — oggi le sole due
//        dell'archiviazione. Resta una funzione (e non l'array nudo) perche'
//        il telaio la invoca PER RIGA, e le due voci si escludono a vicenda
//        secondo `row.archiviato`.
function buildRowActions(row) {
  return azioniArchiviazione(row)
}
</script>

<template>
  <CodaTabBase
    ref="baseRef"
    :store="store"
    codice="vendite.fatture_stampa_coda"
    coda="coda_stampa"
    :stato-map="STATO_CODA_STAMPA_MAP"
    :stato-severity="statoCodaStampaSeverity"
    empty-key="strumenti.code.nessuna_riga"
    :empty-icon="MANAGE_ICONS.STAMPA"
    :extra-loading="archiviazioneLoading"
    :build-row-actions="buildRowActions"
    :selezione="selezione"
    :on-archivia-selezione="archiviaRighe"
  >
    <!-- La label resta anno/serie/numero componibile; l'ordinamento della
         colonna e' su `fattura_numero` (campo_sorgente del seed, NULLS LAST
         lato BE: e' NULL finche' la fattura e' in bozza). -->
    <template #cell-fattura="{ data }">
      {{ formatFatturaNumero(data) }}
    </template>
    <template #cell-emittente="{ data }">
      {{ data.emittente_codice ?? '—' }}
    </template>
    <!-- Operatore che ha innescato il processo (audit user_insert via GUC
         identità), con tag «mio» come la colonna proprietario della coda
         lavori. Sempre visibile: anche in «Solo i miei» dice chi sei. -->
    <template #cell-operatore="{ data }">
      <span>
        {{ data.operatore ?? '—' }}
        <Tag
          v-if="data.is_mio"
          :value="t('strumenti.code.mio_tag')"
          severity="info"
          class="app-code-mio-tag"
        />
      </span>
    </template>
    <template #cell-lotto_id="{ data }">
      {{ data.lotto_id ?? '—' }}
    </template>
    <!-- Colonne calcolate FE (seed: campo_sorgente NULL, ordinabile=f). -->
    <template #cell-esito="{ data }">
      <span v-if="data.documento_id">
        <i :class="MANAGE_ICONS.PDF" /> {{ t('strumenti.code.esito_documento', { id: data.documento_id }) }}
      </span>
      <span v-else-if="erroreLabel(data)" class="app-code-errore">
        {{ erroreLabel(data) }}
      </span>
      <span v-else>—</span>
    </template>
    <!-- data_update non ha slot: il seed dichiara `datetime_short`. -->
  </CodaTabBase>
</template>

<style scoped>
.app-code-errore {
  color: var(--app-severity-danger);
  font-size: 0.85em;
}
</style>
