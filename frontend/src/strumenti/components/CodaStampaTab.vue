<script setup>
// Scopo: Tab «Coda stampa» della vista Strumenti (FE-4): lista paginata
//        dell'outbox PDF (vendite.fatture_stampa_coda). SOLA LETTURA: nessuna
//        azione (P-4 — il drainer ritenta da solo). Ambito PER-OPERATORE come
//        la coda lavori (2026-07-23, decisione Tid): «Solo i miei» = righe
//        innescate da me (audit user_insert via GUC identità), «Tutti» = di
//        tutti gli operatori. La colonna «Operatore» + tag «mio» rendono
//        leggibile chi ha lanciato; l'emittente resta colonna informativa.
//
//        Convertita a <ListaConfigurabile> (config DB
//        `vendite.fatture_stampa_coda`, ui.lista_definizione id 35 — 7° lotto,
//        2026-08-03): personalizzazione colonne + ordinamento server-side
//        (whitelist BE CODA_STAMPA_SORT_SQL, estesa il 2026-08-02 — la
//        colonna fattura ordina per `fattura_numero` con NULLS LAST, non per
//        id) + preset `data_update desc` che replica il default BE. Stato
//        lista nello store Pinia `useCodaStampaStore` (stores/codeJobs.js).
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useNotify } from '../../core/composables/useNotify'
import { extractApiError } from '../../core/utils/apiError'
import { statoCodaStampaSeverity, STATO_CODA_STAMPA_MAP } from '../../core/utils/severity'
import { useCodaFiltri } from '../composables/useCodaFiltri'
import { useCodaStampaStore } from '../stores/codeJobs'
import CodaFiltriToolbar from './CodaFiltriToolbar.vue'
import CodaWorkerStato from './CodaWorkerStato.vue'

const { t } = useI18n()
const notify = useNotify()

const store = useCodaStampaStore()

// Helper UI condivisi dei tab code. La coda stampa non ha azioni per-riga né
// dettaglio: `canManage` non serve (le righe sono per-emittente).
const { statoOptions, ambitoOptions } = useCodaFiltri(STATO_CODA_STAMPA_MAP)

// Stato worker: ricaricato insieme alla lista, così «Ricarica» aggiorna anche
// l'ultimo giro (altrimenti resterebbe fermo al primo ingresso nel tab).
const workerStatoRef = ref(null)

// Scopo: fetch con refresh worker e cattura errore (fail-visible).
async function load() {
  workerStatoRef.value?.refresh()
  try {
    await store.fetchList()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

const {
  onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, { onReload: load })

// Cambio filtro toolbar: si riparte da pagina 1.
function onFilterChange() {
  store.filters.offset = 0
  load()
}

// Primo caricamento al mount: con <Tabs lazy> ogni attivazione del tab è un
// MOUNT (pattern ResiCodaTable); la freshness al rientro rotta la gestisce
// l'onActivated di useSearchTable dentro lo scaffolding.
onMounted(load)

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
  <div class="app-tab-content">
    <CodaFiltriToolbar
      :filtri="store.filters"
      :stato-options="statoOptions"
      :ambito-options="ambitoOptions"
      :page-actions="pageActions"
      :filtri-inerti="perimetroBloccato"
      @change="onFilterChange"
    >
      <template #actions-suffix>
        <ListaConfigStatusTag :dirty="dirty" />
      </template>
    </CodaFiltriToolbar>

    <!-- Liveness del drainer: dice se la coda sta girando o è ferma. Il
         conteggio delle sue esecuzioni è volutamente assente (un poller a
         1/2min produce numeri enormi che non informano su nulla). -->
    <CodaWorkerStato ref="workerStatoRef" coda="coda_stampa" />

    <ListaConfigurabile
      ref="listaRef"
      codice="vendite.fatture_stampa_coda"
      data-key="id"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @config-loaded="onConfigLoaded"
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
      <template #cell-stato="{ data }">
        <Tag :value="data.stato" :severity="statoCodaStampaSeverity(data.stato)" />
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

      <template #empty>
        <div class="app-empty-state">
          <i class="pi pi-print" />
          <p>{{ t('strumenti.code.nessuna_riga') }}</p>
        </div>
      </template>
    </ListaConfigurabile>
  </div>
</template>

<style scoped>
.app-code-errore {
  color: var(--p-red-500);
  font-size: 0.85em;
}
.app-code-mio-tag {
  margin-left: 0.35rem;
  font-size: 0.65rem;
}
</style>
