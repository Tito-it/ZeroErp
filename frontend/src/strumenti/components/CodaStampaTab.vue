<script setup>
// Scopo: Tab «Coda stampa» della vista Strumenti (FE-4): lista paginata
//        dell'outbox PDF (vendite.fatture_stampa_coda). SOLA LETTURA: nessuna
//        azione (P-4 — il drainer ritenta da solo). Ambito PER-OPERATORE come
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
//    `CodaTabBase`, condiviso con la coda lavori. Qui restano le sole colonne
//    di dominio: fattura, emittente, operatore, lotto, esito.
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { statoCodaStampaSeverity, STATO_CODA_STAMPA_MAP } from '../../core/utils/severity'
import { useCodaStampaStore } from '../stores/codeJobs'
import CodaTabBase from './CodaTabBase.vue'

const { t } = useI18n()
const store = useCodaStampaStore()

// Scopo: numero fattura leggibile (anno/serie/numero, campi opzionali).
function fatturaLabel(row) {
  if (row.fattura_numero == null) return `#${row.fattura_id}`
  const serie = row.fattura_serie ? `/${row.fattura_serie}` : ''
  return `${row.fattura_anno ?? ''}${serie} n. ${row.fattura_numero}`
}

// Scopo: messaggio sintetico dall'ultimo_errore jsonb (fail-visible in lista).
function erroreLabel(row) {
  const err = row.ultimo_errore
  if (!err) return null
  return err.message || err.code || t('common.error')
}
</script>

<template>
  <CodaTabBase
    :store="store"
    codice="vendite.fatture_stampa_coda"
    coda="coda_stampa"
    :stato-map="STATO_CODA_STAMPA_MAP"
    :stato-severity="statoCodaStampaSeverity"
    empty-key="strumenti.code.nessuna_riga"
    empty-icon="pi pi-print"
  >
    <!-- La label resta anno/serie/numero componibile; l'ordinamento della
         colonna e' su `fattura_numero` (campo_sorgente del seed, NULLS LAST
         lato BE: e' NULL finche' la fattura e' in bozza). -->
    <template #cell-fattura="{ data }">
      {{ fatturaLabel(data) }}
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
    <!-- Colonne calcolate FE (seed: campo_sorgente vuoto, ordinabile=f). -->
    <template #cell-esito="{ data }">
      <span v-if="data.documento_id">
        <i class="pi pi-file-pdf" /> {{ t('strumenti.code.esito_documento', { id: data.documento_id }) }}
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
  color: var(--p-red-500);
  font-size: 0.85em;
}
</style>
